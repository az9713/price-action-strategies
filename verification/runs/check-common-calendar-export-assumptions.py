"""Actual calendar-bearing common-search JSON/CSV/offline assumptions, with frozen input parity."""
from pathlib import Path
from io import StringIO
import csv,json,os,urllib.request
base='http://127.0.0.1:8767'
def get(path):
 with urllib.request.urlopen(base+path,timeout=30) as r:return r.read()
jobs=json.loads(get('/api/jobs'));job=next(j for j in jobs if j['status']=='completed' and j['kind']=='search' and j['payload'].get('sampling_policy',{}).get('include_news') is True and j['payload'].get('name','').startswith('Explicit synthetic common modes'))
jid=job['id'];saved=json.loads(get('/api/jobs/'+jid+'/result'));deck=json.loads(get('/api/jobs/'+jid+'/export/presentation.json'));facts={tuple(f['path']):f['value'] for f in deck['facts'].values()}
assert saved['sampling_policy']==job['payload']['sampling_policy'] and saved['news_calendar_id']==job['payload']['news_calendar_id'] and saved['news_calendar']==job['payload']['news_calendar']
assert saved['kind']=='search' and saved['search_screen']['settings']['include_news'] is True
for key in ['id']:
 assert facts[('news_calendar',key)]==saved['news_calendar'][key]
for key in ['start','end','complete','mode','name']:assert facts[('news_calendar','spec',key)]==saved['news_calendar']['spec'][key]
assert facts[('search_screen','settings','include_news')] is True and facts[('sampling','recipe_hash')]==saved['sampling']['recipe_hash']
rows=list(csv.DictReader(StringIO(get('/api/jobs/'+jid+'/search-screen/export/csv').decode())));assert len(rows)==saved['count']==6
assert all(r['include_news']=='True' and r['news_calendar_id']==saved['news_calendar_id'] and r['recipe_hash']==saved['sampling']['recipe_hash'] for r in rows)
value=dict(job_id=jid,core_hash=saved['core_hash'],accounts=len(rows),pages=len(deck['pages']),frozen_calendar_id=saved['news_calendar_id'],knowledge_mode=saved['news_calendar']['spec']['mode'],scope=__doc__)
Path(os.environ['PA_EVIDENCE_RUN_DIR'],'calendar-export-assumptions.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
