"""Complete saved-only cohort projections, CSV and self-contained evidence.

No financial or qualification arithmetic runs here. Original inspectors remain
authority; every projection preserves frozen membership and unavailable values.
"""
from itertools import islice
from io import StringIO
from pathlib import Path
import csv
import hashlib
import html
import json
import os
import uuid
import zipfile

from .config import canonical,identity
from .research import require_current_source,checked_saved_read
from .store import StateError
from .research_family_source import file_hash,_root_event
from .research_funnel_arms import _study
from .research_funnel import SOURCE_VIDEO

TABLES=('metadata','versions','accounts','gates','family_summary','family_daily','family_members','stability','attrition','original_accounts')
COLUMNS={
    'metadata':('key','value_json'),
    'versions':('part','config_id','family','timeframe','candidate','family_passed','prequalified','controls_required','control_state','configuration_json'),
    'accounts':('part','config_id','arm','symbol','start','end','signal_count','trades','net_profit','marked_sharpe','positive_profit','final_gate_pass','computed_sha256'),
    'gates':('part','config_id','gate','state','observed','comparison','threshold','passed','record_json'),
    'family_summary':('family','arm','state','version_count','family_preselected','convention','sessions','net_profit_numerator','net_profit_denominator','annualized_profit','sharpe','gate_pass','risk_basis'),
    'family_daily':('family','arm','convention','date','mean_pnl_numerator','mean_pnl_denominator'),
    'family_members':('family','arm','config_id','computed_sha256'),
    'stability':('config_id','neighbors','available','missing','positive','undefined_sharpe','mean_net_profit_numerator','mean_net_profit_denominator','sample_variance_net_profit_numerator','sample_variance_net_profit_denominator','coordinate_counts_json'),
    'attrition':('gate','entering','passing','removed','unavailable','not_required','ineligible','confirmed_passing_prefix','cohort_json'),
    'original_accounts':('arm','part','config_id','original_job_id','artifact_sha256','archive_path'),
}
COMMON=('job_id','kind','study_id','core_hash','configuration_universe_hash','source_root_sha256','candidate_freeze_hash')


def _cancel(cancel):
    if cancel and cancel():raise InterruptedError('Saved evidence export canceled; no partial export certified.')


@checked_saved_read
def inspect_export_source(lab,jid,cancel=None):
    from .research_funnel_jobs import inspect_qualification
    from .research_funnel_final import inspect_final
    _cancel(cancel);require_current_source();kind=lab.store.job_status(jid)['kind']
    if kind not in {'funnel_qualification','funnel_final'}:raise StateError('Choose an original complete research-funnel result.')
    value=(inspect_qualification if kind=='funnel_qualification' else inspect_final)(lab,jid,cancel=cancel)
    with lab.store.db() as db:
        db.execute('BEGIN');job,digest,_=lab.store._input_index.verified_inputs(jid,db)
        study=_study(lab,db,job['payload']['study_id']);event,root_sha=_root_event(db,jid)
    spec=study['spec'];freeze=value['candidate_freeze'] if kind=='funnel_qualification' else None
    generation=spec.get('cohort_generation',{})
    metadata=dict(export_version=1,job_id=jid,kind=kind,study_id=study['id'],study_name=study['name'],core_hash=value['core_hash'],
        configuration_universe_hash=spec['configuration_universe_hash'],source_root_sha256=root_sha,source_result_event_id=event,
        source_payload_hash=digest,source_computed_sha256=identity(value),candidate_freeze_hash=identity(freeze) if freeze else value['candidate_freeze_hash'],
        version_count=len(spec['configurations']),source_video=SOURCE_VIDEO,host_engine_parity_verified=False,
        primary_symbol=spec['primary_symbol'],replication_symbol=spec['replication_symbol'],final_cohort_policy=spec['final_cohort_policy'],
        candidate_count=len(freeze['candidate_ids']) if freeze else value['report']['candidate_count'],
        frozen_assumptions={k:spec[k] for k in ['costs','portfolio','seed','discovery','era_one','era_two','validation','holdout','qualification_policy','stability_policy','control_scheduling_policy','dataset_context','replication_dataset_context','news_calendar_id'] if k in spec},
        cohort_generation=dict(settings=generation.get('settings'),recipe_hash=generation.get('sampling',{}).get('recipe_hash'),host_private_recipe_reproduced=False),
        instrument_replication_adaptation=spec['instrument_replication_adaptation'],
        original_evidence_verified=True,financial_accounts_recomputed=0,qualification_math_recomputed=False,
        csv_text_escape='Text beginning with spreadsheet formula characters is prefixed with an apostrophe; numeric values are unchanged. Null is an empty CSV cell; JSON retains null.',
        offline_scope='All cohort summary tables and exact family daily means. The ZIP additionally retains complete original result, frozen inputs and phase account files, including per-version daily arrays and trade evidence.',
        table_availability={name:kind=='funnel_qualification' or name not in {'gates','stability','attrition'} for name in TABLES})
    _cancel(cancel);return dict(value=value,job=job,study=study,metadata=metadata)


