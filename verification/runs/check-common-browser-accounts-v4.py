"""Audit all120 v2 account instances, including complete sampling/news export assumptions.
Keep the diagnosed identical-input Sharpe oracle and every original financial tolerance.
"""
from pathlib import Path
source=Path('verification/runs/check-common-browser-accounts-v3.py').read_text(encoding='utf-8')
needle="source=Path('verification/runs/check-common-browser-accounts.py').read_text(encoding='utf-8')"
addition='''
source=source.replace('assert complete==108','assert complete==120')
before="  proposals=job['payload']['sampling']['proposals'];accepted="
after="""  assert saved['sampling_policy']==job['payload']['sampling_policy']
  assert saved['news_calendar_id']==job['payload'].get('news_calendar_id') and saved['news_calendar']==job['payload'].get('news_calendar')
  proposals=job['payload']['sampling']['proposals'];accepted="""
assert source.count(before)==1;source=source.replace(before,after)
before="   for k in ['job_id','dataset_id','core_hash','start','end']:assert csvrow[k]==str(saved[k])"
after=before+"""
   assert csvrow['include_news']==str(screen['settings']['include_news']) and csvrow['recipe_hash']==saved['sampling']['recipe_hash']
   assert csvrow['news_calendar_id']==(saved['news_calendar_id'] or '')"""
assert source.count(before)==1;source=source.replace(before,after)
before="  for later,v in screen['later_stages'].items():"
after="""  assert facts[('search_screen','settings','mode')]==screen['settings']['mode']
  assert facts[('search_screen','settings','include_news')]==screen['settings']['include_news']
  assert facts[('sampling','recipe_hash')]==saved['sampling']['recipe_hash']
  for key in ['signal_definition','scope']:assert facts[('search_screen',key)]==screen[key]
  if saved['news_calendar_id']:assert facts[('news_calendar','id')]==saved['news_calendar_id']
  for later,v in screen['later_stages'].items():"""
assert source.count(before)==1;source=source.replace(before,after)
'''
assert source.count(needle)==1
exec(compile(source.replace(needle,needle+addition),'check-common-browser-accounts-v4-resolved.py','exec'))
