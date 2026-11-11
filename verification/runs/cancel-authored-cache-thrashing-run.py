"""Normally cancel only the authored worker exhibiting measured cache thrashing."""
from pathlib import Path
import json,os,sys
root=Path.cwd();sys.path.insert(0,str(root/'data/dev027/research-src'))
from backend.lab.store import Store
folder=(root/'data/dev027/funnel-positive/e4930345acd847bba17352f24c6565d7').resolve()
assert folder.is_relative_to((root/'data/dev027/funnel-positive').resolve())
store=Store(folder);jid='b6d29c1d3f6e4d9bbc426637c8ae8ca9';before=store.job_status(jid)
assert before['kind']=='trade_twins'
after=store.cancel(jid,public=True)
with store.db() as db:
    parts=db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='twin_part_committed'",(jid,)).fetchone()[0]
    sets=db.execute("SELECT COUNT(*) FROM trial_plans WHERE job_id=? AND role='trade_twin_set' AND state IN ('checkpointed','completed')",(jid,)).fetchone()[0]
    consumed=db.execute("SELECT COUNT(*) FROM events WHERE kind='final_unlock_consumed'").fetchone()[0]
assert consumed==0
fields=['id','kind','status','progress','checkpoint']
value=dict(scope=__doc__,before={k:before.get(k) for k in fields},after={k:after.get(k) for k in fields},
    preserved_financial_parts=parts,preserved_financial_sets=sets,required_financial_sets=20000,final_consumptions=consumed,
    profile_receipt='20261110T145004120145Z-control-part6-live-profile',
    reason='Part6 crossed the4-part decoded cache boundary and took767seconds. Live samples:85percent in book lookup,79percent in whole-part load,59percent in live-control connection selection; all original checks must remain.',
    goal_paused=False,installed_app_untouched=True,processes_forcibly_stopped=False)
(Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'authored-thrashing-run-cancellation.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value,indent=2))