def _families(source):
    value=source['value'];report=value['report'];final=value['kind']=='funnel_final'
    if final:
        frozen={row['config']['family'] for row in value['rows'] if row['family_passed']}
        for arm,summary in report['arms'].items():
            for family,average in summary['families'].items():yield family,arm,average,family in frozen
    else:
        for family,summary in report['families'].items():
            for arm,average in summary['axes'].items():yield family,arm,average,summary['passed']


def original_accounts(lab,source):
    value=source['value'];jid=source['job']['id']
    if value['kind']=='funnel_final':
        from .research_funnel_final import _path
        for row in value['rows']:
            for arm,record in row['reports'].items():
                path,_=_path(lab,jid,row['part'],arm)
                yield dict(arm=arm,part=row['part'],config_id=row['config_id'],original_job_id=jid,
                    artifact_sha256=record['report_sha256'],archive_path='accounts/'+arm+'/'+str(row['part']).zfill(6)+'.json.gz'),path
    else:
        for arm,binding in value['report']['source_authority']['arms'].items():
            for part in binding['parts']:
                path=lab.output_path(binding['job_id']).parent/'parts'/(str(part['part']).zfill(6)+'.json.gz')
                yield dict(arm=arm,part=part['part'],config_id=part['config_id'],original_job_id=binding['job_id'],
                    artifact_sha256=part['report_sha256'],archive_path='accounts/'+arm+'/'+str(part['part']).zfill(6)+'.json.gz'),path


