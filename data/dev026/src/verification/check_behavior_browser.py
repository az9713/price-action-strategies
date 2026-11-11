"""Reread actual behavior browser evidence against immutable local reports."""
from pathlib import Path
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

def main():
    folder=(ROOT/sys.argv[1]).resolve();folder.relative_to(ROOT)
    suites=list(ET.parse(folder/'junit.xml').iter('testsuite'))
    suite_size=sum(int(s.attrib['tests']) for s in suites);assert suite_size in {2,10,12}
    assert sum(int(s.attrib.get(k,0)) for s in suites for k in ['failures','errors','skipped'])==0
    build=json.loads((ROOT/'verification/runs/frontend-build.json').read_text(encoding='utf-8'))['files']
    for path,digest in build.items():assert sha(ROOT/path)==digest
    lab=Lab(ROOT);observations=[p for p in (folder/'artifacts').glob('*/observations.json') if (p.parent/'behavior-study.json').exists()];assert len(observations)==2
    outcomes=[]
    for path in observations:
        value=json.loads(path.read_text(encoding='utf-8'));base=path.parent
        root=json.loads((base/'behavior-study.json').read_text(encoding='utf-8'));chart=json.loads((base/'behavior-chart.json').read_text(encoding='utf-8'))
        assert root==lab.report(value['job_id']) and chart==lab.report(value['job_id'],0)
        assert root['core_hash']==value['core_hash']==core_hash() and value['console_errors']==[]
        assert value['tables']==list(root['tables']) and len(value['tables'])==17
        assert 'frontend/dist'+value['bundle'] in build and value['counts']==root['counts']
        records=0
        for name in value['csv_files']:
            key=name.removeprefix('behavior-').removesuffix('.csv');assert key in root['tables']
            with (base/name).open(encoding='utf-8-sig',newline='') as f:actual=list(csv.DictReader(f))
            expected=[{k:'' if v is None else str(v) for k,v in row.items()} for row in root['tables'][key]['rows']]
            assert actual==expected,(name,'CSV values differ from saved rows');records+=len(actual)
        assert len(value['csv_files'])==17
        images=[]
        for name in value['captures']:
            p=base/name;raw=p.read_bytes();assert raw[:8]==b'\x89PNG\r\n\x1a\n';width,height=struct.unpack('>II',raw[16:24])
            if name=='behavior-price-chart.png':
                g=value['chart_geometry'];assert g['height']==350 and g['scale']=='css'
                assert width==g['expected_png_width']==math.ceil(g['x']+g['width']-1e-3)-math.floor(g['x']+1e-3)
                assert height==g['expected_png_height']==math.ceil(g['y']+g['height']-1e-3)-math.floor(g['y']+1e-3)
            else:
                assert 200<width<=value['viewport']['width'] and height>0
                if name=='behavior-validation.png':assert width==value['viewport']['width'] and height>=value['viewport']['height']
            images.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),width=width,height=height))
        trace=base/'trace.zip'
        with zipfile.ZipFile(trace) as z:assert z.testzip() is None and any(n.endswith('.trace') for n in z.namelist())
        outcomes.append(dict(job_id=value['job_id'],viewport=value['viewport'],core_hash=root['core_hash'],tables=17,csv_rows=records,selected_chart_bars=len(chart['bars']['SPY']),touch_records=len(chart['touches']),images=images,trace_sha256=sha(trace)))
    assert {r['viewport']['width'] for r in outcomes}=={1920,1280}
    output=dict(scope='Two actual behavior journeys; persisted JSON/table CSV/geometry/trace/bundle audit. Not final acceptance or numerical feature completeness.',flows=outcomes)
    destination=Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'behavior-browser-reconciliation.json';destination.write_text(json.dumps(output,indent=2),encoding='utf-8')
    print(json.dumps(dict(flows=len(outcomes),images=sum(len(r['images']) for r in outcomes),csv_files=34,csv_rows=sum(r['csv_rows'] for r in outcomes))))

if __name__=='__main__':main()
