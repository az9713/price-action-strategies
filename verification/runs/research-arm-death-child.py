"""Controlled actual interpreter exits at arm checkpoint/publication boundaries."""
from pathlib import Path
import hashlib,json,os,sys
from backend.lab import service
from backend.lab import worker as workers
from backend.lab.service import Lab
from backend.lab.worker import Worker

EXITS={'after_first_checkpoint':111,'after_second_checkpoint':112,'after_part_receipt':113,'inside_root_transaction':114,'after_root_commit':115}


def main():
    root,jid,boundary,marker=sys.argv[1:];lab=Lab(Path(root))
    ready = Path(marker).with_name('actual-death-ready.json')
    temporary = ready.with_suffix('.tmp')
    temporary.write_text(json.dumps(dict(pid=os.getpid(),job_id=jid)),encoding='utf-8')
    temporary.replace(ready)
    service.generate_signals=lambda *a,**k:[]
    def die():
        folder=lab.output_path(jid).parent
        files={p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file()}
        Path(marker).write_text(json.dumps(dict(job_id=jid,boundary=boundary,exit_code=EXITS[boundary],files=files,detector_validation=False)),encoding='utf-8')
        os._exit(EXITS[boundary])
    if boundary in {'after_first_checkpoint','after_second_checkpoint'}:
        old=Worker._progress;target=1 if boundary=='after_first_checkpoint' else 2
        def progress(self,job,fraction,note,checkpoint=None):
            result=old(self,job,fraction,note,checkpoint)
            if job['id']==jid and checkpoint==target:die()
            return result
        Worker._progress=progress
    elif boundary=='after_part_receipt':
        old=workers.atomic_json
        def receipt(path,value):
            result=old(path,value)
            if path.parent==lab.output_path(jid).parent/'parts' and path.name=='000000.json.sha256.json':die()
            return result
        workers.atomic_json=receipt
    elif boundary=='inside_root_transaction':
        old=lab.store.event
        def event(kind,entity,details,db=None):
            result=old(kind,entity,details,db)
            if kind=='result_saved' and entity==jid and db is not None and db.in_transaction:die()
            return result
        lab.store.event=event
    else:
        old=lab.result_index.build
        def build(job_id,*args,**kwargs):
            if job_id==jid:die()
            return old(job_id,*args,**kwargs)
        lab.result_index.build=build
    Worker(lab).run_once()
    raise AssertionError('The real arm death boundary was not reached.')


if __name__=='__main__':main()
