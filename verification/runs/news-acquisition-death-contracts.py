"""Abrupt acquisition death preserves actual committed documents and original hashes."""
from pathlib import Path
from copy import deepcopy
import hashlib,json,os
import pytest
from backend.lab import news
from backend.lab.research import core_hash
from backend.lab.service import Lab
from backend.lab.worker import Worker
from owned_death_probe import run_probe
from test_news_acquisition import document


@pytest.mark.parametrize('phase,corrupt',[('before_checkpoint',False),('after_checkpoint',False),('after_checkpoint',True)])
def test_actual_calendar_process_death_resume_and_committed_corruption(tmp_path,monkeypatch,phase,corrupt):
    lab=Lab(tmp_path/'owned');request=news.NewsDownload(start='2022-01-01',end='2022-01-31')
    job=lab.store.create_job('news_download',request.model_dump(mode='json')|dict(core_hash=core_hash()))
    original_payload=deepcopy(job['payload']);ready=tmp_path/'news-ready.json';marker=tmp_path/'news-death.json'
    child=Path(__file__).with_name('news-acquisition-death-child.py')
    result=run_probe(child,[str(lab.root),job['id'],phase,str(ready),str(marker)],ready)
    assert result.returncode==(141 if phase=='before_checkpoint' else 142)
    controller=json.loads(ready.with_suffix('.controller.json').read_text())
    assert controller['actual_process_exited'] and not controller['timed_out']
    observed=json.loads(marker.read_text());receipt=observed['receipt'];source=receipt['details']['document']
    assert observed['checkpoint_present'] is (phase=='after_checkpoint')
    raw=lab.news.source_path(source['sha256']).read_bytes()
    assert len(raw)==source['bytes'] and hashlib.sha256(raw).hexdigest()==source['sha256']
    if corrupt:lab.news.source_path(source['sha256']).write_bytes(raw+b'authored corruption after process death')
    with lab.store.db() as db:db.execute('UPDATE jobs SET lease_until=0 WHERE id=?',(job['id'],))
    calls=[]
    monkeypatch.setattr(news,'fetch_document',lambda url,cancel=None:(calls.append(url) or document(url)))
    assert Worker(lab).run_once();state=lab.store.job(job['id'])
    assert state['payload']==original_payload
    receipts=[e for e in lab.store.events(job['id']) if e['kind']=='news_document_saved']
    assert receipts[0]==receipt
    if corrupt:
        assert state['status']=='failed' and calls==[] and lab.news.list()==[] and not lab.output_path(job['id']).exists()
    else:
        assert state['status']=='completed' and len(calls)==1 and calls[0]!=receipt['details']['url']
        assert len(receipts)==2 and lab.news.source_path(source['sha256']).read_bytes()==raw
        saved=lab.result(job['id']);assert saved['calendar']==lab.news.load(saved['news_calendar_id'])
        assert {(e['date'],e['kind']) for e in saved['calendar']['spec']['events']}=={('2022-01-07','jobs'),('2022-01-12','cpi'),('2022-01-26','fed')}
    if os.environ.get('PA_EVIDENCE_RUN_DIR'):
        Path(os.environ['PA_EVIDENCE_RUN_DIR'],f'news-actual-death-{phase}-{corrupt}.json').write_text(json.dumps(dict(
            controller=controller,phase=phase,corrupt=corrupt,original_source_sha256=source['sha256'],
            original_receipt_preserved=True,remaining_fetches=len(calls),terminal_status=state['status'],
            actual_provider_network=False,scope=__doc__),indent=2),encoding='utf-8')
