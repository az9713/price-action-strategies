"""Sample only the verified owned authored-test process; never collect locals."""
from collections import Counter
from pathlib import Path
import hashlib,json,os,subprocess
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);pid=52504
check=subprocess.run(['powershell','-NoProfile','-Command',
    "$p=Get-CimInstance Win32_Process -Filter 'ProcessId=52504'; if($p){[pscustomobject]@{id=$p.ProcessId;command=$p.CommandLine;created=$p.CreationDate.ToUniversalTime().ToString('o')}|ConvertTo-Json -Compress}"],
    capture_output=True,text=True,timeout=20)
assert check.returncode==0 and check.stdout.strip(),check.stderr
identity=json.loads(check.stdout)
assert identity['id']==pid and 'measure-fresh-market-capacity-current-stage.py' in identity['command']
assert identity['created'].startswith('2026-11-10T18:58:03'),identity['created']
private=root/'data/private-evidence/profiles'/out.name;private.mkdir(parents=True,exist_ok=False)
profile=private/'owned-control.speedscope.json'
result=subprocess.run([str(root/'data/dev027/profiling-tools/py-spy.exe'),'record','--pid',str(pid),
    '--duration','20','--rate','50','--format','speedscope','--output',str(profile)],capture_output=True,text=True,timeout=45)
(private/'profiler-stdout.log').write_text(result.stdout,encoding='utf-8')
(private/'profiler-stderr.log').write_text(result.stderr,encoding='utf-8')
assert result.returncode==0,result.stderr
raw=profile.read_bytes();data=json.loads(raw);frames=data['shared']['frames'];inclusive=Counter();leaves=Counter();project_calls=Counter();observations=0;weight=0
for record in data['profiles']:
    assert record['type']=='sampled'
    for stack,amount in zip(record['samples'],record.get('weights',[1]*len(record['samples']))):
        if not any(Path(frames[i].get('file','')).name=='measure-fresh-market-capacity-current-stage.py' for i in stack):continue
        observations+=1;weight+=amount
        names=[(Path(frames[i].get('file','')).name,frames[i]['name']) for i in stack]
        for name in set(names):inclusive[name]+=amount
        locations={(Path(frames[i].get('file','')).name,frames[i]['name'],frames[i].get('line')) for i in stack
            if '/backend/lab/' in frames[i].get('file','').replace('\\','/')}
        for location in locations:project_calls[location]+=amount
        if names:leaves[names[-1]]+=amount
assert observations>50 and weight>0
def rows(counts):return [dict(file=name[0],function=name[1],weight=value,fraction=value/weight) for name,value in counts.most_common(35)]
value=dict(scope=__doc__,verified_pid=pid,process_created_utc=identity['created'],duration_seconds=20,rate_hz=50,
    target='Owned real-market10000 numerical capacity fixture only',locals_collected=False,product_source_changed=False,
    raw_profile_retained_private=True,raw_profile_sha256=hashlib.sha256(raw).hexdigest(),
    selected_main_samples=observations,selected_main_weight=weight,top_inclusive=rows(inclusive),top_leaf=rows(leaves),
    project_inclusive=[dict(file=name[0],function=name[1],line=name[2],weight=value,fraction=value/weight) for name,value in project_calls.most_common(35)],
    full_financial_comparison_certified=False)
(out/'live-authored-worker-profile.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(dict(top_leaf=value['top_leaf'][:8],selected_main_samples=observations),indent=2))
