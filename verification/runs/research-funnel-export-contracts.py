"""Independent full-cohort export reconciliation; authored original stores only."""
import csv,gzip,hashlib,importlib.util,io,json,os,re,zipfile
from pathlib import Path
import pytest
from backend.lab import service,research_funnel_exports as exports
from backend.lab.config import identity
from backend.lab.store import StateError
from backend.lab.service import Lab
from test_search_statistics_integration import client

spec=importlib.util.spec_from_file_location('exports_authored_final_sources',Path(__file__).with_name('research-funnel-final-boundaries.py'))
fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
originals=fixtures.originals;finals=fixtures.finals;clone_authored=fixtures.clone_authored


def counts(lab):
    with lab.store.db() as db:return {table:db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ['jobs','trial_plans','trial_attempts','events','viewed_windows']}


def forbidden(*args,**kwargs):raise AssertionError('Saved export cannot generate finance or qualification math.')


@pytest.fixture
def saved(finals,tmp_path,monkeypatch):
    lab=clone_authored(finals['complete'],tmp_path)
    monkeypatch.setattr(service,'generate_signals',forbidden);monkeypatch.setattr(Lab,'evaluate',forbidden);monkeypatch.setattr(Lab,'_evaluation_input',forbidden)
    monkeypatch.setattr('backend.lab.research_qualification.qualify',forbidden)
    monkeypatch.setattr('backend.lab.research_funnel_final.family_average',forbidden)
    return lab,finals['qualification_job_id'],finals['job_id']


def original_daily(value):
    output={}
    if value['kind']=='funnel_qualification':
        axes=((family,arm,average) for family,item in value['report']['families'].items() for arm,average in item['axes'].items())
    else:axes=((family,arm,average) for arm,item in value['report']['arms'].items() for family,average in item['families'].items())
    for family,arm,average in axes:
        for convention in ['marked','realized_exit_day_compatibility']:
            for day in average[convention]['daily']:
                output[(family,arm,convention,day['date'])]=(day['mean_pnl']['numerator'],day['mean_pnl']['denominator'])
    return output


def decode(text):return text[1:] if text.startswith("'") else text


@pytest.mark.parametrize('phase',['qualification','final'])
def test_complete_bundle_exact_originals_every_account_every_family_day_and_no_new_work(saved,phase):
    lab,qid,fid=saved;jid=qid if phase=='qualification' else fid;before=counts(lab)
    source=exports.inspect_export_source(lab,jid);value=source['value'];built=exports.build_export(lab,jid,'zip')
    try:
        with zipfile.ZipFile(built['path']) as archive:
            manifest=json.loads(archive.read('manifest.json'))
            assert set(archive.namelist())==set(manifest['entries'])|{'manifest.json'}
            for name,record in manifest['entries'].items():
                raw=archive.read(name);assert hashlib.sha256(raw).hexdigest()==record['sha256'] and len(raw)==record['bytes']
            assert json.loads(archive.read('original-result.json'))==value
            assert json.loads(archive.read('original-study-inputs.json'))==lab.store.study_inputs(source['study']['id'])
            assert json.loads(archive.read('original-job-inputs.json'))==lab.store.job_inputs(jid)
            versions=list(csv.DictReader(io.StringIO(archive.read('versions.csv').decode())))
            originals=value['report']['rows'] if phase=='qualification' else value['rows']
            assert len(versions)==len(originals)==2 and [row['config_id'] for row in versions]==[row['config_id'] for row in originals]
            assert all(row['candidate']=='False' and row['configuration_universe_hash']==source['metadata']['configuration_universe_hash'] for row in versions)
            accounts=list(csv.DictReader(io.StringIO(archive.read('accounts.csv').decode())))
            members=list(csv.DictReader(io.StringIO(archive.read('original_accounts.csv').decode())))
            assert len(accounts)==len(members)==(10 if phase=='qualification' else 4)
            for member in members:
                raw=archive.read(member['archive_path']);assert hashlib.sha256(raw).hexdigest()==member['artifact_sha256']
                book=json.loads(gzip.decompress(raw));report=book['report'] if phase=='qualification' else book[member['arm']]
                assert report['config_id']==member['config_id'] and report['trades']==[] and report['entry_traces']==[]
            actual=list(csv.DictReader(io.StringIO(archive.read('family_daily.csv').decode())))
            got={(row['family'],row['arm'],row['convention'],row['date']):(decode(row['mean_pnl_numerator']),decode(row['mean_pnl_denominator'])) for row in actual}
            assert got==original_daily(value) and len(actual)==len(got)
            html=archive.read('index.html').decode('utf-8');data=json.loads(re.search(r'<script id="evidence" type="application/json">(.*?)</script>',html,re.S)[1])
            assert data['metadata']==source['metadata'] and len(data['tables']['versions']['rows'])==2
            assert len(data['tables']['original_accounts']['rows'])==len(members)
            assert len(data['tables']['family_daily']['rows'])==len(got)
            assert all(row[4] is False for row in data['tables']['versions']['rows'])
        assert counts(lab)==before
    finally:built['path'].unlink(missing_ok=True)


