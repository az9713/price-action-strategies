"""Kill only this authored child interpreter at a real family-job boundary."""
from pathlib import Path
import hashlib,json,os,sys
from pytest import MonkeyPatch
from backend.lab.service import Lab
from backend.lab.worker import Worker

BOUNDARIES={'after_computation':91,'after_root_file':92,'inside_publication':93,'after_publication':94,'after_view':95}


def install(patch,lab,jid,boundary,callback):
    from backend.lab import service
    fired=[]
    def once():
        if not fired:fired.append(True);callback()
    if boundary=='after_computation':
        old=lab.store.computed_trial
        def computed(job_id,*args,**kwargs):
            result=old(job_id,*args,**kwargs)
            if job_id==jid:once()
            return result
        patch.setattr(lab.store,'computed_trial',computed)
    elif boundary=='after_root_file':
        old=service.compressed_write
        def write(path,*args,**kwargs):
            result=old(path,*args,**kwargs)
            if path==lab.output_path(jid):once()
            return result
        patch.setattr(service,'compressed_write',write)
    elif boundary=='inside_publication':
        old=lab.store.event
        def event(kind,entity,*args,**kwargs):
            result=old(kind,entity,*args,**kwargs)
            if entity==jid and kind=='result_saved':once()
            return result
        patch.setattr(lab.store,'event',event)
    elif boundary in {'after_publication','after_view'}:
        old=lab.result_index.build
        def build(job_id,*args,**kwargs):
            if job_id==jid and boundary=='after_publication':once()
            result=old(job_id,*args,**kwargs)
            if job_id==jid and boundary=='after_view':once()
            return result
        patch.setattr(lab.result_index,'build',build)
    else:raise AssertionError('Unknown authored family boundary')
    return fired


if __name__=='__main__':
    root,jid,boundary,marker=sys.argv[1:];lab=Lab(Path(root))
    def die():
        path=lab.output_path(jid)
        Path(marker).write_text(json.dumps(dict(job_id=jid,boundary=boundary,exit_code=BOUNDARIES[boundary],root_sha256=hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None)),encoding='utf-8')
        os._exit(BOUNDARIES[boundary])
    install(MonkeyPatch(),lab,jid,boundary,die)
    Worker(lab).run_once()
    raise AssertionError('The actual authored death boundary was not reached.')
