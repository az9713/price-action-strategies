"""One owned synthetic store and lifecycle; no credentials or live-store access."""
from pathlib import Path
import hashlib,json,os,shutil,socket,sys,threading,time,uuid

def main():
    sys.stdout.reconfigure(encoding='utf-8',errors='replace');sys.stderr.reconfigure(encoding='utf-8',errors='replace')
    root=Path.cwd();source=root;run=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
    sys.path.insert(0,str(root))
    from verification.record_check import source_paths
    from verification.frontend_check import browser_run
    def snapshot():
        paths=list(source_paths(source))+[p for p in (source/'frontend/dist').rglob('*') if p.is_file()]
        return {p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    before=snapshot()
    sys.path.insert(0,str(source));sys.path.insert(0,str(source/'tests'))
    import backend.lab.api as api_module
    assert Path(api_module.__file__).resolve()==(source/'backend/lab/api.py').resolve()
    from test_spread_probe import owned
    import uvicorn
    store=root/'data/dev025/browser-stores'/uuid.uuid4().hex;store.mkdir(parents=True)
    lab,manifest,context,cfg=owned.__wrapped__(store)
    shutil.copytree(source/'frontend/dist',store/'frontend/dist')
    app=api_module.create_app(store)
    listener=socket.socket();listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='warning',access_log=False))
    thread=threading.Thread(target=lambda:server.run(sockets=[listener]),daemon=False)
    thread.start();exitcode=2;clean=False
    try:
        deadline=time.monotonic()+45
        while not server.started:
            if not thread.is_alive() or time.monotonic()>deadline:raise RuntimeError('Owned browser server failed to start')
            time.sleep(.1)
        os.environ['PA_BROWSER_BASE_URL']='http://127.0.0.1:'+str(port)
        os.environ['PA_SPREAD_DATASET']=manifest['id']
        assert lab.store.path.resolve().is_relative_to((root/'data/dev025/browser-stores').resolve())
        os.environ['PA_OWNED_BROWSER_DB']=str(lab.store.path.resolve())
        selected=sys.argv[1:] or ['common-sampling.spec.ts','dataset-context-universe.spec.ts','portfolio-study.spec.ts','study-status.spec.ts','dataset-context-owned.spec.ts']
        exitcode=browser_run(['exec','--','playwright','test','--config=../verification/runs/legacy025-browser.config.ts',*selected])
        from spread_browser_originals import retain
        retain(lab,manifest,run,root)
    finally:
        server.should_exit=True;thread.join(25);listener.close()
        worker=getattr(app.state,'worker_process',None)
        clean=not thread.is_alive() and (worker is None or not worker.is_alive())
        after=snapshot()
        changed=sorted(k for k in set(before)|set(after) if before.get(k)!=after.get(k))
        (run/'spread-browser-subject.json').write_text(json.dumps(dict(source_files=before,changed_during_check=changed,
            child_exit_code=exitcode,owned_http_and_worker_retired=clean,api_source=str(Path(api_module.__file__).relative_to(root)),
            dataset=manifest,scope='Owned synthetic store and development build only; no live credentials or data',
            store_relative=store.relative_to(root).as_posix()),indent=2),encoding='utf-8')
        if changed or not clean:raise RuntimeError('Source drift or unretired owned browser server')
    return exitcode

if __name__=='__main__':
    from verification_awake import awake
    with awake():raise SystemExit(main())
