"""Lint the plan or fail closed on missing/stale release evidence. Executes no receipt commands."""
from pathlib import Path
from datetime import datetime
import argparse
import csv
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
V = ROOT / 'verification'
sys.path.insert(0,str(ROOT))
from verification.record_check import review_artifact_allowed

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

def safe_path(name):
    if not isinstance(name,str) or Path(name).is_absolute() or re.match(r'^[A-Za-z]:',name):
        raise ValueError('Evidence path must be workspace-relative')
    path=(ROOT/name).resolve()
    path.relative_to(ROOT.resolve())
    if any(part=='.env' or part.startswith('.env.') for part in path.parts):
        raise ValueError('Credential files cannot be evidence')
    if not path.is_file():
        raise ValueError('Missing evidence file')
    if not review_artifact_allowed(path,ROOT):
        raise ValueError('Private captures and unreviewed trace archives cannot be release evidence')
    return path

def check_plan():
    c=load(V/'catalog.json')
    reqs={r['id']:r for r in c['requirements']}
    cases={r['id']:r for r in c['cases']}
    errors=[]
    if len(reqs)!=len(c['requirements']) or len(cases)!=len(c['cases']):
        errors.append('Duplicate requirement/case IDs')
    for rid,r in reqs.items():
        if not r['case_ids']: errors.append('Requirement has no acceptance cases: '+rid)
        for cid in r['case_ids']:
            if cid not in cases or cases[cid]['requirement_id']!=rid:
                errors.append('Invalid requirement/case mapping: '+rid)
    for cid,case in cases.items():
        if case['requirement_id'] not in reqs or cid not in reqs[case['requirement_id']]['case_ids']:
            errors.append('Orphan case: '+cid)
        if not case.get('expected') or not case.get('method'):
            errors.append('Missing acceptance definition: '+cid)
    matrix={(x.get('family'),x.get('timeframe'),x.get('direction')) for x in cases.values() if x['id'].startswith('MATRIX-')}
    contract=c['strategy_matrix']
    expected={(f,t,d) for f in contract['families'] for t in contract['timeframes'] for d in contract['directions']}
    if len(expected)!=120 or matrix!=expected: errors.append('Incomplete 120-case strategy matrix')
    with (V/'coverage.csv').open(encoding='utf-8',newline='') as f:
        rows=list(csv.DictReader(f))
    if len(rows)!=len(cases) or {r['case_id'] for r in rows}!=set(cases):
        errors.append('Coverage CSV does not match catalog')
    if any(r['initial_status']!='not_run' or r['receipt'] for r in rows):
        errors.append('Planning CSV must not masquerade as executed results')
    mapping=load(V/'implementation-map.json')
    if len(mapping['requirements'])!=len(reqs) or {r['id'] for r in mapping['requirements']}!=set(reqs):
        errors.append('Implementation-map requirement inventory differs')
    for name in ['PLAN.md','VERIFICATION_PLAN.md','verification/README.md']:
        p=ROOT/name
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if target.startswith(('http://','https://','#')): continue
            if not (p.parent/target.split('#')[0]).exists(): errors.append('Broken documentation link: '+name)
    from jsonschema import Draft202012Validator
    Draft202012Validator.check_schema(load(V/'receipt.schema.json'))
    print(json.dumps({'check':'planning_inventory','requirements':len(reqs),'acceptance_cases':len(cases),
                      'strategy_matrix_cases':len(matrix),'executed_product_tests':0,'errors':errors},indent=2))
    return 1 if errors else 0

