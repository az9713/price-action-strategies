"""Owned headless workflow over authored empty-signal accounts; no user store or screen."""
from pathlib import Path
import csv,hashlib,io,json,os,re,shutil,socket,sys,threading,time,uuid,zipfile


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
    # Chrome file:// navigation still has a Windows path-length boundary even
    # when Node's download.saveAs can successfully write the longer path.
    exports=root/'data/private-evidence/funnel-browser-exports'/uuid.uuid4().hex;exports.mkdir(parents=True,exist_ok=False)
    longest=max(len(str(exports/(project+'-'+suffix))) for project in fixtures for suffix in ['inputs.json','qualification.json','final.json','account.json','family-daily.csv','bundle.zip','offline.html'])
    assert longest<240,'Private evidence paths must leave Windows file navigation headroom.'
    (out/'funnel-browser-download-scope.json').write_text(json.dumps(dict(private_export_id=exports.name,
        maximum_expected_absolute_path_characters=longest,windows_navigation_headroom_verified=True),indent=2),encoding='utf-8')
    app=create_app(folder,run_worker=False);listener=socket.socket();listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='warning',access_log=False))
    stop=threading.Event();failures=[];worker=Worker(lab,stop)
    def run_worker():
        try:
            while not stop.is_set():
                if not worker.run_once():stop.wait(.1)
        except BaseException as error:failures.append(dict(type=type(error).__name__,message=str(error)))
    http=threading.Thread(target=lambda:server.run(sockets=[listener]),daemon=False);work=threading.Thread(target=run_worker,daemon=False)
    generator=service.generate_signals;service.generate_signals=lambda *a,**k:[];exitcode=2;checks=[];incomplete=[]
    try:
        http.start();work.start();deadline=time.monotonic()+45
        while not server.started:
            if not http.is_alive() or time.monotonic()>deadline:raise RuntimeError('Owned research browser HTTP failed to start.')
            time.sleep(.1)
        os.environ.update(PA_BROWSER_BASE_URL='http://127.0.0.1:'+str(port),PA_FUNNEL_DATASETS=json.dumps(fixtures),PA_FUNNEL_PRIVATE_EXPORTS=str(exports))
        exitcode=browser_run(['exec','--','playwright','test','--config=../verification/runs/research-funnel-export-browser.config.ts'])
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
            required=[exports/(project+'-'+suffix) for suffix in ['bundle.zip','offline.html','family-daily.csv']]
            missing=[p.name for p in required if not p.exists()]
            if missing:incomplete.append(dict(project=project,missing=missing));continue
            bundle=exports/(project+'-bundle.zip');standalone=(exports/(project+'-offline.html')).read_bytes()
            with zipfile.ZipFile(bundle) as archive:
                manifest=json.loads(archive.read('manifest.json'));assert set(archive.namelist())==set(manifest['entries'])|{'manifest.json'}
                for name,item in manifest['entries'].items():
                    raw=archive.read(name);assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
                assert json.loads(archive.read('original-result.json'))==verified and archive.read('index.html')==standalone
                assert (exports/(project+'-family-daily.csv')).read_bytes()==archive.read('family_daily.csv')
                rows=list(csv.DictReader(io.StringIO(archive.read('family_daily.csv').decode())))
                expected={(family,arm,convention,day['date']):(day['mean_pnl']['numerator'],day['mean_pnl']['denominator']) for arm,summary in verified['report']['arms'].items() for family,average in summary['families'].items() for convention in ['marked','realized_exit_day_compatibility'] for day in average[convention]['daily']}
                assert {(row['family'],row['arm'],row['convention'],row['date']):(row['mean_pnl_numerator'].removeprefix("'"),row['mean_pnl_denominator'].removeprefix("'")) for row in rows}==expected and len(rows)==len(expected)==8
                members=list(csv.DictReader(io.StringIO(archive.read('original_accounts.csv').decode())));assert len(members)==4
                for member in members:assert hashlib.sha256(archive.read(member['archive_path'])).hexdigest()==member['artifact_sha256']
                offline=json.loads(re.search(rb'<script id="evidence" type="application/json">(.*?)</script>',standalone,re.S)[1]);assert len(offline['tables']['versions']['rows'])==2
            checks.append(dict(project=project,study_id=sid,final_job_id=value['job_id'],qualification_job_id=qualification['job_id'],complete_versions=2,instruments=2,candidates=0,
                original_final_json_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),all_four_original_downloads_reconciled=True,complete_csv_zip_offline_downloads_reconciled=True,downloaded_files=7,complete_phase_account_files_in_zip=4,complete_family_daily_records=8))
        if exitcode==0:assert len(checks)==3 and not incomplete
        retired=not http.is_alive() and not work.is_alive();after=snapshot()
        (out/'funnel-browser-subject.json').write_text(json.dumps(dict(scope=__doc__,source_files=before,source_unchanged=before==after,child_exit_code=exitcode,
            owned_http_and_worker_retired=retired,worker_failures=failures,independently_verified_downloads=checks,incomplete_download_sets=incomplete,store=folder.relative_to(root).as_posix(),
            private_export_id=exports.name,maximum_expected_download_path_characters=longest,
            synthetic_empty_signal_accounts=True,actual_detectors_tested=False,completed_random_controls_tested=False,installed_app_untouched=True,final_product_acceptance=False),indent=2),encoding='utf-8')
        assert before==after and retired and not failures
    return exitcode


if __name__=='__main__':raise SystemExit(main())
