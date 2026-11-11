"""Actual owned synthetic-provider calendar acquisition crash, without network."""
from pathlib import Path
import json,os,sys
from backend.lab import news
from backend.lab.service import Lab
from backend.lab.worker import Worker
from test_news_acquisition import document

folder,jid,phase,ready_text,marker_text=sys.argv[1:]
lab=Lab(Path(folder));ready=Path(ready_text);marker=Path(marker_text)
temporary=ready.with_suffix('.tmp');temporary.write_text(json.dumps(dict(pid=os.getpid(),job_id=jid)),encoding='utf-8');temporary.replace(ready)
news.fetch_document=lambda url,cancel=None:document(url)


def die():
    events=[e for e in lab.store.events(jid) if e['kind']=='news_document_saved']
    assert len(events)==1 and lab.news.list()==[] and not lab.output_path(jid).exists()
    marker.write_text(json.dumps(dict(phase=phase,receipt=events[0],checkpoint_present=(lab.output_path(jid).parent/'news-documents.json').exists())),encoding='utf-8')
    os._exit(141 if phase=='before_checkpoint' else 142)


write=news.atomic_json
def checkpoint(path,value):
    if Path(path).name=='news-documents.json' and len(value.get('documents',{}))==1 and phase=='before_checkpoint':die()
    return write(path,value)
news.atomic_json=checkpoint
progress=Worker._progress
def progressed(self,job,fraction,note,checkpoint=None):
    result=progress(self,job,fraction,note,checkpoint)
    if phase=='after_checkpoint' and 0<fraction<1:die()
    return result
Worker._progress=progressed
assert Worker(lab).run_once()
raise AssertionError('The actual news acquisition death boundary was not reached.')