@pytest.mark.parametrize('phase',['qualification','final'])
def test_all_public_pages_and_csvs_match_complete_saved_table_records_without_new_trials(saved,phase):
    lab,qid,fid=saved;jid=qid if phase=='qualification' else fid;before=counts(lab);source=exports.inspect_export_source(lab,jid)
    with client(lab) as c:
        for table in exports.TABLES:
            expected=list(exports.records(lab,source,table))
            response=c.get('/api/jobs/'+jid+'/funnel-evidence/'+table,params={'limit':1,'offset':1})
            assert response.status_code==200,response.text
            page=response.json();assert page['rows']==expected[1:2] and page['pagination']['total']==len(expected)
            csv_response=c.get('/api/jobs/'+jid+'/funnel-export/csv',params={'table':table});assert csv_response.status_code==200,csv_response.text
            assert csv_response.headers['x-evidence-complete']=='1' and csv_response.headers['x-original-root-sha256']==source['metadata']['source_root_sha256']
            rows=list(csv.DictReader(io.StringIO(csv_response.text)));assert len(rows)==len(expected)
            for row,original in zip(rows,expected):
                assert row['job_id']==jid
                for key in exports.COLUMNS[table]:
                    value=original.get(key);assert decode(row[key])==('' if value is None else str(value))
        html=c.get('/api/jobs/'+jid+'/funnel-export/html');assert html.status_code==200
        archive=c.get('/api/jobs/'+jid+'/funnel-export/zip');assert archive.status_code==200
        assert not list((lab.root/'data/exports').iterdir())
        if phase=='qualification':
            rows=c.get('/api/jobs/'+jid+'/result-rows?limit=1&offset=1');assert rows.status_code==200 and rows.json()['rows'][0]['part']==1
    assert counts(lab)==before


def test_offline_untrusted_labels_are_data_and_script_termination_is_escaped(saved):
    lab,qid,fid=saved;source=exports.inspect_export_source(lab,fid)
    label='</script><img src=x onerror=alert(1)> & <b>not markup</b>'
    source['metadata']['study_name']=label
    html=b''.join(exports.html_chunks(lab,source)).decode()
    assert html.count('<script')==2 and html.count('</script>')==2
    assert '<img src=x' not in html and 'connect-src' in html and "default-src 'none'" in html
    data=json.loads(re.search(r'<script id="evidence" type="application/json">(.*?)</script>',html,re.S)[1])
    assert data['metadata']['study_name']==label and 'textContent' in html and 'innerHTML' not in html


@pytest.mark.parametrize('value',["=1+1"," +SUM(A1)","-cmd|x","@SUM(A1)","\tplain","\rplain","\nplain"])
def test_spreadsheet_text_is_escaped_but_numeric_losses_remain_numeric(value):
    assert exports._cell(value)=="'"+value
    assert exports._cell(-12.5)==-12.5 and exports._cell(0)==0 and exports._cell(None) is None


@pytest.mark.parametrize('fault',['missing','changed'])
def test_all_export_routes_refuse_damaged_original_financial_accounts(saved,fault):
    lab,qid,fid=saved;source=exports.inspect_export_source(lab,fid);record,path=next(exports.original_accounts(lab,source));before=counts(lab)
    if fault=='missing':path.unlink()
    else:path.write_bytes(b'changed original bytes')
    with client(lab) as c:
        for tail in ['funnel-export/html','funnel-export/zip','funnel-export/csv','funnel-evidence/versions']:
            response=c.get('/api/jobs/'+fid+'/'+tail);assert response.status_code==409,response.text
    assert counts(lab)==before


def test_cancel_during_serialization_removes_temporary_export_and_preserves_original_jobs(saved,monkeypatch):
    lab,qid,fid=saved;before=counts(lab);original=exports.records;stop={'value':False}
    def canceled(*args,**kwargs):
        for row in original(*args,**kwargs):yield row;stop['value']=True
    monkeypatch.setattr(exports,'records',canceled)
    with pytest.raises(InterruptedError):exports.build_export(lab,fid,'html',cancel=lambda:stop['value'])
    assert counts(lab)==before and not list((lab.root/'data/exports').iterdir())


def test_closing_original_change_cannot_publish_partial_export_or_page(saved,monkeypatch):
    lab,qid,fid=saved;original=exports.records;path=lab.output_path(fid);before=path.read_bytes();changed={'value':False}
    def changed_source(*args,**kwargs):
        for row in original(*args,**kwargs):
            yield row
            if not changed['value']:path.write_bytes(b'changed after original inspection');changed['value']=True
    monkeypatch.setattr(exports,'records',changed_source)
    try:
        with pytest.raises(StateError):exports.build_export(lab,fid,'csv')
        assert not list((lab.root/'data/exports').iterdir())
        path.write_bytes(before);changed['value']=False
        with pytest.raises(StateError):exports.export_page(lab,fid)
    finally:path.write_bytes(before)


@pytest.mark.parametrize('format,table',[('bad',None),('csv','bad'),('html','versions'),('zip','accounts')])
def test_unsupported_or_ignored_export_settings_are_refused_before_work(saved,format,table):
    lab,qid,fid=saved;before=counts(lab)
    with pytest.raises(StateError):exports.build_export(lab,fid,format,table=table)
    assert counts(lab)==before


@pytest.mark.parametrize('limit,offset',[(0,0),(101,0),(True,0),(1,-1)])
def test_page_boundaries_do_not_return_partial_or_ambiguous_evidence(saved,limit,offset):
    lab,qid,fid=saved
    with pytest.raises(StateError):exports.export_page(lab,fid,limit=limit,offset=offset)
