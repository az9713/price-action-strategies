"""Reopen the completed actual 10000-set owned workload; do not repeat finance.

The original command remains failed: its last assertion expected checkpointed
trials after successful worker completion had promoted them to completed.
Worker peak memory was not saved before that assertion and is unavailable.
"""
from pathlib import Path
from decimal import Decimal
from fractions import Fraction
import hashlib,json,os,sys
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
owned=root/'data/dev026/full-owned/20261110T001925270510Z';source=owned/'src'
sys.path.insert(0,str(root));from verification.record_check import source_paths
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
original_id='20261110T001925270510Z-current-owned-worker-10000-paired-financial-sets-original-checkpoints-independent-books-and-resources'
failed=json.loads((root/'verification/receipts'/(original_id+'.json')).read_text())
assert failed['command']['exit_code']==1
assert not any(n.startswith(('Source changed','Missing requested')) for n in failed['notes'])
checkpoint_id='20261110T001935855967Z-source-cashflows-canonical-tampering-independent-components-and-production-baseline-current'
checkpoint=json.loads((root/'verification/receipts'/(checkpoint_id+'.json')).read_text())
entry=next(a for a in checkpoint['artifacts'] if a['path'].endswith('/next-stage-source-subject.json'))
assert sha(root/entry['path'])==entry['sha256']
subject={p.relative_to(source).as_posix():sha(p) for p in source_paths(source)}
assert subject==json.loads((root/entry['path']).read_text())['source_files']
sys.path[:0]=[str(source),str(source/'tests')]
for name in list(sys.modules):
    if name=='verification' or name.startswith('verification.'):del sys.modules[name]
from backend.lab.service import Lab,compressed_read
from backend.lab.data import load_window,prepare
from verification.trade_twin_reference import execute_reference
lab=Lab(owned/'store');child='1ea147546a634445bb23e1238283cfeb';parent='8cadfb41c02a45ad9037f0f636bc14d9'
job=lab.store.job(child);assert job['status']=='completed'
saved=compressed_read(lab.output_path(child));report=saved['report'];payload=job['payload']
assert report['financial_occurrences']==20000 and report['comparison_eligible']
assert sha(lab.output_path(parent))==payload['twin_parent']['authority']['root_sha256']
folder=lab.output_path(child).parent/'twins';prep=compressed_read(next((folder/'preparation').glob('*.json.gz')));plan=prep['plan']
assert plan['plan_hash']==report['plan_hash'] and digest(lab.report(parent))==report['source']['report_hash']
manifest=compressed_read(folder/'results'/saved['financial_manifest']['filename'])
assert sha(folder/'results'/saved['financial_manifest']['filename'])==saved['financial_manifest']['sha256']
assert digest(manifest)==report['manifest_hash']
bank={};parts=[];seen={p:set() for p in report['summaries']}
with lab.store.db() as db:
    for header in manifest['parts']:
        path=folder/'parts'/header['filename'];assert sha(path)==header['sha256']
        original=db.execute("SELECT details FROM events WHERE entity_id=? AND kind='twin_part_committed' AND json_extract(details,'$.part')=?",(child,header['part'])).fetchall()
        assert len(original)==1 and json.loads(original[0][0])==header
        value=compressed_read(path);parts.append(value)
        for book in value['books']:
            assert book['key'] not in bank and digest(book['book'])==book['sha256'] and digest(book['inputs'])==book['key']
            bank[book['key']]=book
    for part in parts:
        for row in part['sets']:
            outcome=row['outcome'];ordinal=outcome['set_index'];policy=outcome['policy']
            assert ordinal not in seen[policy];seen[policy].add(ordinal)
            assert outcome['state']=='completed' and outcome['trade_count']==len(plan['sources'])==1
            trial=db.execute('SELECT * FROM trial_plans WHERE job_id=? AND part=? AND window=?',(child,ordinal,policy)).fetchone()
            assert trial['state']=='completed' and trial['computed_sha256']==digest(row)
            assert trial['artifact_sha256']==manifest['parts'][part['part']]['sha256']
            attempt=db.execute('SELECT * FROM trial_attempts WHERE trial_id=? AND ordinal=?',(trial['id'],trial['attempts'])).fetchone()
            assert attempt['state']=='checkpointed' and attempt['computed_sha256']==digest(row) and attempt['artifact_sha256']==trial['artifact_sha256']
            assert digest({k:v for k,v in row['draw'].items() if k!='draw_hash'})==row['draw']['draw_hash']
            total=Fraction(0)
            for original_trade,pool,match,member in zip(plan['sources'],plan['pools'],row['draw']['matches'],row['members']):
                coordinate=dict(policy=plan['draw_policy'],plan_hash=plan['plan_hash'],seed=payload['seed'],set_index=ordinal,source_id=original_trade['trade_id'])
                domain=1<<256;ceiling=domain-domain%len(pool);counter=0
                while True:
                    number=int(digest(coordinate|dict(counter=counter)),16)
                    if number<ceiling:break
                    counter+=1
                moment=plan['moments'][pool[number%len(pool)]]
                assert match['entry_at']==moment['entry_at'] and match['source_id']==original_trade['trade_id']==member['source_id']
                # Independently check every transported price and exact elapsed cutoff.
                import pandas as pd
                for field,source_field in [('stop','entry_stop'),('target','entry_target')]:
                    distance=(Fraction(str(original_trade[source_field]))-Fraction(str(original_trade['entry_price'])))/Fraction(str(original_trade['entry_atr']))
                    assert Fraction(match[field])==Fraction(str(moment['reference_price']))+distance*Fraction(str(moment['atr']))
                duration=pd.Timestamp(original_trade['exit_at'])-pd.Timestamp(original_trade['entry_at'])
                assert pd.Timestamp(match['cutoff_at'])==pd.Timestamp(match['entry_at'])+duration
                book=bank[member['book_key']];assert member['book_sha256']==book['sha256']
                assert book['inputs']['match']==match and book['inputs']['policy']==policy
                total+=Fraction(book['book']['net_profit'])
            assert Fraction(outcome['net_profit'])==total==0
    assert all(values==set(range(10000)) for values in seen.values())
    states=dict(db.execute('SELECT state,COUNT(*) FROM trial_plans WHERE job_id=? GROUP BY state',(child,)))
    assert states=={'completed':20001}
    assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='trial_checkpoint_saved'",(child,)).fetchone()[0]==20001
    assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='result_saved'",(child,)).fetchone()[0]==1
    assert db.execute('SELECT COUNT(*) FROM trade_twin_book_index WHERE job_id=?',(child,)).fetchone()[0]==len(bank)
