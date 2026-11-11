"""Isolated headless browsers over authored source accounts; retire owned HTTP and worker."""
from pathlib import Path
import csv,hashlib,io,json,os,shutil,socket,sys,threading,time,uuid


def main():
    root=Path.cwd();stage=root/'data/dev027/research-src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
    sys.path.insert(0,str(root));from verification.record_check import source_paths
    from verification.frontend_check import browser_run
    def snapshot():return {p.relative_to(stage).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [*source_paths(stage),*(p for p in (stage/'frontend/dist').rglob('*') if p.is_file())]}
    before=snapshot();sys.path.insert(0,str(stage));sys.path.insert(1,str(stage/'tests'))
    import pandas as pd,uvicorn
    from backend.lab import service
    from backend.lab.service import Lab
    from backend.lab.api import create_app
    from backend.lab.models import Search
    from backend.lab.data import save_dataset
    from backend.lab.worker import Worker
    from backend.lab.research_family_jobs import create_analysis,inspect_analysis
    from conftest import minute_frame
    folder=root/'data/dev027/family-browser'/uuid.uuid4().hex;lab=Lab(folder)
    frame=pd.concat([minute_frame(day) for day in ['2026-11-02','2026-11-03','2026-11-04']],ignore_index=True)
    dataset=save_dataset(lab.datasets_root,frame,dict(input_kind='synthetic',provider='Authored browser family accounts with no signals',corporate_actions_complete=True))
    generator=service.generate_signals;service.generate_signals=lambda *a,**k:[]
    try:
        def search(n,seed):
            parent=lab.create_experiment(Search(dataset_id=dataset['id'],start='2026-11-02',end='2026-11-04',seed=seed,count=n,families=['change_of_character'],timeframes=['1m']))
            assert Worker(lab).run_once() and lab.store.job(parent['id'])['status']=='completed'
            return parent
        parent=search(51,42);second=search(3,43);other=create_analysis(lab,second['id'],'change_of_character')
        part=lab.output_path(second['id']).parent/'parts/000000.json.gz';original=part.read_bytes();part.write_bytes(original+b'authored original corruption')
        assert Worker(lab).run_once() and lab.store.job(other['id'])['status']=='failed'
        part.write_bytes(original)
    finally:service.generate_signals=generator
    shutil.copytree(stage/'frontend/dist',folder/'frontend/dist')
    exports=root/'data/private-evidence/family-browser-exports'/out.name;exports.mkdir(parents=True,exist_ok=False)
    app=create_app(folder,run_worker=True);listener=socket.socket();listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='warning',access_log=False))
    thread=threading.Thread(target=lambda:server.run(sockets=[listener]),daemon=False);thread.start();exitcode=2
    try:
        deadline=time.monotonic()+45
        while not server.started:
            if not thread.is_alive() or time.monotonic()>deadline:raise RuntimeError('Owned family browser server failed to start.')
            time.sleep(.1)
        os.environ.update(PA_BROWSER_BASE_URL='http://127.0.0.1:'+str(port),PA_FAMILY_PARENT=parent['id'],PA_FAMILY_OTHER=other['id'],PA_FAMILY_PRIVATE_EXPORTS=str(exports))
        exitcode=browser_run(['exec','--','playwright','test','--config=../verification/runs/research-family-browser.config.ts'])
    finally:
        server.should_exit=True;thread.join(25);listener.close()
        checks=[]
        for path in sorted(exports.glob('*.json')):
            value=json.loads(path.read_text());verified=inspect_analysis(lab,value['job_id'])
            assert value==verified and len(value['rows'])==51 and len(value['report']['marked']['daily'])==3
            csv_path=path.with_suffix('.csv');records=list(csv.DictReader(io.StringIO(csv_path.read_text())))
            assert len(records)==6 and all(row['mean_pnl_numerator']=='0' and row['mean_pnl_denominator']=='1' for row in records)
            checks.append(dict(json_filename=path.name,json_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),csv_sha256=hashlib.sha256(csv_path.read_bytes()).hexdigest(),complete_members=51,daily_conventions=2))
        if exitcode==0:assert len(checks)==3
        after=snapshot();retired=not thread.is_alive() and not app.state.worker_process.is_alive()
        (out/'family-browser-subject.json').write_text(json.dumps(dict(scope=__doc__,source_files=before,source_unchanged=before==after,child_exit_code=exitcode,owned_http_and_worker_retired=retired,original_parent=parent['id'],other_original_analysis=other['id'],other_analysis_real_failure_before_browser=True,independently_verified_downloads=checks,store=folder.relative_to(root).as_posix(),detector_validation=False,financial_signals_authored_empty=True,installed_app_untouched=True,final_product_acceptance=False),indent=2),encoding='utf-8')
        assert before==after and retired
    return exitcode


if __name__=='__main__':raise SystemExit(main())
