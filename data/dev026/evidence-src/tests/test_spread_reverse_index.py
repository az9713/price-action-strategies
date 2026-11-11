"""Nonfinancial reverse-index corruption fixtures; no price or account execution."""
import pytest
from backend.lab.store import Store,StateError

@pytest.mark.parametrize('job_id',['bad','g'*32,'f'*33,'é'*32,b'\x00'*32])
def test_reverse_index_rejects_malformed_child_id_before_any_account_work(tmp_path,job_id):
 store=Store(tmp_path);parent='a'*32
 job=store.create_job('download',dict(spread_parent=dict(job_id=parent),configurations=[]))
 with store.db() as db:
  # Explicit disposable file-corruption injection; normal writes enforce FKs.
  db.execute('PRAGMA foreign_keys=OFF')
  db.execute('UPDATE job_input_index SET job_id=? WHERE job_id=?',(job_id,job['id']))
  with pytest.raises(StateError,match='reservation metadata is malformed'):store.spread_children(parent,db)

def test_reverse_index_returns_at_most_two_child_reservations_from_a_larger_corrupt_set(tmp_path):
 store=Store(tmp_path);parent='a'*32;ids=[]
 for _ in range(3):ids.append(store.create_job('download',dict(spread_parent=dict(job_id=parent),configurations=[]))['id'])
 with store.db() as db:
  result=store.spread_children(parent,db);assert len(result)==2 and set(result)<=set(ids)
  query=db.execute("EXPLAIN QUERY PLAN SELECT job_id FROM job_input_index INDEXED BY spread_child_parent_index WHERE (CASE WHEN json_valid(projection) THEN json_extract(projection,'$.spread_parent.job_id') END) IS NOT NULL AND (CASE WHEN json_valid(projection) THEN json_extract(projection,'$.spread_parent.job_id') END)=? ORDER BY job_id LIMIT 2",(parent,)).fetchall()
  assert any('SEARCH' in r['detail'] and 'spread_child_parent_index' in r['detail'] for r in query)
