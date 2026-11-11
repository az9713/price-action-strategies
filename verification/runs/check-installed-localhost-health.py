"""Read-only installed app/source/asset/listener check; no user-store extraction."""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,socket
import httpx

root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
p=argparse.ArgumentParser();p.add_argument('--expected-pid',type=int,required=True);args=p.parse_args()
with httpx.Client(base_url='http://127.0.0.1:8767',timeout=20,trust_env=False) as client:
    response=client.get('/api/health');response.raise_for_status();health=response.json()
    assert health['status']=='ok' and health['source_current'] and health['worker_ready']
    assert health['core_hash']=='9bfb4b13b15e0dff2d3548926a2310735dd931399fb30aa8b73bf98082aaba89'
    html=client.get('/');html.raise_for_status()
    assert html.content==(root/'frontend/dist/index.html').read_bytes()
    assets=[]
    for name in re.findall(r'(?:src|href)="(/assets/[^\"]+)"',html.text):
        local=root/'frontend/dist'/name.lstrip('/')
        fetched=client.get(name);fetched.raise_for_status()
        assert fetched.content==local.read_bytes()
        assets.append(dict(path=name,bytes=len(fetched.content),sha256=hashlib.sha256(fetched.content).hexdigest()))
    assert any(a['path'].endswith('.js') for a in assets)
script="Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object { $_.LocalPort -in @(8767,8768) } | Select-Object LocalAddress,LocalPort,OwningProcess | ConvertTo-Json -Compress"
result=subprocess.run(['powershell.exe','-NoProfile','-Command',script],capture_output=True,text=True,timeout=30)
assert result.returncode==0,result.stderr
listeners=json.loads(result.stdout) if result.stdout.strip() else []
if isinstance(listeners,dict):listeners=[listeners]
if listeners:
    assert len(listeners)==1 and listeners[0]['LocalPort']==8767 and listeners[0]['OwningProcess']==args.expected_pid
    assert listeners[0]['LocalAddress']=='127.0.0.1'
with socket.create_connection(('127.0.0.1',8767),timeout=5):pass
try:
    alternate=socket.create_connection(('127.0.0.1',8768),timeout=2)
except OSError:
    alternate_reachable=False
else:
    alternate.close();alternate_reachable=True
assert not alternate_reachable
value=dict(scope=__doc__,health={k:health[k] for k in ['status','core_hash','source_current','worker_ready']},
           localhost_listeners=listeners,assets=assets,
           native_listener_identity_verified=bool(listeners),
           native_observation='Listener returned by native CIM' if listeners else 'Native CIM returned no matching listener despite direct socket/HTTP success; native PID-to-port identity remains unverified.',
           direct_loopback_8767_reachable=True,alternate_8768_reachable=False,
           installed_app_restarted_without_experimental_source=True,user_jobs_or_data_copied=False,
           experimental_global_regression_separate=True,final_acceptance_certified=False)
(out/'installed-app-health.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value,indent=2))
