"""Independent saved-signal accounts and four-rate export/presenter reconciliation.
This verifies execution/accounting under assumed lending, not detector omissions or trading edge.
"""
from pathlib import Path
from decimal import Decimal
from types import SimpleNamespace
import csv,hashlib,json,math,os,re,statistics,struct,sys
root=Path.cwd();sys.path[:0]=[str(root),str(root/'tests')]
from backend.lab.service import Lab
from backend.lab.config import canonical,identity
from backend.lab.research import core_hash
from backend.lab.data import read_manifest,load_window,prepare,Action
from backend.lab.presentation_audit import audit_deck
from test_reference_execution import primitive,assert_parity
from verification.reference_execution import execute
browser=(root/sys.argv[1]).resolve();browser.relative_to(root)
lab=Lab(root);records=[]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def close(actual,expected,tol='1e-7'):assert abs(Decimal(str(actual))-Decimal(str(expected)))<=Decimal(tol),(actual,str(expected))
def nonrates(costs):
    value=json.loads(json.dumps(costs));value.pop('borrow_annual')
    if value.get('borrow_scenario'):
        for event in value['borrow_scenario']['events']:event.pop('annual_rate')
    return value
for observation in sorted((browser/'artifacts').glob('*/sensitivity-observations.json')):
    folder=observation.parent;observed=read(observation);jid=observed['job_id'];report=lab.report(jid)
    assert read(folder/'comparison.json')==report and report['core_hash']==core_hash()
    manifest=read_manifest(lab.datasets_root,report['dataset_id']);assert identity(manifest)==report['dataset_manifest_hash']
    lab.guard.access(manifest['quality']['symbols'],report['start'],report['end'],'four_rate_saved_signal_reference')
    prices,_=load_window(lab.datasets_root,report['dataset_id'],report['start'],report['end'])
    actions=[Action(**a) for a in manifest['actions']];regular=prepare(prices,actions)
    books=[];references=[];outcomes=[]
    for part,rate in enumerate([0,.03,.1,.3]):
        book=lab.report(jid,part);assert read(folder/('account-'+str(part)+'.json'))==book
        assert book['core_hash']==report['core_hash'] and book['costs']==report['arms'][part]['costs']
        assert book['costs']['borrow_annual']==rate and all(e['annual_rate']==rate for e in book['costs']['borrow_scenario']['events'])
        assert nonrates(book['costs'])==nonrates(report['original_costs'])
        assert book['config']==report['config'] and book['signals']==(books[0]['signals'] if books else book['signals'])
        expected=execute(primitive(regular),[s|dict(config_id=book['config_id']) for s in book['signals']],{book['config_id']:book['config']},book['costs'],book['portfolio'],[a.__dict__ for a in actions],book['start'],book['end'])
        assert_parity(SimpleNamespace(**book),expected)
        assert any(t['side']<0 for t in expected['trades'])
        capital=Decimal(str(book['portfolio']['capital']));equities=[capital,*[r['equity'] for r in expected['equity']]]
        returns=[float((b-a)/a) for a,b in zip(equities,equities[1:])];daily=[b-a for a,b in zip(equities,equities[1:])]
        high=capital;worst=Decimal(0)
        for value in equities:high=max(high,value);worst=max(worst,(high-value)/high)
        profits=[t['net_pnl'] for t in expected['trades']]
        metrics=dict(net_profit=equities[-1]-capital,total_return=equities[-1]/capital-1,max_drawdown=worst,trades=len(profits),win_rate=sum(v>0 for v in profits)/len(profits),marked_sharpe=statistics.mean(returns)/statistics.stdev(returns)*math.sqrt(252),profit_without_ten_best_days=sum(daily)-sum(sorted(daily)[-min(10,len(daily)):]))
        for key,value in metrics.items():close(book['metrics'][key],value,'1e-7' if key in {'net_profit','profit_without_ten_best_days'} else '1e-10')
        close(report['comparison_rows'][part]['borrow_paid'],sum(t['borrow'] for t in expected['trades']))
        close(report['comparison_rows'][part]['fees_paid'],sum(t['fees'] for t in expected['trades']))
        with (folder/('account-'+str(part)+'.csv')).open(encoding='utf-8',newline='') as f:csvrows=list(csv.DictReader(f))
        assert len(csvrows)==len(book['trades'])
        for a,b in zip(csvrows,book['trades']):
            assert a['id']==b['id'];close(a['net_pnl'],b['net_pnl']);close(a['borrow'],b['borrow'])
        references.append(daily);books.append(book)
        outcomes.append(dict(part=part,rate=rate,signals=len(book['signals']),trades=len(expected['trades']),short_trades=sum(t['side']<0 for t in expected['trades']),ledger_events=len(expected['ledger']),daily_marks=len(expected['equity']),independent_metrics={k:str(v) for k,v in metrics.items()}))
    for part,days in enumerate(references):
        difference=report['daily_differences'][part]['rows'];assert len(difference)==len(days)
        for row,base,value,equity in zip(difference,references[0],days,books[part]['equity']):
            assert row['date']==equity['date'];close(row['baseline_profit'],base);close(row['scenario_profit'],value);close(row['difference'],value-base)
        close(report['comparison_rows'][part]['delta_from_zero'],sum(days)-sum(references[0]))
    with (folder/'comparison.csv').open(encoding='utf-8',newline='') as f:csvrows=list(csv.DictReader(f))
    assert len(csvrows)==4
    for a,b in zip(csvrows,report['comparison_rows']):
        for key in ['annual_rate','net_profit','delta_from_zero','borrow_paid','fees_paid']:close(a[key],b[key])
    registry=read(folder/'trial-registry.json');assert len(registry['rows'])==4
    assert {r['config_id'] for r in registry['rows']}=={a['account_id'] for a in report['arms']}
    assert all(r['state']=='completed' for r in registry['rows'])
    audits=[]
    for filename,source_report in [('sensitivity-presentation.html',report),('selected-account-presentation.html',books[3])]:
        document=(folder/filename).read_text(encoding='utf-8');deck=json.loads(re.search(r'<script id="presentation-manifest" type="application/json">(.*?)</script>',document,re.S).group(1))
        assert len(deck['sources'])==1
        audit=audit_deck({deck['sources'][0]['name']:canonical(source_report).encode()},deck)
        audits.append(dict(file=filename,audit=audit,pages=len(deck['pages'])))
    assert len(deck['sources'])==1 and observed['pages']==audits[0]['pages']==len(observed['layouts'])
    assert all(v==[] for v in observed['layouts']) and observed['networkRequests']==observed['consoleErrors']==[]
    screenshots=[]
    for index in range(observed['pages']):
        path=folder/('sensitivity-presentation-'+str(index+1)+'.png');raw=path.read_bytes();assert raw[:8]==b'\x89PNG\r\n\x1a\n'
        width,height=struct.unpack('>II',raw[16:24]);assert dict(width=width,height=height)==observed['viewport']
        screenshots.append(dict(path=path.relative_to(root).as_posix(),sha256=hashlib.sha256(raw).hexdigest()))
    records.append(dict(profile=folder.name,job_id=jid,core_hash=report['core_hash'],accounts=outcomes,presentations=audits,screenshots=screenshots))
assert len(records)==2 and {r['profile'].split('-')[-1] for r in records}=={'desktop1920','desktop1280'}
output=Path(os.environ['PA_EVIDENCE_RUN_DIR']);(output/'independent-sensitivity-accounts.json').write_text(json.dumps(dict(scope=__doc__,profiles=records),indent=2),encoding='utf-8')
print(json.dumps(dict(profiles=len(records),complete_independent_accounts=sum(len(r['accounts']) for r in records),offline_pages=sum(r['presentations'][0]['pages'] for r in records),scope=__doc__)))