def records(lab,source,table,cancel=None):
    if table not in TABLES:raise StateError('Choose a complete saved evidence table.')
    value=source['value'];report=value['report'];final=value['kind']=='funnel_final'
    if table=='metadata':
        for key,val in source['metadata'].items():yield dict(key=key,value_json=canonical(val))
    elif table=='versions':
        for part,row in enumerate(value['rows'] if final else report['rows']):
            _cancel(cancel);config=row['config' if final else 'configuration']
            yield dict(part=part,config_id=row['config_id'],family=config['family'],timeframe=config['timeframe'],
                **{k:row.get(k) for k in ['candidate','family_passed','prequalified','controls_required','control_state']},configuration_json=canonical(config))
    elif table=='accounts':
        for part,row in enumerate(value['rows'] if final else report['rows']):
            for arm,account in row['reports' if final else 'accounts'].items():
                _cancel(cancel);scope=source['study']['spec']['final_arms' if final else 'development_arms'][arm]
                m=account['metrics'] if final else account
                yield dict(part=part,config_id=row['config_id'],arm=arm,symbol=scope['symbol'],start=scope['start'],end=scope['end'],
                    **{k:m.get(k) if m is not None else None for k in ['signal_count','trades','net_profit','marked_sharpe','positive_profit']},
                    final_gate_pass=account.get('final_gate_pass') if final else None,
                    computed_sha256=account.get('computed_sha256' if final else 'report_hash') if account is not None else None)
    elif table=='gates' and not final:
        for part,row in enumerate(report['rows']):
            for gate,record in row['gates'].items():
                _cancel(cancel);yield dict(part=part,config_id=row['config_id'],gate=gate,**{k:record.get(k) for k in ['state','observed','comparison','threshold','passed']},record_json=canonical(record))
    elif table in {'family_summary','family_daily','family_members'}:
        for family,arm,average,passed in _families(source):
            if table=='family_members':
                for cid in average['members']:
                    _cancel(cancel);yield dict(family=family,arm=arm,config_id=cid,computed_sha256=average.get('source_report_hashes',{}).get(cid))
            else:
                for convention in ['marked','realized_exit_day_compatibility']:
                    stats=average.get(convention)
                    if table=='family_summary':
                        _cancel(cancel);fraction=(stats or {}).get('net_profit') or {}
                        yield dict(family=family,arm=arm,state=average['state'],version_count=average['version_count'],family_preselected=passed,convention=convention,
                            net_profit_numerator=fraction.get('numerator'),net_profit_denominator=fraction.get('denominator'),
                            **{k:stats.get(k) if stats is not None else None for k in ['sessions','annualized_profit','sharpe','gate_pass','risk_basis']})
                    else:
                        for day in (stats or {}).get('daily',[]):
                            _cancel(cancel);yield dict(family=family,arm=arm,convention=convention,date=day['date'],mean_pnl_numerator=day['mean_pnl']['numerator'],mean_pnl_denominator=day['mean_pnl']['denominator'])
    elif table=='stability' and not final:
        for row in report['stability']['rows']:
            _cancel(cancel);result={k:row[k] for k in ['config_id','neighbors','available','missing','positive','undefined_sharpe']}
            for name in ['mean_net_profit','sample_variance_net_profit']:
                for part in ['numerator','denominator']:result[name+'_'+part]=(row[name] or {}).get(part)
            yield result|dict(coordinate_counts_json=canonical(row['coordinate_counts']))
    elif table=='attrition' and not final:
        for row in report['attrition']:
            _cancel(cancel);yield {k:row[k] for k in COLUMNS[table] if k!='cohort_json'}|dict(cohort_json=canonical(row['cohort']))
    elif table=='original_accounts':
        for record,_ in original_accounts(lab,source):_cancel(cancel);yield record


def export_page(lab,jid,table='versions',limit=50,offset=0,*,cancel=None):
    if type(limit) is not int or not 1<=limit<=100 or type(offset) is not int or offset<0:raise StateError('Choose a saved evidence page of1 through100 rows and a nonnegative offset.')
    source=inspect_export_source(lab,jid,cancel);rows=[];total=0
    for total,record in enumerate(records(lab,source,table,cancel),1):
        if offset<total<=offset+limit:rows.append(record)
    _closing(lab,source,cancel)
    result=dict(job_id=jid,table=table,columns=COLUMNS[table],rows=rows,pagination=dict(limit=limit,offset=offset,total=total),
        available=source['metadata']['table_availability'][table],original_evidence_verified=True,source_root_sha256=source['metadata']['source_root_sha256'])
    if len(canonical(result).encode())>8*1024*1024:raise StateError('Evidence page exceeds8 MiB; request fewer rows.')
    _cancel(cancel);return result


def _cell(value):
    if isinstance(value,str) and (value[:1] in {'\t','\r','\n'} or value.lstrip().startswith(('=','+','-','@'))):return "'"+value
    return value


def csv_chunks(lab,source,table,cancel=None):
    fields=COMMON+COLUMNS[table];common={k:source['metadata'][k] for k in COMMON}
    buffer=StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=fields);writer.writeheader()
    yield buffer.getvalue().encode('utf-8')
    for row in records(lab,source,table,cancel):
        _cancel(cancel);buffer.seek(0);buffer.truncate(0);writer.writerow({k:_cell(v) for k,v in (common|row).items()})
        yield buffer.getvalue().encode('utf-8')


def _json_chunks(value):
    for chunk in json.JSONEncoder(sort_keys=True,separators=(',',':'),allow_nan=False).iterencode(value):yield chunk.encode('utf-8')


