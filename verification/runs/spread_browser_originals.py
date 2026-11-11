"""Retain original synthetic authority after UI execution, never live-store data."""
from pathlib import Path
import hashlib,json,shutil

def retain(lab,manifest,run,workspace):
    assert lab.root.resolve().is_relative_to((workspace/'data/dev025/browser-stores').resolve())
    assert manifest.get('metadata',{}).get('input_kind')=='synthetic'
    from backend.lab.config import canonical
    from test_reference_execution import primitive
    with lab.store.db() as db:
        children=list(db.execute("SELECT id FROM jobs WHERE kind='spread_accounts' AND status='completed' ORDER BY created LIMIT 11"))
    assert len(children)<=10,'Unexpected account inventory; no partial archive is certified'
    output=run/'original-browser-accounts';output.mkdir();observations=[]
    def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    for child_row in children:
        child=lab.store.job(child_row['id']);parent=lab.store.job(child['payload']['spread_parent']['job_id'])
        assert parent['payload']['dataset_id']==child['payload']['dataset_id']==manifest['id']
        assert len(child['payload']['configurations'])==1
        base=output/child['id'];base.mkdir();copied=[]
        for role,job in [('parent',parent),('child',child)]:
            folder=base/role;folder.mkdir()
            for name,value in [('inputs',lab.store.job_inputs(job['id'])),('events',lab.store.events(job['id'])),('registry',lab.store.registry(job_id=job['id']))]:
                (folder/(name+'.json')).write_text(canonical(value),encoding='utf-8')
            original=lab.output_path(job['id']).parent
            allowed={'result.json.gz','spread-proposals','spread-preparation','spread-signals'} if role=='parent' else {'result.json.gz','parts'}
            for path in original.rglob('*'):
                if not path.is_file():continue
                relative=path.relative_to(original)
                if relative.parts[0] not in allowed:continue
                assert not path.is_symlink() and not any(p.lower().startswith('.env') for p in relative.parts)
                target=folder/'artifacts'/relative;target.parent.mkdir(parents=True,exist_ok=True);digest=sha(path);shutil.copyfile(path,target)
                assert sha(target)==sha(path)==digest
                copied.append(dict(path=target.relative_to(run).as_posix(),sha256=digest,bytes=target.stat().st_size))
        original=parent['payload'];_,regular,_,_=lab._evaluation_input(original['dataset_id'],original['start'],original['end'],expected_manifest=original['dataset_manifest_hash'],symbols=[original['primary_symbol']])
        (base/'synthetic-primary-bars.json').write_text(canonical(primitive(regular)),encoding='utf-8')
        observations.append(dict(child_id=child['id'],parent_id=parent['id'],files=copied))
    value=dict(scope=__doc__,accounts=observations,actual_ui_accounts=len(observations),price_kind='synthetic',financial_work_executed_by_capture=False,live_store_accessed=False)
    (output/'manifest.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
    return value