def check_release():
    from jsonschema import Draft202012Validator, FormatChecker
    catalog=load(V/'catalog.json')
    cases={c['id']:c for c in catalog['cases']}
    requirements={r['id']:r for r in catalog['requirements']}
    validator=Draft202012Validator(load(V/'receipt.schema.json'),format_checker=FormatChecker())
    errors=[]
    if not cases or not requirements:
        errors.append('Release catalog must contain requirements and acceptance cases')
    if len(cases)!=len(catalog['cases']) or len(requirements)!=len(catalog['requirements']):
        errors.append('Duplicate release requirement/case IDs')
    for rid,requirement in requirements.items():
        if not requirement.get('case_ids') or any(
            cid not in cases or cases[cid]['requirement_id']!=rid for cid in requirement['case_ids']):
            errors.append('Invalid release requirement/case mapping: '+rid)
    for cid,case in cases.items():
        rid=case['requirement_id']
        if rid not in requirements or cid not in requirements[rid].get('case_ids',[]):
            errors.append('Orphan release case: '+cid)
    passed={}
    stale=[]
    current=[]
    receipts=sorted((V/'receipts').glob('*.json')) if (V/'receipts').exists() else []
    subject_file=V/'release-subject.json'
    subject=None
    if not subject_file.exists(): errors.append('Frozen release-subject.json is missing')
    else:
        subject=load(subject_file)
        try:
            for name,sha in subject['source_files'].items():
                if digest(safe_path(name))!=sha: raise ValueError('Changed source')
        except Exception:
            errors.append('Release source manifest is missing, unsafe or stale')
    mapping=load(V/'implementation-map.json')
    mapped=[row['id'] for row in mapping['requirements']]
    if len(mapped)!=len(requirements) or set(mapped)!=set(requirements):
        errors.append('Release implementation-map requirement inventory differs')
    for row in mapping['requirements']:
        if not row.get('implementation') or not row.get('tests') or not row.get('rulebook_sections'):
            errors.append('Missing implementation/test/rulebook mapping: '+row['id'])
        elif subject:
            try:
                for ref in row['implementation']+row['tests']:
                    name=ref['path'] if isinstance(ref,dict) else ref
                    safe_path(name)
                    if name not in subject['source_files']: raise ValueError('Unversioned mapped source')
                if not all(isinstance(s,str) and s.strip() for s in row['rulebook_sections']):
                    raise ValueError('Empty rulebook mapping')
            except Exception:
                errors.append('Invalid/unversioned implementation mapping: '+row['id'])
    seen=set()
    for filename in receipts:
        try:
            receipt=load(filename)
            validator.validate(receipt)
            if receipt['receipt_id'] in seen: raise ValueError('Duplicate receipt ID')
            seen.add(receipt['receipt_id'])
            # Planning and implementation work cannot satisfy product cases.
            if receipt['kind']!='verification': continue
            if datetime.fromisoformat(receipt['finished_at_utc'].replace('Z','+00:00')) < datetime.fromisoformat(receipt['started_at_utc'].replace('Z','+00:00')):
                raise ValueError('Invalid receipt times')
            sub=receipt['subject']
            spec_current=all(sub[field]==digest(ROOT/name) for field,name in [('plan_sha256','PLAN.md'),('verification_plan_sha256','VERIFICATION_PLAN.md'),('catalog_sha256','verification/catalog.json')])
            if not spec_current or not subject or sub!=subject:
                stale.append(receipt['receipt_id'])
                continue
            all_files=list(sub['source_files'].items())+[(x['path'],x['sha256']) for x in [sub['rulebook']]+sub['dependency_locks']+sub['input_manifests']]
            for name,sha in all_files:
                if digest(safe_path(name))!=sha: raise ValueError('Subject file hash mismatch')
            artifacts={a['path']:a for a in receipt['artifacts']}
            if len(artifacts)!=len(receipt['artifacts']): raise ValueError('Duplicated artifact path')
            for name,a in artifacts.items():
                p=safe_path(name)
                if digest(p)!=a['sha256'] or p.stat().st_size!=a['bytes']:
                    raise ValueError('Evidence artifact integrity failure')
            if not any('log' in a['purpose'].lower() for a in artifacts.values()):
                raise ValueError('Missing execution log artifact')
            local=set()
            for result in receipt['results']:
                cid=result['case_id']
                if cid not in cases or cid in local: raise ValueError('Unknown or duplicated case')
                local.add(cid)
                if not set(result['artifact_paths'])<=set(artifacts): raise ValueError('Case evidence is not in artifact manifest')
                if result['status']=='pass':
                    if receipt['command']['exit_code']!=0: raise ValueError('Failing command cannot certify a pass')
            current.append(receipt)
        except Exception as exc:
            # Do not echo receipt content or potentially sensitive error values.
            errors.append('Receipt rejected: '+filename.name+' ('+type(exc).__name__+')')
    # Only fully validated, current receipts may certify or supersede a case.
    for receipt in current:
        for result in receipt['results']:
            cid=result['case_id']
            if result['status']=='pass':
                passed.setdefault(cid,[]).append(receipt['receipt_id'])
            else:
                old_time=datetime.fromisoformat(receipt['finished_at_utc'].replace('Z','+00:00'))
                replaced=any(
                    receipt['receipt_id'] in newer.get('supersedes',[]) and
                    datetime.fromisoformat(newer['started_at_utc'].replace('Z','+00:00'))>=old_time and
                    any(r['case_id']==cid and r['status']=='pass' for r in newer['results'])
                    for newer in current if newer['receipt_id']!=receipt['receipt_id'])
                if not replaced: errors.append('Unresolved current non-pass: '+cid)
    mandatory={c['id'] for c in cases.values() if c['mandatory']}
    missing=sorted(mandatory-set(passed))
    ready=not errors and not missing
    print(json.dumps({'check':'release_evidence','ready':ready,'mandatory_cases':len(mandatory),
                      'verified_cases':len(mandatory&set(passed)),'unverified_cases':len(missing),
                      'stale_receipts':stale,'errors':errors,'missing_case_ids':missing},indent=2))
    return 0 if ready else 1

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=['plan','release'])
    args=parser.parse_args()
    try:
        raise SystemExit(check_plan() if args.mode=='plan' else check_release())
    except ImportError:
        print('BLOCKED: jsonschema is required for evidence validation; no verification claimed.')
        raise SystemExit(2)
