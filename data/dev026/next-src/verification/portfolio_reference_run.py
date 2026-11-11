"""Independent historical joint-account differential on actual saved signals.

The Decimal execution oracle imports no production logic. The data adapter and
saved signals here do not independently certify detection, corporate-action
completeness, trading edge, all portfolio options, or the operating envelope.
"""
from pathlib import Path
from decimal import Decimal
from types import SimpleNamespace
import hashlib
import json
import math
import os
import statistics
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from backend.lab.config import identity
from backend.lab.data import read_manifest,load_window,prepare,Action
from backend.lab.research import core_hash
from backend.lab.service import Lab
from test_reference_execution import primitive,assert_parity
from verification.reference_execution import execute


def main():
    lab=Lab(ROOT);folder=Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'portfolio-reference';folder.mkdir(parents=True)
    comparisons=[]
    for name in sys.argv[1:]:
        path=(ROOT/name).resolve();path.relative_to(ROOT)
        report=json.loads(path.read_text(encoding='utf-8'))
        assert report['report_type']=='shared_capital_portfolio' and report['core_hash']==core_hash()
        manifest=read_manifest(lab.datasets_root,report['dataset_id'])
        assert identity(manifest)==report['dataset_manifest_hash']
        start=report['provenance']['warmup_start'];end=report['end']
        lab.guard.access(manifest['quality']['symbols'],start,end,'portfolio_reference_verification')
        frame,_=load_window(lab.datasets_root,report['dataset_id'],start,end)
        actions=[Action(**a) for a in manifest['actions'] if start<=a['ex_date']<=end]
        regular=prepare(frame,actions)
        configs={c['config_id']:c['config'] for c in report['configurations']}
        assert all(identity(c)==cid for cid,c in configs.items())
        expected=execute(primitive(regular),report['signals'],configs,report['costs'],report['portfolio'],
            [a.__dict__ for a in actions],report['start'],report['end'])
        output={'scope':'Supplied-signal shared-account execution/accounting and basic metric differential, not detector or trading-edge certification.',
            'report_file':path.relative_to(ROOT).as_posix(),'report_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'core_hash':report['core_hash'],'dataset_manifest_hash':report['dataset_manifest_hash'],
            'actual':{k:report[k] for k in ['trades','ledger','equity','rejected']},'reference':expected,'status':'comparison_pending'}
        target=folder/(path.parent.name+'.json')
        target.write_text(json.dumps(output,default=str,indent=2),encoding='utf-8')
        assert_parity(SimpleNamespace(**report),expected)
        capital=Decimal(str(report['portfolio']['capital']))
        values=[capital,*[r['equity'] for r in expected['equity']]]
        returns=[float((b-a)/a) for a,b in zip(values,values[1:])]
        deviation=statistics.stdev(returns) if len(returns)>1 else 0
        sharpe=statistics.mean(returns)/deviation*math.sqrt(252) if deviation else None
        high=capital;drawdown=Decimal(0)
        for value in values: high=max(high,value);drawdown=max(drawdown,(high-value)/high)
        profits=[t['net_pnl'] for t in expected['trades']]
        gain=sum((v for v in profits if v>0),Decimal(0));loss=-sum((v for v in profits if v<0),Decimal(0))
        daily=[b-a for a,b in zip(values,values[1:])]
        independent={'net_profit':values[-1]-capital,'total_return':values[-1]/capital-1,
            'marked_sharpe':sharpe,'max_drawdown':drawdown,'trades':len(profits),
            'win_rate':sum(p>0 for p in profits)/len(profits) if profits else None,
            'profit_factor':gain/loss if loss else None,'profit_without_ten_best_days':sum(daily)-sum(sorted(daily)[-min(10,len(daily)):])}
        metrics=[]
        for key,value in independent.items():
            actual=report['metrics'][key]
            difference=None if value is None else abs(Decimal(str(actual))-Decimal(str(value)))
            assert (actual is None if value is None else difference<=Decimal('1e-7')),(key,actual,str(value))
            metrics.append({'metric':key,'actual':actual,'reference':str(value),'absolute_difference':str(difference)})
        for row in report['attribution']:
            own=[t for t in expected['trades'] if t['strategy_id']==row['config_id']]
            assert len(own)==row['trades']
            for field,source in [('closed_trade_net_profit','net_pnl'),('fees','fees'),('borrow','borrow'),('distributions','distributions')]:
                assert abs(Decimal(str(row[field]))-sum((t[source] for t in own),Decimal(0)))<=Decimal('1e-7')
        usage={}
        for event in report['ledger']:
            if event['kind']!='entry': continue
            key=(event['symbol'],event['liquidity_reference_at']);before=usage.get(key,0)
            assert event['entry_volume_before']==before
            usage[key]=before+event['quantity']
            limit=int(Decimal(str(event['liquidity_reference_volume']))*Decimal(str(report['portfolio']['participation'])))
            assert event['entry_volume_after']==usage[key]<=event['entry_volume_limit']==limit
        output.update(status='pass',metric_comparisons=metrics,entry_budget_samples=len(usage))
        target.write_text(json.dumps(output,default=str,indent=2),encoding='utf-8')
        comparisons.append({'file':path.relative_to(ROOT).as_posix(),'trades':len(profits),'ledger_events':len(expected['ledger']),
            'equity_points':len(expected['equity']),'net_profit':str(independent['net_profit']),'entry_budget_samples':len(usage)})
    assert comparisons,'At least one actual portfolio report is required.'
    print(json.dumps({'scope':'Actual supplied-signal historical portfolio comparisons; not full acceptance.','comparisons':comparisons},indent=2))

if __name__=='__main__': main()
