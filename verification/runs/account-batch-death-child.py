"""Abruptly exit this owned synthetic worker at an actual batch boundary."""
from pathlib import Path
from threading import Timer
import hashlib,importlib.util,json,os,sys

watch=Timer(75,lambda:os._exit(199));watch.daemon=True;watch.start()
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'data/dev027/research-src/tests'))
from backend.lab import service,worker as worker_module,account_checkpoints as checkpoints
from backend.lab.service import Lab
from backend.lab.worker import Worker

spec=importlib.util.spec_from_file_location('actual_batch_financial_fixture',Path(__file__).with_name('account-batch-financial-contracts.py'))
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
folder=Path(sys.argv[1]);jid=sys.argv[2];phase=sys.argv[3];marker=Path(sys.argv[4]);lab=Lab(folder)
EXITS={'private_candidates':130,'first_promotion':131,'last_receipt':132,'closing_source':133,'committed_unit':134}
assert phase in EXITS
service.generate_signals=fixture.authored
def die():
    with lab.store.db() as db:
        originals=[dict(r) for r in db.execute('SELECT part,attempts,artifact_sha256,computed_sha256 FROM trial_plans WHERE job_id=? AND artifact_sha256 IS NOT NULL ORDER BY part',(jid,))]
        started=db.execute('SELECT SUM(attempts) FROM trial_plans WHERE job_id=?',(jid,)).fetchone()[0]
    files={}
    for row in originals:
        path=lab.output_path(jid).parent/'parts'/f"{row['part']:06d}.json.gz"
        files[str(row['part'])]=hashlib.sha256(path.read_bytes()).hexdigest()
        assert files[str(row['part'])]==row['artifact_sha256']
    marker.write_text(json.dumps(dict(phase=phase,originals=originals,files=files,actual_started_attempts=started,
        report_files_visible=len(list((lab.output_path(jid).parent/'parts').glob('[0-9]*.json.gz')))),indent=2),encoding='utf-8')
    os._exit(EXITS[phase])
written=[];real_write=worker_module.compressed_write
def write(path,value):
    real_write(path,value)
    if path.name.startswith('unpublished-part-'):
        written.append(path)
        if phase=='private_candidates' and len(written)==4:die()
worker_module.compressed_write=write
real_replace=os.replace
def replace(source,destination,*a,**k):
    result=real_replace(source,destination,*a,**k)
    if phase=='first_promotion' and Path(source).name.startswith('unpublished-part-') and Path(destination).name=='000000.json.gz':die()
    return result
os.replace=replace
real_receipt=worker_module.atomic_json
def receipt(path,value):
    real_receipt(path,value)
    if phase=='last_receipt' and path.name=='000007.json.sha256.json':die()
worker_module.atomic_json=receipt
checks=[];real_source=checkpoints.require_current_source
def source():
    if sys._getframe(1).f_code.co_name=='publish_checkpoints':
        checks.append(1)
        if phase=='closing_source' and len(checks)==3:die()
    return real_source()
checkpoints.require_current_source=source
progress=Worker._progress
def progressed(self,job,fraction,note,checkpoint=None):
    result=progress(self,job,fraction,note,checkpoint)
    if phase=='committed_unit' and checkpoint==8:die()
    return result
Worker._progress=progressed
assert Worker(lab).run_once()
raise AssertionError('The requested actual batch-death boundary was never reached.')
