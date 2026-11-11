"""Cancel only the explicitly authored slow verification job via Store.cancel."""
from pathlib import Path
import json,os,sys
root=Path.cwd();sys.path.insert(0,str(root/'data/dev027/research-src'))
from backend.lab.store import Store
folder=(root/'data/dev027/funnel-positive/72bda7bd74694a9b82d3a8a9facd1c9d').resolve()
assert folder.is_relative_to((root/'data/dev027/funnel-positive').resolve())
jid='0bb4e66743e1473cb6c344f54fcfef8f';store=Store(folder)
before=store.job_status(jid);assert before['kind']=='trade_twins'
after=store.cancel(jid,public=True)
with store.db() as db:
    parts=db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='twin_part_committed'",(jid,)).fetchone()[0]
    consumed=db.execute("SELECT COUNT(*) FROM events WHERE kind='final_unlock_consumed'").fetchone()[0]
assert consumed==0
value=dict(scope=__doc__,job_id=jid,before=before,after=after,preserved_original_financial_parts=parts,
    final_consumptions=consumed,reason='Both observed financial batches took several minutes;20-book exact replay profile found98percent of execution in repeated input preparation. Optimize before retrying unchanged20000 sets.',
    goal_paused=False,installed_app_untouched=True,processes_forcibly_stopped=False)
(Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'authored-run-cancellation.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value,indent=2))