def html_chunks(lab,source,cancel=None):
    title=html.escape(source['metadata']['study_name'])
    yield (OFFLINE_HEAD.replace('%%TITLE%%',title)).encode('utf-8')
    def safe(chunks):
        for chunk in chunks:
            _cancel(cancel);yield chunk.replace(b'&',b'\\u0026').replace(b'<',b'\\u003c').replace(b'>',b'\\u003e')
    yield b'{"metadata":';yield from safe(_json_chunks(source['metadata']));yield b',"tables":{'
    for number,table in enumerate(TABLES):
        if number:yield b','
        yield from _json_chunks(table);yield b':{"columns":';yield from _json_chunks(COLUMNS[table]);yield b',"rows":['
        for index,row in enumerate(records(lab,source,table,cancel)):
            if index:yield b','
            yield from safe(_json_chunks([row.get(k) for k in COLUMNS[table]]))
        yield b']}'
    yield b'}}';yield OFFLINE_TAIL.encode('utf-8')


def _write(stream,chunks,cancel):
    digest=hashlib.sha256();size=0;buffer=bytearray()
    for chunk in chunks:
        _cancel(cancel);buffer.extend(chunk);digest.update(chunk);size+=len(chunk)
        if len(buffer)>=65536:stream.write(buffer);buffer.clear()
    if buffer:stream.write(buffer)
    return dict(sha256=digest.hexdigest(),bytes=size)


def _closing(lab,source,cancel):
    closing=inspect_export_source(lab,source['job']['id'],cancel)
    if closing['metadata']!=source['metadata']:raise StateError('Original evidence changed during export; no partial artifact certified.')


def build_export(lab,jid,format,*,table=None,cancel=None):
    if format not in {'csv','html','zip'} or table is not None and (format!='csv' or table not in TABLES):raise StateError('Choose CSV with a declared table, HTML or a complete ZIP bundle.')
    source=inspect_export_source(lab,jid,cancel);table=table or 'versions'
    folder=lab.root/'data'/'exports';folder.mkdir(parents=True,exist_ok=True)
    stem=uuid.uuid4().hex;partial=folder/(stem+'.partial');path=folder/(stem+'.'+format)
    try:
        if format=='zip':
            entries={}
            with zipfile.ZipFile(partial,'w',compression=zipfile.ZIP_DEFLATED,allowZip64=True) as archive:
                def add(name,chunks):
                    with archive.open(name,'w',force_zip64=True) as output:entries[name]=_write(output,chunks,cancel)
                add('original-result.json',_json_chunks(source['value']))
                add('original-study-inputs.json',_json_chunks(lab.store.study_inputs(source['study']['id'])))
                add('original-job-inputs.json',_json_chunks(lab.store.job_inputs(jid)))
                for name in TABLES:add(name+'.csv',csv_chunks(lab,source,name,cancel))
                add('index.html',html_chunks(lab,source,cancel))
                for record,account in original_accounts(lab,source):
                    _cancel(cancel)
                    with account.open('rb') as file,archive.open(record['archive_path'],'w',force_zip64=True) as output:
                        member=_write(output,iter(lambda:file.read(1024*1024),b''),cancel)
                    if member['sha256']!=record['artifact_sha256']:raise StateError('An original account changed during archive construction.')
                    entries[record['archive_path']]=member
                add('manifest.json',_json_chunks(dict(metadata=source['metadata'],entries=entries)))
        else:
            with partial.open('wb') as output:_write(output,csv_chunks(lab,source,table,cancel) if format=='csv' else html_chunks(lab,source,cancel),cancel)
        _closing(lab,source,cancel)
        _cancel(cancel);os.replace(partial,path)
        return dict(path=path,format=format,table=table if format=='csv' else None,metadata=source['metadata'])
    except BaseException as error:
        partial.unlink(missing_ok=True);path.unlink(missing_ok=True)
        if isinstance(error,(StateError,InterruptedError)):raise
        if isinstance(error,(OSError,ValueError,zipfile.BadZipFile)):
            raise StateError('Saved export could not finish; no partial evidence was certified.') from error
        raise


