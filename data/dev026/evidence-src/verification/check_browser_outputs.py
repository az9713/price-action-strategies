"""Independently reread actual browser artifacts; not a replacement UI test."""
from pathlib import Path
import hashlib
import json
import struct
import sys
import csv
import math
from decimal import Decimal
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from backend.lab.config import identity
from backend.lab.data import read_manifest
from backend.lab.service import Lab
from backend.lab.research import core_hash

def main():
    folder=(ROOT/(sys.argv[1] if len(sys.argv)>1 else 'verification/runs/browser-local-regression')).resolve()
    folder.relative_to(ROOT.resolve())
    built=json.loads((ROOT/'verification/runs/frontend-build.json').read_text(encoding='utf-8'))['files']
    suites=list(ET.parse(folder/'junit.xml').iter('testsuite'))
    expected_flows=int(sys.argv[2]) if len(sys.argv)>2 else 2
    assert expected_flows in {2,4,6,8,10,12}
    reference_control_job=sys.argv[3] if len(sys.argv)>3 else None
    assert sum(int(s.attrib['tests']) for s in suites)==expected_flows
    assert sum(int(s.attrib.get('failures',0))+int(s.attrib.get('errors',0))+int(s.attrib.get('skipped',0)) for s in suites)==0
    lab=Lab(ROOT);rows=[]
    files=list((folder/'artifacts').glob('*/observations.json'))
    if expected_flows>=10:files=[p for p in files if not (p.parent/'behavior-study.json').exists() and not (p.parent/'ablation-study.json').exists()]
    assert len(files)==(8 if expected_flows>=10 else expected_flows)
    for name,digest in built.items(): assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    for observation in files:
        value=json.loads(observation.read_text(encoding='utf-8'))
        report=lab.report(value['job_id'])
        kind=report.get('report_type')
        passive=kind=='passive_benchmarks';controls=kind=='matched_random_controls'
        assert report['core_hash']==core_hash(), 'Saved engine differs from the current process.'
        assert 'frontend/dist/'+value['bundle'].lstrip('/') in built, 'Browser bundle differs from the current built artifact.'
        filename='benchmark-report.json' if passive else ('control-study.json' if controls else 'downloaded-report.json')
        downloaded=json.loads((observation.parent/filename).read_text(encoding='utf-8'))
        assert downloaded==report
        book=report['benchmarks']['buy_hold'] if passive else report
        csv_file='benchmark-trades.csv' if passive else ('control-trades.csv' if controls else value.get('csv_file'))
        if controls:
            book=lab.report(value['job_id'],value['selected_part'])
            assert json.loads((observation.parent/'control-account.json').read_text(encoding='utf-8'))==book
            assert reference_control_job,'Provide the independently audited default20 control job ID.'
            reference=lab.report(reference_control_job)
            assert reference['core_hash']==core_hash() and reference['replicas_requested']==20
            assert reference['matching']['matched_source_ids']==report['matching']['matched_source_ids']
            assert reference['matching']['replicas'][:report['replicas_requested']]==report['matching']['replicas']
            assert book==lab.report(reference_control_job,value['selected_part'])
            assert report['matching']['source_count']==report['matching']['matched_count']+len(report['matching']['unmatched'])
        if csv_file:
            assert csv_file==('benchmark-trades.csv' if passive else 'control-trades.csv' if controls else 'downloaded-trades.csv')
            with (observation.parent/csv_file).open(encoding='utf-8',newline='') as handle:
                exported=list(csv.DictReader(handle))
            assert len(exported)==len(book['trades'])
            for row,trade in zip(exported,book['trades']):
                for key in ['id','symbol','entry_at','exit_at']+([] if passive else ['strategy_id']): assert row[key]==trade[key]
                for key in ['entry_price','exit_price','entry_quantity','exit_quantity','net_pnl','fees','borrow','distributions']:
                    assert abs(Decimal(row[key])-Decimal(str(trade[key])))<=Decimal('1e-9' if key in {'entry_price','exit_price','entry_quantity','exit_quantity'} else '1e-7')
        manifest=read_manifest(lab.datasets_root,report['dataset_id'])
        assert report['dataset_manifest_hash']==identity(manifest)
        assert report['provenance']['input_kind']=='historical_market_data'
        assert book['trades'] and {t['side'] for t in book['trades']}==({1} if passive else {-1,1})
        if report.get('report_type')=='shared_capital_portfolio':
            assert len(report['configurations'])==2 and len(report['attribution'])==2
            assert sum(r['trades'] for r in report['attribution'])==len(report['trades'])
            assert {r['config']['timeframe'] for r in report['configurations']}=={'1h','15m'}
        elif passive:assert len(book['trades'])==5 and report['benchmarks']['cash']['metrics']['net_profit']==0
        elif not controls:assert len(report['trades'])==10
        trade_net=sum(t['net_pnl'] for t in book['trades'])
        discrepancy=abs(trade_net-book['metrics']['net_profit']);assert discrepancy<1e-7
        assert value.get('consoleErrors',value.get('console_errors'))==[]
        shots=[]
        for name in value.get('captures',['data','strategies','experiment','results','trade-inspector','validation','reports']):
            if name.endswith('.png'):name=name[:-4]
            assert '/' not in name and '\\' not in name and '..' not in name
            path=observation.parent/(name+'.png');raw=path.read_bytes()
            assert raw[:8]==b'\x89PNG\r\n\x1a\n'
            width,height=struct.unpack('>II',raw[16:24])
            assert (width<=value['viewport']['width'] if name in {'benchmark-panel','controls-panel'} else width==value['viewport']['width']) and height>=value['viewport']['height']
            shots.append({'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(raw).hexdigest(),'width':width,'height':height})
        for name in (['control-trade-chart'] if controls else value.get('chart_captures',[])):
            assert '/' not in name and '\\' not in name and '..' not in name
            path=observation.parent/(name+'.png');raw=path.read_bytes()
            assert raw[:8]==b'\x89PNG\r\n\x1a\n'
            width,height=struct.unpack('>II',raw[16:24])
            geometry=value['chart_geometry'] if controls else value['chart_geometry'][name]
            assert geometry['height']==350 and geometry['scale']=='css'
            expected_width=math.ceil(geometry['x']+geometry['width']-1e-3)-math.floor(geometry['x']+1e-3)
            expected_height=math.ceil(geometry['y']+geometry['height']-1e-3)-math.floor(geometry['y']+1e-3)
            assert width==expected_width==geometry['expected_png_width']
            assert height==expected_height==geometry['expected_png_height']
            assert 200<width<=value['viewport']['width']
            shots.append({'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(raw).hexdigest(),'width':width,'height':height,'kind':'actual_chart_element'})
        trace=observation.parent/'trace.zip';assert trace.stat().st_size>0
        rows.append({**value,'trade_net_total':trade_net,'account_net_profit':book['metrics']['net_profit'],
            'reconciliation_absolute_difference':discrepancy,'screenshots':shots,
            'trace':{'path':trace.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(trace.read_bytes()).hexdigest()}})
    output={'scope':f'{len(rows)} financial flows reread from the successful {expected_flows}-journey browser run. Behavior flows have a separate reader. Not full acceptance certification.',
        'flows':rows,'input_manifest':'data/datasets/90f347229b2fb03ec112ee71/manifest.json'}
    destination=folder/'reconciliation.json';destination.write_text(json.dumps(output,indent=2),encoding='utf-8')
    print(json.dumps({'flows':len(rows),'screenshots':sum(len(r['screenshots']) for r in rows),
        'largest_reconciliation_difference':max(r['reconciliation_absolute_difference'] for r in rows)}))
if __name__=='__main__': main()
