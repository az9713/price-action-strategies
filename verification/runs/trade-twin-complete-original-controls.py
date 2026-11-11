"""Actual complete original 10000-set policies; an unsuccessful control is retained."""
from decimal import Decimal
from pathlib import Path
import gzip,hashlib,json,os,time
from backend.lab import trade_twin_jobs as jobs
from backend.lab.trade_twin_views import Originals
from backend.lab.trade_twins import EXECUTION_POLICIES,TOTAL_SETS
from backend.lab.worker import Worker
from test_trade_twin_source import original


def test_complete_owned_original_policies_keep_every_occurrence_and_independent_exact_totals(original):
    lab,parent,_=original;child=jobs.create(lab,parent['id']);started=time.perf_counter()
    assert TOTAL_SETS==10000
    assert Worker(lab).run_once()
    job=lab.store.job(child['id']);assert job['status']=='completed',job
    saved=Originals(lab,child['id']);report=saved.report
    assert report['comparison_eligible'] and report['financial_occurrences']==20000
    assert len(saved.headers)==100
    seen={p:set() for p in EXECUTION_POLICIES};books={};counts={p:0 for p in EXECUTION_POLICIES}
    exceeds={p:0 for p in EXECUTION_POLICIES};part_digests=[]
    for header in saved.headers:
        with lab.store.db() as db:
            db.execute('BEGIN');_,_,path=saved.part(db,header['part'])
        raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==header['sha256']
        value=json.loads(gzip.decompress(raw));part_digests.append(header['sha256'])
        for entry in value['books']:
            assert entry['key'] not in books
            books[entry['key']]=entry
        for row in value['sets']:
            result=row['outcome'];policy=result['policy'];ordinal=result['set_index']
            assert ordinal not in seen[policy] and len(row['members'])==result['trade_count']==1
            seen[policy].add(ordinal);counts[policy]+=1
            actual=[books[member['book_key']]['book'] for member in row['members']]
            assert all(book['status']=='complete' for book in actual) and result['state']=='completed'
            net=sum((Decimal(book['net_profit']) for book in actual),Decimal(0))
            assert Decimal(result['net_profit'])==net
            exceeds[policy]+=net>=Decimal(report['summaries'][policy]['real_profit'])
    saved.guard()
    for policy in EXECUTION_POLICIES:
        summary=report['summaries'][policy]
        assert seen[policy]==set(range(10000))
        assert summary['observed_sets']==summary['expected_sets']==summary['complete_sets']==counts[policy]==10000
        assert summary['failed_sets']==0 and summary['exceedances']==exceeds[policy]
        assert summary['adapted_pass'] is (exceeds[policy]<500)
    with lab.store.db() as db:
        trials=db.execute("SELECT COUNT(*) FROM trial_plans WHERE job_id=? AND role='trade_twin_set' AND state='completed' AND attempts=1",(child['id'],)).fetchone()[0]
        assert trials==20000
        assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='twin_part_committed'",(child['id'],)).fetchone()[0]==100
    out=os.environ.get('PA_EVIDENCE_RUN_DIR')
    if out:Path(out,'actual-complete-single-source-original-controls.json').write_text(json.dumps(dict(
        scope=__doc__,source_cohort_size=1,actual_original_set_occurrences=20000,policies=counts,
        exceedances=exceeds,complete_original_parts=100,part_digests=part_digests,
        original_financial_books=len(books),original_completed_trials=trials,elapsed_seconds=time.perf_counter()-started,
        source_prices_are_authored=True,market_edge_claimed=False,full_funnel_certified=False),indent=2),encoding='utf-8')
