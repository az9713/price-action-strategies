"""Wire only the isolated frontend; main source, installed packages and served assets stay separate."""
from pathlib import Path
import hashlib,json,os,shutil
root=Path.cwd();frontend=root/'data/dev025/src/frontend';app=frontend/'src/App.tsx';value=app.read_text(encoding='utf-8');before=hashlib.sha256(app.read_bytes()).hexdigest()
changes=[
 ("import {TrialLedger} from './TrialLedger';","import {TrialLedger} from './TrialLedger';\nimport {SpreadFlow} from './SpreadFlow';"),
 ("  const [ablationJob,setAblationJob]", "  const [spreadJob,setSpreadJob]=useState('');\n  const [ablationJob,setAblationJob]"),
 ("      if(value.requires_index){", "      if(value.kind==='spread'){setSpreadJob(jid);if(go&&navigationRevision.current===navigationAtStart)setPage('Experiments');return;}\n      if(value.requires_index){"),
 ('<Panel title="Job queue">','<SpreadFlow input={request()} dataset={dataset} familyLabels={schema.families} statistics={statistics} jobs={jobs} jobId={spreadJob} onJob={setSpreadJob} onRefresh={refresh} onAccount={id=>{void action(()=>openResult(id));}}/><Panel title="Job queue">'),
 ("isSearch={result?.kind==='search'}","isSearch={['search','spread_accounts'].includes(result?.kind)}"),
]
for old,new in changes:
 assert value.count(old)==1,(old,value.count(old));value=value.replace(old,new,1)
app.write_text(value,encoding='utf-8');shutil.copyfile(root/'data/dev025/ui-stage/SpreadFlow.tsx',frontend/'src/SpreadFlow.tsx')
result=dict(scope=__doc__,app_before_sha256=before,app_after_sha256=hashlib.sha256(app.read_bytes()).hexdigest(),declared_replacements=len(changes),main_source_not_replaced=True)
if os.environ.get('PA_EVIDENCE_RUN_DIR'):(Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'spread-ui-wiring.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
