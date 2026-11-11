"""Short nonblocking profile of the exact owned optimized 10000-configuration worker; no local variables."""
from collections import Counter
from pathlib import Path
import hashlib,json,os,subprocess

root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
run=root/'verification/runs/20261111T030636680106Z-adopted-numerical-real-market-10000-capacity'
progress=json.loads((run/'capacity-live-progress.json').read_text())
assert progress['job_id']=='8ee40f8ae842454cb0243a749c364750' and progress['count']==10000
query="""$items=Get-CimInstance Win32_Process -Filter "Name='python.exe' AND CommandLine LIKE '%measure-fresh-market-capacity-current-stage.py%'"; @($items | ForEach-Object { [pscustomobject]@{id=$_.ProcessId;command=$_.CommandLine;created=$_.CreationDate.ToUniversalTime().ToString('o');cpu=([double]$_.KernelModeTime+[double]$_.UserModeTime)} }) | ConvertTo-Json -Compress"""
found=subprocess.run(['powershell','-NoProfile','-Command',query],capture_output=True,text=True,timeout=30)
assert found.returncode==0 and found.stdout.strip()
candidates=json.loads(found.stdout)
if isinstance(candidates,dict):candidates=[candidates]
candidates=[p for p in candidates if 'f00ea201d8ad4776ace124d08f704cf7/origin.json' in p['command'] and p['command'].rstrip().endswith('10000')]
assert candidates
selected=max(candidates,key=lambda p:p['cpu']);pid=selected['id']
assert selected['created'].startswith('2026-11-11T03:06:') and '.env' not in selected['command']
private=root/'data/private-evidence/profiles'/out.name;private.mkdir(parents=True,exist_ok=False)
profile=private/'owned-market.speedscope.json'
result=subprocess.run([str(root/'data/dev027/profiling-tools/py-spy.exe'),'record','--pid',str(pid),
    '--duration','10','--rate','25','--nonblocking','--format','speedscope','--output',str(profile)],
    capture_output=True,text=True,timeout=40)
(private/'stdout.log').write_text(result.stdout,encoding='utf-8')
(private/'stderr.log').write_text(result.stderr,encoding='utf-8')
assert result.returncode==0,result.stderr
raw=profile.read_bytes();data=json.loads(raw);frames=data['shared']['frames']
inclusive=Counter();leaves=Counter();locations=Counter();observations=0;weight=0
for record in data['profiles']:
    assert record['type']=='sampled'
    for stack,amount in zip(record['samples'],record.get('weights',[1]*len(record['samples']))):
        if not any(Path(frames[i].get('file','')).name=='measure-fresh-market-capacity-current-stage.py' for i in stack):continue
        observations+=1;weight+=amount
        names=[(Path(frames[i].get('file','')).name,frames[i]['name']) for i in stack]
        for name in set(names):inclusive[name]+=amount
        for location in {(Path(frames[i].get('file','')).name,frames[i]['name'],frames[i].get('line')) for i in stack
                         if '/backend/lab/' in frames[i].get('file','').replace('\\','/')}:
            locations[location]+=amount
        if names:leaves[names[-1]]+=amount
assert observations>30 and weight>0
def rows(counts):return [dict(file=k[0],function=k[1],weight=v,fraction=v/weight) for k,v in counts.most_common(30)]
value=dict(scope=__doc__,job_id=progress['job_id'],verified_pid=pid,created_utc=selected['created'],duration_seconds=10,rate_hz=25,
    nonblocking=True,locals_collected=False,source_changed=False,capacity_run=run.name,
    benchmark_includes_short_external_profile=True,raw_retained_private=True,raw_sha256=hashlib.sha256(raw).hexdigest(),
    samples=observations,weight=weight,top_inclusive=rows(inclusive),top_leaf=rows(leaves),
    project_inclusive=[dict(file=k[0],function=k[1],line=k[2],weight=v,fraction=v/weight) for k,v in locations.most_common(35)],
    full_capacity_certified=False)
(out/'owned-batched-market-profile.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(dict(samples=observations,top_inclusive=value['top_inclusive'][:12],top_leaf=value['top_leaf'][:12]),indent=2))
