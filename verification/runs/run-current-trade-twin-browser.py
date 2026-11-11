"""Owned real-browser flow; actual empty accounts, controlled worker scheduling."""
from pathlib import Path
import hashlib,json,os,shutil,socket,sys,threading,time,uuid

def main():
    sys.stdout.reconfigure(encoding='utf-8',errors='replace');sys.stderr.reconfigure(encoding='utf-8',errors='replace')
    root=Path.cwd();source=root/'data/dev026/next-src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
    sys.path.insert(0,str(root))
    from verification.record_check import source_paths
    from verification.frontend_check import browser_run
    def snapshot():return {p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [*source_paths(source),*(p for p in (source/'frontend/dist').rglob('*') if p.is_file())]}
    before=snapshot();sys.path[:0]=[str(source),str(source/'tests')]
    from conftest import minute_frame
    from backend.lab import service
    from backend.lab.api import create_app
    from backend.lab.models import Experiment
    from backend.lab.service import Lab
    from backend.lab.worker import Worker
    from backend.lab.data import save_dataset
    from backend.lab.runtime import StoreLease
    import uvicorn
    folder=root/'data/dev026/twin-browser'/uuid.uuid4().hex
    # This is exclusively the owned, authored synthetic workload. No user data.
    completed_store=root/'data/dev026/full-owned/20261110T001925270510Z/store'
    shutil.copytree(completed_store/'data',folder/'data')
    lab=Lab(folder)
    completed='1ea147546a634445bb23e1238283cfeb'
    assert lab.store.job(completed)['status']=='completed' and lab.report(completed)['financial_occurrences']==20000
    manifest=save_dataset(lab.datasets_root,minute_frame('2026-11-04'),dict(input_kind='synthetic',provider='Authored empty-account browser fixture',corporate_actions_complete=True))
    service.generate_signals=lambda *a,**k:[]
    parents={}
    for project in ['desktop1920','desktop1280','mobile390']:
        parent=lab.create_experiment(Experiment(name='Empty source '+project,dataset_id=manifest['id'],start='2026-11-04',end='2026-11-04'))
        assert Worker(lab).run_once() and lab.store.job(parent['id'])['status']=='completed'
        assert lab.report(parent['id'])['trades']==[];parents[project]=parent['id']
    shutil.copytree(source/'frontend/dist',folder/'frontend/dist')
    app=create_app(folder,run_worker=False);stop=threading.Event();failures=[]
    def work():
        try:
            with StoreLease(folder):
                while not stop.wait(.1):
                    with lab.store.db() as db:
                        resumed=db.execute("SELECT 1 FROM jobs j WHERE j.status='queued' AND j.kind='trade_twins' AND EXISTS(SELECT 1 FROM events e WHERE e.entity_id=j.id AND e.kind='job_resumed') LIMIT 1").fetchone()
                    if resumed:Worker(lab).run_once()
        except BaseException as error:failures.append(type(error).__name__+': '+str(error))
    worker=threading.Thread(target=work,daemon=False)
    listener=socket.socket();listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='warning',access_log=False))
    http=threading.Thread(target=lambda:server.run(sockets=[listener]),daemon=False)
    exitcode=2;worker.start();http.start()
    try:
        deadline=time.monotonic()+45
        while not server.started:
            if not http.is_alive() or time.monotonic()>deadline:raise RuntimeError('Owned test HTTP server failed to start.')
            time.sleep(.1)
        os.environ['PA_BROWSER_BASE_URL']='http://127.0.0.1:'+str(port);os.environ['PA_TWIN_PARENTS']=json.dumps(parents)
        os.environ['PA_TWIN_COMPLETED']=completed
        exitcode=browser_run(['exec','--','playwright','test','--config=../verification/runs/trade-twin-browser.config.ts'])
    finally:
        stop.set();server.should_exit=True;http.join(25);worker.join(25);listener.close()
        clean=not http.is_alive() and not worker.is_alive();after=snapshot()
        value=dict(scope=__doc__,source_files=before,source_unchanged=before==after,child_exit_code=exitcode,
                   owned_http_and_worker_retired=clean,worker_errors=failures,parents=parents,store=folder.relative_to(root).as_posix(),
                   scheduling='Only children with their original resume event are claimed; API and calculations are real.',
                   actual_new_browser_financial_sets=0,original_completed_synthetic_workload=completed,
                   positive_saved_summary_reopened=True,positive_new_financial_workflow_verified=False,final_product_acceptance=False)
        (out/'trade-twin-browser-subject.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
        assert clean and before==after and not failures,value
    return exitcode

if __name__=='__main__':raise SystemExit(main())
