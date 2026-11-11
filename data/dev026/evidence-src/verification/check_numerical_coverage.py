"""Fail closed on the plan's numerical coverage thresholds, independent of test count.

This checks an actual recorded coverage artifact and current numerical source.
It does not promote implementation receipts to product acceptance certificates.
"""
from pathlib import Path
import hashlib
import json
import os
import sys
import argparse

ROOT=Path(__file__).resolve().parents[1]
MODULES=['backend/lab/'+name+'.py' for name in ['config','data','signals','engine','metrics','service','benchmarks','controls','behavior','ablations','trials','news','borrow','sensitivity','research','search_statistics','sampling','dataset_context','job_index','study_index','result_index','evaluation_cache','spread','spread_preparation','spread_jobs','spread_worker','spread_accounts','trade_twins','trade_twin_source','trade_twin_execution','trade_twin_features','trade_twin_amounts','trade_twin_results','trade_twin_jobs','trade_twin_preparation','trade_twin_parts','trade_twin_worker','source_cashflows','trade_twin_evidence','trade_twin_views']]


def safe(root,name):
    relative=Path(name)
    if relative.is_absolute() or ':' in str(name) or any(p.startswith('.env') for p in relative.parts):
        raise ValueError('Unsafe evidence path.')
    path=(root/relative).resolve();path.relative_to(root.resolve())
    return path


def evaluate(receipt,root=ROOT):
    if receipt['command']['exit_code']!=0 or any(note.startswith(('Source changed','Missing requested')) for note in receipt.get('notes',[])):
        raise ValueError('The executed check is failing or incoherent.')
    artifacts=[a for a in receipt['artifacts'] if a['path'].endswith('coverage.json')]
    if len(artifacts)!=1: raise ValueError('Exactly one recorded coverage artifact is required.')
    artifact=artifacts[0];raw=safe(root,artifact['path']).read_bytes()
    if len(raw)!=artifact['bytes'] or hashlib.sha256(raw).hexdigest()!=artifact['sha256']:
        raise ValueError('Coverage artifact integrity failure.')
    coverage=json.loads(raw);files={name.replace('\\','/'):value for name,value in coverage['files'].items()}
    rows=[]
    for name in MODULES:
        current=hashlib.sha256(safe(root,name).read_bytes()).hexdigest()
        source_current=receipt['subject']['source_files'].get(name)==current
        summary=files.get(name,{}).get('summary',{})
        statements=summary.get('num_statements',0);branches=summary.get('num_branches',0)
        covered=summary.get('covered_lines',-1);covered_branches=summary.get('covered_branches',-1)
        if not 0<=covered<=statements or not 0<=covered_branches<=branches:
            raise ValueError('Invalid coverage counts.')
        lines=100*covered/statements if statements else 0
        branch_percent=100*covered_branches/branches if branches else 0
        rows.append(dict(path=name,source_current=source_current,line_percent=lines,branch_percent=branch_percent,
            required_line_percent=95,required_branch_percent=90,
            gate_pass=source_current and statements>0 and branches>0 and lines>=95 and branch_percent>=90))
    return dict(scope='Numerical source/coverage gate only; not complete acceptance certification.',
        coverage_artifact=artifact['path'],modules=rows,ready=all(r['gate_pass'] for r in rows))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('receipt',help='Workspace-relative receipt with one actual coverage.json artifact.')
    args=parser.parse_args()
    receipt_path=safe(ROOT,args.receipt);receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
    result=evaluate(receipt)
    folder=Path(os.environ.get('PA_EVIDENCE_RUN_DIR',ROOT/'verification/runs/numerical-coverage-manual'))
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'numerical-coverage-gate.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    return 0 if result['ready'] else 1


if __name__=='__main__': raise SystemExit(main())
