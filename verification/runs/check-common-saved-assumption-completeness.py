"""Verify actual saved common-search exports carry the complete sampling/news/window assumptions."""
from pathlib import Path
import csv,json,os,urllib.request
from io import StringIO
base='http://127.0.0.1:8767'
def get(path):
 with urllib.request.urlopen(base+path,timeout=30) as r:return r.read()
jobs=json.loads(get('/api/jobs'));job=next(j for j in jobs if j['status']=='completed' and j['kind']=='search' and j['payload'].get('sampling_policy',{}).get('mode')=='common_grid' and j['payload'].get('name','').startswith('Explicit synthetic common modes'))
jid=job['id'];saved=json.loads(get('/api/jobs/'+jid+'/result'));deck=json.loads(get('/api/jobs/'+jid+'/export/presentation.json'));facts={tuple(f['path']) for f in deck['facts'].values()}
columns=next(csv.reader(StringIO(get('/api/jobs/'+jid+'/search-screen/export/csv').decode())))
missing=[]
for key in ['sampling_policy','news_calendar_id','news_calendar']:
 if key not in saved:missing.append('root:'+key)
for path in [('search_screen','settings','mode'),('search_screen','settings','include_news'),('sampling','recipe_hash'),('search_screen','signal_definition'),('search_screen','scope')]:
 if path not in facts:missing.append('offline:'+'.'.join(path))
for key in ['include_news','recipe_hash','news_calendar_id']:
 if key not in columns:missing.append('csv:'+key)
result=dict(job_id=jid,core_hash=saved['core_hash'],accounts=len(saved['rows']),pages=len(deck['pages']),missing_assumptions=missing,scope=__doc__)
Path(os.environ['PA_EVIDENCE_RUN_DIR'],'assumption-completeness.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2));assert not missing,'Saved assumptions are incomplete; do not certify the common-search export.'
