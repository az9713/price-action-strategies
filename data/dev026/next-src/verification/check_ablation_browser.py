"""Reread saved browser downloads, actual reports, geometry and trace integrity."""
from pathlib import Path
from decimal import Decimal
import csv
import hashlib
import json
import math
import os
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.lab.service import Lab
from backend.lab.research import core_hash

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def csv_rows(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def main():
    folder=(ROOT/sys.argv[1]).resolve();folder.relative_to(ROOT)
    suites=list(ET.parse(folder/'junit.xml').iter('testsuite'));assert sum(int(s.attrib['tests']) for s in suites) in {2,12}
    assert not sum(int(s.attrib.get(k,0)) for s in suites for k in ['failures','errors','skipped'])
    build=json.loads((ROOT/'verification/runs/frontend-build.json').read_text(encoding='utf-8'))['files']
    for name,value in build.items():assert sha(ROOT/name)==value
    lab=Lab(ROOT);out=[]
    paths=[p for p in (folder/'artifacts').glob('*/observations.json') if (p.parent/'ablation-study.json').exists()];assert len(paths)==2
    for path in paths:
        value=json.loads(path.read_text(encoding='utf-8'));base=path.parent;root=lab.report(value['job_id'])
        assert root==json.loads((base/'ablation-study.json').read_text(encoding='utf-8'))
        assert root['core_hash']==value['core_hash']==core_hash() and value['console_errors']==[]
        assert 'frontend/dist'+value['bundle'] in build and len(root['arms'])==3
        comparisons=csv_rows(base/'ablation-comparisons.csv');assert len(comparisons)==2
        for actual,expected in zip(comparisons,root['comparison_rows']):
            assert actual=={k:'' if v is None else str(v) for k,v in expected.items()}
        book=lab.report(value['job_id'],value['selected_part'])
        assert book==json.loads((base/'ablation-account.json').read_text(encoding='utf-8'))
        trades=csv_rows(base/'ablation-account-trades.csv');assert len(trades)==len(book['trades'])>0
        for actual,expected in zip(trades,book['trades']):
            for k in ['id','symbol','entry_at','exit_at','strategy_id']:assert actual[k]==expected[k]
            for k in ['entry_price','exit_price','entry_quantity','exit_quantity','net_pnl','fees','borrow','distributions']:
                assert abs(Decimal(actual[k])-Decimal(str(expected[k])))<=Decimal('1e-9' if 'price' in k or 'quantity' in k else '1e-7')
        numeric=lab.report(value['numeric_job_id']);assert numeric==json.loads((base/'numeric-ablation-study.json').read_text(encoding='utf-8')) and len(numeric['arms'])==13
        ledger=json.loads((base/'trial-ledger.json').read_text(encoding='utf-8'));rows=ledger['rows'];assert ledger['occurrences']==len(rows)==13 and ledger['job_id']==value['numeric_job_id']
        current=lab.store.registry(limit=200,job_id=value['numeric_job_id'])['rows']
        for row in rows:
            saved=next(r for r in current if r['id']==row['id'])
            assert row=={k:saved[k] for k in row}
            assert row['state']=='completed' and row['provenance']=='prespecified' and row['attempts']==1 and row['artifact_sha256']
            arm=next(a for a in numeric['arms'] if a['part']==row['part']);assert arm['config_id']==row['config_id']
        exported=csv_rows(base/'trial-ledger.csv');assert len(exported)==13
        for actual,expected in zip(exported,rows):
            for key,val in expected.items():
                if key=='attempt_history':assert json.loads(actual[key])==val
                else:
                    text='' if val is None else str(val)
                    if text.lstrip().startswith(('=','+','-','@','\t','\r')):text="'"+text
                    assert actual[key]==text,(key,actual[key],text)
        images=[]
        for name in value['captures']:
            p=base/name;raw=p.read_bytes();assert raw[:8]==b'\x89PNG\r\n\x1a\n';width,height=struct.unpack('>II',raw[16:24])
            if name=='ablation-trade-chart.png':
                g=value['chart_geometry'];assert g['height']==350 and g['scale']=='css'
                assert width==g['expected_png_width']==math.ceil(g['x']+g['width']-1e-3)-math.floor(g['x']+1e-3)
                assert height==g['expected_png_height']==math.ceil(g['y']+g['height']-1e-3)-math.floor(g['y']+1e-3)
            else:assert 200<width<=value['viewport']['width'] and height>0
            images.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),width=width,height=height))
        with zipfile.ZipFile(base/'trace.zip') as z:assert z.testzip() is None and any(n.endswith('.trace') for n in z.namelist())
        out.append(dict(job_id=value['job_id'],numeric_job_id=value['numeric_job_id'],viewport=value['viewport'],images=images,trace_sha256=sha(base/'trace.zip'),downloaded_trial_rows=len(rows),downloaded_trade_rows=len(trades)))
    assert {v['viewport']['width'] for v in out}=={1920,1280}
    result=dict(status='pass',scope='Two actual historical paired-comparison and ledger browser journeys. Persisted JSON/CSV, full beyond-page history, geometry, trace and bundle checks; not full acceptance.',flows=out)
    (Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'ablation-browser-reconciliation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(dict(flows=len(out),images=sum(len(r['images']) for r in out),full_ledger_rows=sum(r['downloaded_trial_rows'] for r in out))))

if __name__=='__main__':main()
