"""Owned browser server over a copy of the actual completed synthetic workload."""
from pathlib import Path
from contextlib import closing
import csv,gzip,hashlib,io,json,os,shutil,socket,sqlite3,sys,threading,time,uuid,zipfile

def main():
    sys.stdout.reconfigure(encoding='utf-8',errors='replace');sys.stderr.reconfigure(encoding='utf-8',errors='replace')
    root=Path.cwd();source=root/'data/dev026/evidence-src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
    sys.path.insert(0,str(root));from verification.record_check import source_paths
    from verification.frontend_check import browser_run
    def snapshot():return {p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [*source_paths(source),*(p for p in (source/'frontend/dist').rglob('*') if p.is_file())]}
    before=snapshot();sys.path.insert(0,str(source))
    from backend.lab.service import Lab
    from backend.lab.api import create_app
    from backend.lab.trade_twin_views import repair_view
    import uvicorn
    original=root/'data/dev026/full-owned/20261110T010321700433Z/store'
    folder=root/'data/dev026/inspector-browser'/uuid.uuid4().hex
    for path in (original/'data/datasets').glob('*/manifest.json'):assert json.loads(path.read_text())['metadata']['input_kind']=='synthetic'
    shutil.copytree(original/'data',folder/'data',ignore=shutil.ignore_patterns('lab.sqlite3','lab.sqlite3-wal','lab.sqlite3-shm'))
    with closing(sqlite3.connect((original/'data/lab.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)) as old,closing(sqlite3.connect(folder/'data/lab.sqlite3')) as new:old.backup(new)
    lab=Lab(folder);jid='3b9f36b31fee4bae838f5a2f6e638049';assert lab.store.job(jid)['status']=='completed'
    repaired=repair_view(lab,jid);assert repaired['financial_recomputations']==0
    shutil.copytree(source/'frontend/dist',folder/'frontend/dist')
    exports=root/'data/private-evidence/twin-browser-exports'/out.name;exports.mkdir(parents=True,exist_ok=False)
    app=create_app(folder,run_worker=False);listener=socket.socket();listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='warning',access_log=False))
    thread=threading.Thread(target=lambda:server.run(sockets=[listener]),daemon=False);exitcode=2;thread.start()
    try:
        deadline=time.monotonic()+45
        while not server.started:
            if not thread.is_alive() or time.monotonic()>deadline:raise RuntimeError('Owned inspector server failed to start.')
            time.sleep(.1)
        os.environ.update(PA_BROWSER_BASE_URL='http://127.0.0.1:'+str(port),PA_TWIN_INSPECTOR_JOB=jid,PA_TWIN_PRIVATE_EXPORTS=str(exports))
        exitcode=browser_run(['exec','--','playwright','test','--config=../verification/runs/twin-inspector-browser.config.ts'])
    finally:
        server.should_exit=True;thread.join(25);listener.close();after=snapshot()
        archive_checks=[]
        expected_parts={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (lab.output_path(jid).parent/'twins/parts').glob('*.json.gz')}
        for path in sorted(exports.glob('*.zip')):
            with zipfile.ZipFile(path) as archive:
                assert archive.testzip() is None
                complete=json.loads(archive.read('COMPLETE.json'))
                assert complete['financial_occurrences']==20000 and complete['original_trials']==20001 and complete['unique_books']==28
                assert complete['tabular_rows']['sets']==complete['tabular_rows']['members']==20000
                for name,digest in expected_parts.items():assert hashlib.sha256(archive.read('original-parts/'+name)).hexdigest()==digest
                assert len(list(csv.DictReader(io.StringIO(archive.read('sets.csv').decode()))))==20000
                archive_checks.append(dict(filename=path.name,complete=complete,original_part_hashes_verified=len(expected_parts),zip_crc_verified=True))
        if exitcode==0:assert len(archive_checks)==3
        value=dict(scope=__doc__,source_files=before,source_unchanged=before==after,child_exit_code=exitcode,
                   owned_http_retired=not thread.is_alive(),worker_process_started=False,original_completed_job=jid,
                   actual_new_financial_sets=0,private_exports=[dict(filename=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(exports.glob('*.zip'))],
                   independent_browser_download_checks=archive_checks,
                   store=folder.relative_to(root).as_posix(),final_product_acceptance=False)
        (out/'inspector-browser-subject.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
        assert before==after and not thread.is_alive()
    return exitcode

if __name__=='__main__':raise SystemExit(main())