OFFLINE_HEAD='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"><title>%%TITLE%% - complete research evidence</title><style>body{background:#0c1422;color:#dde6f3;font:16px system-ui;margin:0;padding:clamp(16px,4vw,48px)}main{max-width:1500px;margin:auto}h1,h2{color:#7bdfeb}label{display:inline-flex;flex-direction:column;gap:8px;margin:10px 18px 10px 0}select,input,button{font:inherit;background:#16253a;color:inherit;border:1px solid #49617e;padding:10px;border-radius:5px;max-width:100%;box-sizing:border-box}button:disabled{opacity:.4}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}.scroll{overflow:auto;max-height:70vh;border:1px solid #49617e}table{border-collapse:collapse;font-size:13px}td,th{padding:10px;text-align:left;vertical-align:top;border-bottom:1px solid #263950;max-width:500px;overflow-wrap:anywhere}th{position:sticky;top:0;background:#16253a}a{color:#7bdfeb}.muted{color:#b4c2d7}nav{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:14px}</style></head><body><main><h1>%%TITLE%%</h1><h2>Complete frozen-cohort evidence</h2><p id="scope"></p><p class="muted">Research results do not guarantee future profitability. Both final instruments retain all frozen versions; candidate and family selection precede final results. The host private recipes and engine are not reproduced. Exact rational numbers remain text. Null means unavailable, never zero. This report computes no financial outcomes and makes no network requests.</p><a href="https://www.youtube.com/watch?v=z97PnFIPoFg" rel="noreferrer">Source YouTube video (opens an external page only when clicked)</a><details><summary>Frozen assumptions, original identities and export scope</summary><pre id="metadata"></pre></details><label>Evidence table<select id="table"></select></label><label>Find text in the complete table<input id="query" type="search"></label><p id="status" role="status"></p><div class="scroll" tabindex="0" role="region" aria-label="Complete saved evidence table"><table><thead id="head"></thead><tbody id="body"></tbody></table></div><nav><button id="previous" type="button">Previous50 records</button><button id="next" type="button">Next50 records</button></nav></main><script id="evidence" type="application/json">'''

OFFLINE_TAIL='''</script><script>'use strict';const evidence=JSON.parse(document.getElementById('evidence').textContent),selector=document.getElementById('table'),query=document.getElementById('query');let offset=0;const names={metadata:'Source and frozen assumptions',versions:'Every frozen version',accounts:'Every instrument account',gates:'Qualification gates and complete control counts',family_summary:'Complete family means',family_daily:'Exact family daily means',family_members:'Every original family member',stability:'Descriptive frozen-neighbor stability',attrition:'Qualification attrition and missingness',original_accounts:'Original account files and hashes'};document.getElementById('metadata').textContent=JSON.stringify(evidence.metadata,null,2);document.getElementById('scope').textContent=evidence.metadata.kind+' / '+evidence.metadata.version_count+' frozen versions / '+evidence.metadata.candidate_count+' preselected candidates. '+evidence.metadata.offline_scope;for(const key of Object.keys(evidence.tables)){const option=document.createElement('option');option.value=key;option.textContent=names[key];selector.append(option);}selector.value='versions';function text(value){return value===null?'Unavailable':typeof value==='object'?JSON.stringify(value):String(value);}function render(){const table=evidence.tables[selector.value],term=query.value.toLowerCase(),rows=term?table.rows.filter(row=>row.some(value=>text(value).toLowerCase().includes(term))):table.rows;const head=document.getElementById('head'),body=document.getElementById('body');head.replaceChildren();body.replaceChildren();const tr=document.createElement('tr');for(const name of table.columns){const th=document.createElement('th');th.textContent=name;tr.append(th);}head.append(tr);for(const row of rows.slice(offset,offset+50)){const tr=document.createElement('tr');for(const value of row){const td=document.createElement('td');td.textContent=text(value);tr.append(td);}body.append(tr);}document.getElementById('status').textContent=(evidence.metadata.table_availability[selector.value]?'Records '+(rows.length?offset+1:0)+' to '+Math.min(offset+50,rows.length)+' of '+rows.length+' matching records; '+table.rows.length+' complete saved records.':'This table does not apply to this final phase. Qualification gates/stability/attrition remain in the separately saved qualification export.');document.getElementById('previous').disabled=offset===0;document.getElementById('next').disabled=offset+50>=rows.length;}selector.addEventListener('change',()=>{offset=0;query.value='';render();});query.addEventListener('input',()=>{offset=0;render();});document.getElementById('previous').addEventListener('click',()=>{offset=Math.max(0,offset-50);render();});document.getElementById('next').addEventListener('click',()=>{offset+=50;render();});render();</script></body></html>'''
