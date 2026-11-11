"""Owned headless workflow over authored empty-signal accounts; no user store or screen."""
from pathlib import Path
import hashlib,json,os,shutil,socket,sys,threading,time,uuid


def main():
    sys.stdout.reconfigure(encoding='utf-8',errors='replace');sys.stderr.reconfigure(encoding='utf-8',errors='replace')
    root=Path.cwd();stage=root/'data/dev027/research-src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
    sys.path.insert(0,str(root));from verification.record_check import source_paths
    from verification.frontend_check import browser_run
    def snapshot():return {p.relative_to(stage).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [*source_paths(stage),*(p for p in (stage/'frontend/dist').rglob('*') if p.is_file())]}
    before=snapshot();(out/'funnel-browser-source-before.json').write_text(json.dumps(before,indent=2),encoding='utf-8');sys.path.insert(0,str(stage));sys.path.insert(1,str(stage/'tests'))
    import pandas as pd,uvicorn
    from backend.lab import service
    from backend.lab.service import Lab
    from backend.lab.api import create_app
    from backend.lab.data import save_dataset
    from backend.lab.worker import Worker
    from backend.lab.research_funnel_final import inspect_final,read_final_account
    from backend.lab.research_funnel_jobs import inspect_qualification
    from conftest import minute_frame
    folder=root/'data/dev027/funnel-browser'/uuid.uuid4().hex;lab=Lab(folder);fixtures={}
    days=['2026-11-02','2026-11-03','2026-11-04','2026-11-05','2026-11-06']
    for project,symbols in [('desktop1920',['SPY','QQQ']),('desktop1280',['IWM','DIA']),('mobile390',['AAPL','MSFT'])]:
        frame=pd.concat([minute_frame(day,symbol=symbol) for symbol in symbols for day in days],ignore_index=True)
        dataset=save_dataset(lab.datasets_root,frame,dict(input_kind='synthetic',provider='Authored empty-signal research-funnel browser fixture',corporate_actions_complete=True))
        fixtures[project]=dict(dataset_id=dataset['id'],symbols=symbols)
    shutil.copytree(stage/'frontend/dist',folder/'frontend/dist')
    exports=root/'data/private-evidence/funnel-browser-exports'/out.name;exports.mkdir(parents=True,exist_ok=False)
    app=create_app(folder,run_worker=False);listener=socket.socket();listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='warning',access_log=False))
    stop=threading.Event();failures=[];worker=Worker(lab,stop)
    def run_worker():
        try:
            while not stop.is_set():
                if not worker.run_once():stop.wait(.1)
        except BaseException as error:failures.append(dict(type=type(error).__name__,message=str(error)))
    http=threading.Thread(target=lambda:server.run(sockets=[listener]),daemon=False);work=threading.Thread(target=run_worker,daemon=False)
    generator=service.generate_signals;service.generate_signals=lambda *a,**k:[];exitcode=2;checks=[]
    try:
        http.start();work.start();deadline=time.monotonic()+45
        while not server.started:
            if not http.is_alive() or time.monotonic()>deadline:raise RuntimeError('Owned research browser HTTP failed to start.')
            time.sleep(.1)
        os.environ.update(PA_BROWSER_BASE_URL='http://127.0.0.1:'+str(port),PA_FUNNEL_DATASETS=json.dumps(fixtures),PA_FUNNEL_PRIVATE_EXPORTS=str(exports))
        exitcode=browser_run(['exec','--','playwright','test','--config=../verification/runs/research-funnel-browser.config.ts'])
    finally:
        stop.set();work.join(30);server.should_exit=True;http.join(25);listener.close();service.generate_signals=generator
        (out/'funnel-browser-cleanup.json').write_text(json.dumps(dict(owned_http_retired=not http.is_alive(),owned_worker_retired=not work.is_alive(),source_unchanged=before==snapshot(),worker_failures=failures),indent=2),encoding='utf-8')
        for path in sorted(exports.glob('*-final.json')):
            value=json.loads(path.read_text(encoding='utf-8'));verified=inspect_final(lab,value['job_id']);assert value==verified
            project=path.name[:-len('-final.json')];qualification=json.loads((exports/(project+'-qualification.json')).read_text(encoding='utf-8'))
            assert qualification==inspect_qualification(lab,qualification['job_id']) and len(value['rows'])==2
            inputs=json.loads((exports/(project+'-inputs.json')).read_text(encoding='utf-8'));sid=inputs['study']['id']
            account=json.loads((exports/(project+'-account.json')).read_text(encoding='utf-8'));assert account==read_final_account(lab,value['job_id'],0,'primary_final')
            assert account['trades']==[] and len(account['entry_traces'])==0
            with lab.store.db() as db:
                assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='final_unlock_consumed'",(sid,)).fetchone()[0]==1
                assert db.execute("SELECT COUNT(*) FROM trial_plans WHERE job_id=? AND role='strategy' AND state='completed'",(value['job_id'],)).fetchone()[0]==4
            checks.append(dict(project=project,study_id=sid,final_job_id=value['job_id'],qualification_job_id=qualification['job_id'],complete_versions=2,instruments=2,candidates=0,
                original_final_json_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),all_four_original_downloads_reconciled=True))
        if exitcode==0:assert len(checks)==3
        retired=not http.is_alive() and not work.is_alive();after=snapshot()
        (out/'funnel-browser-subject.json').write_text(json.dumps(dict(scope=__doc__,source_files=before,source_unchanged=before==after,child_exit_code=exitcode,
            owned_http_and_worker_retired=retired,worker_failures=failures,independently_verified_downloads=checks,store=folder.relative_to(root).as_posix(),
            synthetic_empty_signal_accounts=True,actual_detectors_tested=False,completed_random_controls_tested=False,installed_app_untouched=True,final_product_acceptance=False),indent=2),encoding='utf-8')
        assert before==after and retired and not failures
    return exitcode


if __name__=='__main__':raise SystemExit(main())
