"""Independent saved-signal lending account and downloaded scenario/presenter reconciliation.
This does not independently certify detector omissions or historical lending conditions.
"""
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo
import hashlib,json,os,re,statistics,math,struct,sys
root=Path.cwd();sys.path[:0]=[str(root),str(root/'tests')]
from backend.lab.service import Lab
from backend.lab.config import canonical,identity
from backend.lab.research import core_hash
from backend.lab.data import read_manifest,load_window,prepare,Action
from backend.lab.presentation_audit import audit_deck
from test_reference_execution import primitive,assert_parity
from verification.reference_execution import execute
browser=(root/sys.argv[1]).resolve();browser.relative_to(root)
lab=Lab(root/'data/sensitivity-browser-instance');rows=[]
for observation in sorted((browser/'artifacts').glob('*/borrow-observations.json')):
    folder=observation.parent;observed=json.loads(observation.read_text(encoding='utf-8'))
    report=lab.report(observed['job_id']);download=json.loads((folder/'downloaded-borrow-account.json').read_text(encoding='utf-8'))
    assert download==report and report['core_hash']==core_hash()
    scenario=report['costs']['borrow_scenario'];assert scenario==observed['scenario'] and scenario['mode']=='synthetic'
    assert json.loads((folder/'downloaded-borrow-scenario.json').read_text(encoding='utf-8'))==scenario
    recalls=[]
    for trade in report['trades']:
        at=datetime.fromisoformat(trade['entry_at'])
        applicable=sorted([e for e in scenario['events'] if e['symbol']==trade['symbol'] and datetime.fromisoformat(e['effective_at'])<=at],key=lambda e:e['effective_at'])
        available=applicable[-1]['available'] if applicable else report['costs']['borrow_available']
        recalled=applicable[-1]['recall'] if applicable else False
        if trade['side']<0:assert available and not recalled
        if trade['exit_reason']=='borrow_recall':
            exit_at=datetime.fromisoformat(trade['exit_at'])
            assert trade['side']==-1 and trade['borrow']>0
            assert any(e['symbol']==trade['symbol'] and e['recall'] and at<=datetime.fromisoformat(e['effective_at'])<=exit_at for e in scenario['events'])
            recalls.append(trade)
    assert recalls and len(recalls)==len(observed['recalls'])
    manifest=read_manifest(lab.datasets_root,report['dataset_id']);assert identity(manifest)==report['dataset_manifest_hash']
    lab.guard.access(manifest['quality']['symbols'],report['start'],report['end'],'news_saved_signal_reference_verification')
    prices,_=load_window(lab.datasets_root,report['dataset_id'],report['start'],report['end'])
    actions=[Action(**a) for a in manifest['actions']];regular=prepare(prices,actions)
    expected=execute(primitive(regular),[s|dict(config_id=report['config_id']) for s in report['signals']],
        {report['config_id']:report['config']},report['costs'],report['portfolio'],[a.__dict__ for a in actions],report['start'],report['end'])
    assert_parity(SimpleNamespace(**report),expected)
    capital=Decimal(str(report['portfolio']['capital']));equities=[capital,*[r['equity'] for r in expected['equity']]]
    returns=[float((b-a)/a) for a,b in zip(equities,equities[1:])]
    profits=[t['net_pnl'] for t in expected['trades']];high=capital;worst=Decimal(0)
    for value in equities:high=max(high,value);worst=max(worst,(high-value)/high)
    daily=[b-a for a,b in zip(equities,equities[1:])]
    reference=dict(net_profit=equities[-1]-capital,total_return=equities[-1]/capital-1,
        marked_sharpe=statistics.mean(returns)/statistics.stdev(returns)*math.sqrt(252),max_drawdown=worst,
        trades=len(profits),win_rate=sum(v>0 for v in profits)/len(profits),
        profit_without_ten_best_days=sum(daily)-sum(sorted(daily)[-min(10,len(daily)):]))
    for key,value in reference.items():
        tolerance=Decimal('1e-7' if key in {'net_profit','profit_without_ten_best_days'} else '1e-10')
        assert abs(Decimal(str(report['metrics'][key]))-Decimal(str(value)))<=tolerance,(key,report['metrics'][key],str(value))
    document=(folder/'borrow-presentation.html').read_text(encoding='utf-8')
    deck=json.loads(re.search(r'<script id="presentation-manifest" type="application/json">(.*?)</script>',document,re.S).group(1))
    sources={}
    for source in deck['sources']:
        jid,filename=source['name'].split('/');assert jid==observed['job_id'] and filename=='report.json'
        sources[source['name']]=canonical(report).encode()
    audit=audit_deck(sources,deck)
    assert len(deck['pages'])==observed['pages']==len(observed['layouts']) and all(v==[] for v in observed['layouts'])
    assert observed['networkRequests']==observed['consoleErrors']==[]
    images=[]
    for index in range(len(deck['pages'])):
        path=folder/('borrow-presentation-'+str(index+1)+'.png');raw=path.read_bytes();assert raw[:8]==b'\x89PNG\r\n\x1a\n'
        width,height=struct.unpack('>II',raw[16:24]);assert dict(width=width,height=height)==observed['viewport']
        images.append(dict(path=path.relative_to(root).as_posix(),sha256=hashlib.sha256(raw).hexdigest()))
    rows.append(dict(profile=folder.name,job_id=observed['job_id'],core_hash=report['core_hash'],scenario_id=identity(scenario),
        recalls=[{k:t[k] for k in ['id','symbol','entry_at','exit_at','exit_reason','borrow']} for t in recalls],
        signals=len(report['signals']),trades=len(expected['trades']),ledger_events=len(expected['ledger']),daily_marks=len(expected['equity']),
        independent_metrics={k:str(v) for k,v in reference.items()},presenter_audit=audit,screenshots=images))
assert len(rows)==2
output=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
(output/'borrow-independent-reconciliation.json').write_text(json.dumps(dict(scope=__doc__,profiles=rows),indent=2),encoding='utf-8')
print(json.dumps(dict(profiles=len(rows),accounts_reconciled=len(rows),page_screenshots=sum(len(r['screenshots']) for r in rows),
    facts_checked=[r['presenter_audit'] for r in rows],metrics=[r['independent_metrics'] for r in rows]),indent=2))