for value in report['summaries'].values():
    assert value['state']=='completed' and value['complete_sets']==value['exceedances']==10000
    assert value['failed_sets']==0 and value['raw_exceedance_fraction']==1 and value['adapted_pass'] is False
data,unused=load_window(lab.datasets_root,payload['dataset_id'],payload['start'],payload['end']);regular=prepare(data)
primitive=[{k:v.isoformat() if hasattr(v,'isoformat') else v for k,v in row.items()} for row in regular.to_dict('records')]
def parity(actual,reference):
    if isinstance(reference,dict):
        assert set(actual)==set(reference)
        for k,v in reference.items():parity(actual[k],v)
    elif isinstance(reference,list):
        assert len(actual)==len(reference)
        for a,b in zip(actual,reference):parity(a,b)
    elif isinstance(reference,Decimal):assert abs(Decimal(str(actual))-reference)<=Decimal('1e-7')
    else:assert type(actual) is type(reference) and actual==reference
for book in bank.values():
    i=book['inputs'];parity(book['book'],execute_reference(primitive,i['match'],i['strategy'],i['costs'],i['portfolio'],[],i['policy']))
assert subject=={p.relative_to(source).as_posix():sha(p) for p in source_paths(source)}
files=[p for p in lab.output_path(child).parent.rglob('*') if p.is_file()]
value=dict(scope=__doc__,source_files=subject,source_snapshot=source.relative_to(root).as_posix(),original_failed_receipt=original_id,
           independently_matched_source_checkpoint=checkpoint_id,source_unchanged=True,child=child,parent=parent,
           configured_sets_per_policy=10000,verified_occurrences=20000,original_checkpoints=20001,completed_trial_occurrences=20001,
           committed_parts=len(parts),independently_replayed_complete_books=len(bank),
           actual_job_wall_seconds=job['updated']-job['created'],worker_peak_memory_bytes=None,
           worker_peak_memory_limitation='Not retained before the original final assertion failure. Do not substitute audit-process memory.',
           output_bytes=sum(p.stat().st_size for p in files),output_files=len(files),summaries=report['summaries'],
           later_api_ui_source_changes_included=False,full_history_capacity_verified=False,final_product_acceptance=False)
(out/'completed-owned-financial-audit.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in value.items() if k not in {'scope','source_files'}},indent=2))
