from pathlib import Path
import argparse
import json
from .data import read_manifest
from .config import Strategy
from .models import Download,Experiment
from .service import Lab
from .worker import Worker
from .research import core_hash

ROOT=Path(__file__).resolve().parents[2]

def main():
    parser=argparse.ArgumentParser(description='Local research commands. No live orders.')
    parser.add_argument('--root',type=Path,default=ROOT)
    commands=parser.add_subparsers(dest='command',required=True)
    download=commands.add_parser('download')
    download.add_argument('--symbols',default='SPY,QQQ,IWM,DIA,AAPL,MSFT')
    download.add_argument('--start',default='2022-01-03');download.add_argument('--end',default='2022-01-31')
    run=commands.add_parser('run')
    run.add_argument('dataset');run.add_argument('--family',default='change_of_character');run.add_argument('--timeframe',default='1h')
    run.add_argument('--symbols',default=None)
    run.add_argument('--start');run.add_argument('--end')
    commands.add_parser('worker')
    args=parser.parse_args();lab=Lab(args.root)
    if args.command=='worker':
        from threading import Event
        try: Worker(lab).serve(Event())
        except KeyboardInterrupt: pass
        return
    if args.command=='download':
        spec=Download(symbols=args.symbols.split(','),start=args.start,end=args.end)
        job=lab.store.create_job('download',{**spec.model_dump(mode='json'),'core_hash':core_hash()})
    else:
        manifest=read_manifest(lab.datasets_root,args.dataset)
        start=args.start or manifest['quality']['start'];end=args.end or manifest['quality']['end']
        if args.symbols:
            manifest=lab.select(args.dataset,args.symbols.split(','),start,end)
        job=lab.create_experiment(Experiment(dataset_id=manifest['id'],strategy=Strategy(family=args.family,timeframe=args.timeframe),start=start,end=end))
    print(json.dumps({'job_id':job['id'],'status':job['status']}),flush=True)
    worker=Worker(lab)
    while lab.store.job(job['id'])['status'] in {'queued','running','canceling'}:
        if not worker.run_once():
            from time import sleep
            sleep(.25)
    finished=lab.store.job(job['id'])
    if finished['status']!='completed': raise SystemExit(finished['error'] or finished['status'])
    result=lab.result(job['id'])
    print(json.dumps({k:v for k,v in result.items() if k!='report'},indent=2))
    if 'report' in result: print(json.dumps(result['report']['metrics'],indent=2))

if __name__=='__main__': main()
