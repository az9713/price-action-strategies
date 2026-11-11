# Continuation failed checks

Nonzero command exits include authored counterexamples, environment failures and harness faults. They are not all product defects. Excerpts are bounded and sanitized; original logs remain linked.

## 20261109T190558345900Z-trade-twins-original-report-extractor-authored-absence-assertion

[Original receipt](../../verification/receipts/20261109T190558345900Z-trade-twins-original-report-extractor-authored-absence-assertion.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T190558345900Z-trade-twins-original-report-extractor-authored-absence-assertion/stdout.log)

~~~~text
F                                                                        [100%]
================================== FAILURES ===================================
_____________ test_original_saved_source_extractor_is_implemented _____________

    def test_original_saved_source_extractor_is_implemented():
>       assert importlib.util.find_spec('backend.lab.trade_twin_source') is not None,'Original account extraction is not implemented.'
E       AssertionError: Original account extraction is not implemented.
E       assert None is not None
E        +  where None = <function find_spec at 0x000001AADF42F060>('backend.lab.trade_twin_source')
E        +    where <function find_spec at 0x000001AADF42F060> = <module 'importlib.util' (frozen)>.find_spec
E        +      where <module 'importlib.util' (frozen)> = importlib.util

tests\test_trade_twin_source.py:17: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_source.py::test_original_saved_source_extractor_is_implemented
1 failed in 1.54s
~~~~

[Original stderr.log](../../verification/runs/20261109T190558345900Z-trade-twins-original-report-extractor-authored-absence-assertion/stderr.log)

~~~~text

~~~~

## 20261109T190723737839Z-trade-twins-original-report-cohort-entry-signal-ledger-and-split-extraction-first-contracts

[Original receipt](../../verification/receipts/20261109T190723737839Z-trade-twins-original-report-cohort-entry-signal-ledger-and-split-extraction-first-contracts.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T190723737839Z-trade-twins-original-report-cohort-entry-signal-ledger-and-split-extraction-first-contracts/stdout.log)

~~~~text
                raise ValueError('Original account ledger is missing or malformed.')
            entries=_index([row for row in ledger if row.get('kind')=='entry'],'trade_id','entry ledger')
            if set(trades)!=set(traces) or set(trades)!=set(entries) or len(trades)>MAX_SOURCE_TRADES:
                raise ValueError('Every original executed trade requires exactly one entry trace and entry ledger; no subset is accepted.')
            output=[];closed=Decimal(0)
            for tid,trade in sorted(trades.items()):
                _cancel(cancel)
                trace=traces[tid];entry=entries[tid];signal=signals.get(tid)
                if (set(trace)!=TRACE_KEYS or type(trace['version']) is not int or trace['version']!=1 or
                    trace['trace_sha256']!=identity({k:v for k,v in trace.items() if k!='trace_sha256'})):
                    raise ValueError('Original entry trace schema or digest differs.')
                if signal is None or trace['signal_sha256']!=identity(signal):raise ValueError('Original entry signal binding differs.')
                if trace['config_id']!=cid or trace['costs_sha256']!=identity(costs) or trace['portfolio_sha256']!=identity(account):
>                   raise ValueError('Original entry assumptions differ.')
E                   ValueError: Original entry assumptions differ.

backend\lab\trade_twin_source.py:75: ValueError
=============================== tests coverage ================================
_______________ coverage: platform win32, python 3.13.5-final-0 _______________

Coverage JSON written to file <workspace>\verification\runs\20261109T190723737839Z-trade-twins-original-report-cohort-entry-signal-ledger-and-split-extraction-first-contracts/source-coverage.json
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_source.py::test_actual_split_account_uses_entry_stop_not_exit_stop
1 failed, 39 passed in 12.55s
~~~~

[Original stderr.log](../../verification/runs/20261109T190723737839Z-trade-twins-original-report-cohort-entry-signal-ledger-and-split-extraction-first-contracts/stderr.log)

~~~~text

~~~~

## 20261109T191137143222Z-trade-twins-original-saved-store-authority-reader-authored-absence-assertion

[Original receipt](../../verification/receipts/20261109T191137143222Z-trade-twins-original-saved-store-authority-reader-authored-absence-assertion.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T191137143222Z-trade-twins-original-saved-store-authority-reader-authored-absence-assertion/stdout.log)

~~~~text
F                                                                        [100%]
================================== FAILURES ===================================
_ test_saved_reader_requires_real_original_authority_and_does_not_recompute_or_write _

source_module = <module 'backend.lab.trade_twin_source' from '<workspace>\\data\\dev026\\src\\backend\\lab\\trade_twin_source.py'>
original = (<backend.lab.service.Lab object at 0x0000020A30057E00>, {'id': '913745aa4c224be4aeb21a3435f7cc14', 'kind': 'experimen...th', 'entry': 'next_open', ...}, 'config_id': '1505c9f0c8c8bd8e3c7d080174163547dc173753d94d1f2ef5d09f45e1c527a6', ...})
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x0000020A4981E190>

    def test_saved_reader_requires_real_original_authority_and_does_not_recompute_or_write(source_module,original,monkeypatch):
        lab,job,report=original
>       assert hasattr(source_module,'read_saved_source'), 'Saved original source authority reader is not implemented.'
E       AssertionError: Saved original source authority reader is not implemented.
E       assert False
E        +  where False = hasattr(<module 'backend.lab.trade_twin_source' from '<workspace>\\data\\dev026\\src\\backend\\lab\\trade_twin_source.py'>, 'read_saved_source')

tests\test_trade_twin_source.py:92: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_source.py::test_saved_reader_requires_real_original_authority_and_does_not_recompute_or_write
1 failed in 2.15s
~~~~

[Original stderr.log](../../verification/runs/20261109T191137143222Z-trade-twins-original-saved-store-authority-reader-authored-absence-assertion/stderr.log)

~~~~text

~~~~

## 20261109T191257164751Z-trade-twins-first-original-saved-input-root-trial-attempt-view-and-source-authorization-contracts

[Original receipt](../../verification/receipts/20261109T191257164751Z-trade-twins-first-original-saved-input-root-trial-attempt-view-and-source-authorization-contracts.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T191257164751Z-trade-twins-first-original-saved-input-root-trial-attempt-view-and-source-authorization-contracts/stdout.log)

~~~~text

backend\lab\trade_twin_source.py:126: AttributeError
=============================== tests coverage ================================
_______________ coverage: platform win32, python 3.13.5-final-0 _______________

Coverage JSON written to file <workspace>\verification\runs\20261109T191257164751Z-trade-twins-first-original-saved-input-root-trial-attempt-view-and-source-authorization-contracts/source-coverage.json
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_source.py::test_saved_reader_requires_real_original_authority_and_does_not_recompute_or_write
FAILED tests/test_trade_twin_source.py::test_original_storage_guard_faults_refuse_without_new_jobs[root_bytes]
FAILED tests/test_trade_twin_source.py::test_original_storage_guard_faults_refuse_without_new_jobs[result_event]
FAILED tests/test_trade_twin_source.py::test_original_storage_guard_faults_refuse_without_new_jobs[frozen_inputs]
FAILED tests/test_trade_twin_source.py::test_original_storage_guard_faults_refuse_without_new_jobs[payload]
FAILED tests/test_trade_twin_source.py::test_original_storage_guard_faults_refuse_without_new_jobs[trial_computation]
FAILED tests/test_trade_twin_source.py::test_original_storage_guard_faults_refuse_without_new_jobs[trial_artifact]
FAILED tests/test_trade_twin_source.py::test_original_storage_guard_faults_refuse_without_new_jobs[attempt_computation]
FAILED tests/test_trade_twin_source.py::test_original_storage_guard_faults_refuse_without_new_jobs[attempt_artifact]
FAILED tests/test_trade_twin_source.py::test_original_storage_guard_faults_refuse_without_new_jobs[missing_attempt]
FAILED tests/test_trade_twin_source.py::test_original_storage_guard_faults_refuse_without_new_jobs[trial_state]
FAILED tests/test_trade_twin_source.py::test_original_storage_guard_faults_refuse_without_new_jobs[job_state]
FAILED tests/test_trade_twin_source.py::test_original_storage_guard_faults_refuse_without_new_jobs[view_missing]
FAILED tests/test_trade_twin_source.py::test_original_storage_guard_faults_refuse_without_new_jobs[manifest_bytes]
FAILED tests/test_trade_twin_source.py::test_original_single_account_part_identity_is_strict[1]
FAILED tests/test_trade_twin_source.py::test_saved_source_still_obeys_protected_price_guard_and_cancellation
16 failed, 44 passed in 18.55s
~~~~

[Original stderr.log](../../verification/runs/20261109T191257164751Z-trade-twins-first-original-saved-input-root-trial-attempt-view-and-source-authorization-contracts/stderr.log)

~~~~text

~~~~

## 20261109T191402286041Z-trade-twins-saved-source-original-input-index-owner-and-fault-contracts

[Original receipt](../../verification/receipts/20261109T191402286041Z-trade-twins-saved-source-original-input-index-owner-and-fault-contracts.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T191402286041Z-trade-twins-saved-source-original-input-index-owner-and-fault-contracts/stdout.log)

~~~~text
        with lab.store.db() as db:
            db.execute('BEGIN')
            job,digest,provenance=lab.store._input_index.verified_inputs(jid,db)
            if job['status']!='completed' or job['kind'] not in {'experiment','search','spread_accounts'} or provenance!='prespecified':
                raise StateError('Use a completed original independent strategy/search account, not a legacy or final-test report.')
            lab.store._trials.verify(jid,db)
            payload=job['payload']
            if payload.get('core_hash')!=core_hash():raise StateError('Original account uses another numerical source; create a new explicitly identified account.')
            configs=[payload['strategy']] if job['kind']=='experiment' else payload['configurations']
            if not isinstance(configs,list) or part>=len(configs):raise StateError('Unknown original configuration ordinal.')
            incomplete=db.execute("SELECT COUNT(*) FROM trial_plans WHERE job_id=? AND (window!='report' OR state!='checkpointed')",(jid,)).fetchone()[0]
>           if incomplete:raise StateError('The full original account plan has incomplete trial evidence.')
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           backend.lab.store.StateError: The full original account plan has incomplete trial evidence.

backend\lab\trade_twin_source.py:135: StateError
=============================== tests coverage ================================
_______________ coverage: platform win32, python 3.13.5-final-0 _______________

Coverage JSON written to file <workspace>\verification\runs\20261109T191402286041Z-trade-twins-saved-source-original-input-index-owner-and-fault-contracts/source-coverage.json
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_source.py::test_saved_reader_requires_real_original_authority_and_does_not_recompute_or_write
FAILED tests/test_trade_twin_source.py::test_saved_source_still_obeys_protected_price_guard_and_cancellation
2 failed, 58 passed in 18.23s
~~~~

[Original stderr.log](../../verification/runs/20261109T191402286041Z-trade-twins-saved-source-original-input-index-owner-and-fault-contracts/stderr.log)

~~~~text

~~~~

## 20261109T191625704451Z-trade-twins-late-price-manifest-authority-changes-authored-refusal-contract

[Original receipt](../../verification/receipts/20261109T191625704451Z-trade-twins-late-price-manifest-authority-changes-authored-refusal-contract.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T191625704451Z-trade-twins-late-price-manifest-authority-changes-authored-refusal-contract/stdout.log)

~~~~text
    def test_late_original_changes_cannot_become_authorized_source(source_module,original,monkeypatch,fault):
        from backend.lab.store import StateError
        lab,job,_=original;extract=source_module.extract_report
        def changed(*args,**kwargs):
            result=extract(*args,**kwargs)
            if fault=='price_bytes':
                p=lab.datasets_root/job['payload']['dataset_id']/'minutes.parquet';raw=bytearray(p.read_bytes());raw[-1]^=1;p.write_bytes(raw)
            elif fault=='manifest_bytes':
                p=lab.datasets_root/job['payload']['dataset_id']/'manifest.json';v=json.loads(p.read_text());v['metadata']['provider']='late change';p.write_text(json.dumps(v))
            else:
                with lab.store.db() as db:
                    if fault=='job_state':db.execute("UPDATE jobs SET status='failed' WHERE id=?",(job['id'],))
                    else:db.execute("UPDATE events SET details=? WHERE entity_id=? AND kind='result_saved'",(json.dumps(dict(sha256='0'*64)),job['id']))
            return result
        monkeypatch.setattr(source_module,'extract_report',changed)
>       with pytest.raises(StateError):source_module.read_saved_source(lab,job['id'])
             ^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE StateError

tests\test_trade_twin_source.py:209: Failed
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_source.py::test_late_original_changes_cannot_become_authorized_source[price_bytes]
FAILED tests/test_trade_twin_source.py::test_late_original_changes_cannot_become_authorized_source[manifest_bytes]
2 failed, 2 passed, 68 deselected in 3.03s
~~~~

[Original stderr.log](../../verification/runs/20261109T191625704451Z-trade-twins-late-price-manifest-authority-changes-authored-refusal-contract/stderr.log)

~~~~text

~~~~

## 20261109T192113779290Z-trade-twins-authored-original-trial-event-loss-with-intact-current-row-refusal

[Original receipt](../../verification/receipts/20261109T192113779290Z-trade-twins-authored-original-trial-event-loss-with-intact-current-row-refusal.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T192113779290Z-trade-twins-authored-original-trial-event-loss-with-intact-current-row-refusal/stdout.log)

~~~~text
tests\test_trade_twin_source.py:262: Failed
_ test_missing_original_trial_events_cannot_be_replaced_by_intact_current_rows[search] _

source_module = <module 'backend.lab.trade_twin_source' from '<workspace>\\data\\dev026\\src\\backend\\lab\\trade_twin_source.py'>
original = (<backend.lab.service.Lab object at 0x0000023BCCF360D0>, {'id': '71edfbd799d94053b0a1a14e499d1f71', 'kind': 'experimen...th', 'entry': 'next_open', ...}, 'config_id': '1505c9f0c8c8bd8e3c7d080174163547dc173753d94d1f2ef5d09f45e1c527a6', ...})
kind = 'search'

    @pytest.mark.parametrize('kind',['single','search'])
    def test_missing_original_trial_events_cannot_be_replaced_by_intact_current_rows(source_module,original,kind):
        from backend.lab.store import StateError
        lab,job,_=original
        if kind=='search':lab,job=search_original(original)
        event='trial_computation_started' if kind=='single' else 'trial_checkpoint_saved'
        with lab.store.db() as db:db.execute('DELETE FROM events WHERE entity_id=? AND kind=?',(job['id'],event))
        before=database_fingerprint(lab)
>       with pytest.raises(StateError):source_module.read_saved_source(lab,job['id'])
             ^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE StateError

tests\test_trade_twin_source.py:262: Failed
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_source.py::test_missing_original_trial_events_cannot_be_replaced_by_intact_current_rows[single]
FAILED tests/test_trade_twin_source.py::test_missing_original_trial_events_cannot_be_replaced_by_intact_current_rows[search]
2 failed, 78 deselected in 2.61s
~~~~

[Original stderr.log](../../verification/runs/20261109T192113779290Z-trade-twins-authored-original-trial-event-loss-with-intact-current-row-refusal/stderr.log)

~~~~text

~~~~

## 20261109T192619985315Z-trade-twins-actual-owned-retry-with-original-checkpoint-history-authored-authority-contract

[Original receipt](../../verification/receipts/20261109T192619985315Z-trade-twins-actual-owned-retry-with-original-checkpoint-history-authored-authority-contract.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T192619985315Z-trade-twins-actual-owned-retry-with-original-checkpoint-history-authored-authority-contract/stdout.log)

~~~~text

db = <sqlite3.Connection object at 0x0000025DB201BB50>
jid = '9662459dab1c4cc48b5911d40413a8a4', kind = 'trial_checkpoint_saved'
trial_id = '8ddbcc3a9a277f14c6017c7c71d8d551bdacf0674b4441cd72bd8d8f46fbdde4'
expected = {'trial_id': '8ddbcc3a9a277f14c6017c7c71d8d551bdacf0674b4441cd72bd8d8f46fbdde4', 'part': 0, 'window': 'report', 'sha256': 'a21b26d7f139738f23a40786c90b98f84af55a54a638c01cce7f97681d5d5a1f'}

    def _original_trial_event(db,jid,kind,trial_id,expected):
        rows=db.execute("SELECT details FROM events WHERE entity_id=? AND kind=? AND CASE WHEN json_valid(details) THEN json_extract(details,'$.trial_id') END=? ORDER BY id",(jid,kind,trial_id))
        matching=0
        for row in rows:
            raw=row['details']
            if len(raw.encode('utf-8'))>4096:raise StateError('Original trial event exceeds its fixed metadata bound.')
            value=json.loads(raw)
            if kind=='trial_computation_started' and value.get('attempt')!=expected['attempt']:continue
            if value!=expected:raise StateError('Original trial event differs from its recorded occurrence.')
            matching+=1
>       if matching!=1:raise StateError('Exactly one intact original trial event is required.')
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       backend.lab.store.StateError: Exactly one intact original trial event is required.

backend\lab\trade_twin_source.py:132: StateError
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_source.py::test_actual_owned_retry_retains_old_checkpoint_and_selects_latest_original_attempt
1 failed in 2.85s
~~~~

[Original stderr.log](../../verification/runs/20261109T192619985315Z-trade-twins-actual-owned-retry-with-original-checkpoint-history-authored-authority-contract/stderr.log)

~~~~text

~~~~

## 20261109T193107063179Z-trade-twins-typed-original-trade-direction-authored-refusal-counterexample

[Original receipt](../../verification/receipts/20261109T193107063179Z-trade-twins-typed-original-trade-direction-authored-refusal-counterexample.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T193107063179Z-trade-twins-typed-original-trade-direction-authored-refusal-counterexample/stdout.log)

~~~~text
        elif fault=='ledger_none':r['ledger']=None
        elif fault=='ledger_row':r['ledger'].append(None)
        elif fault=='trades_none':r['trades']=None
        elif fault=='signal_id':r['signals'][0]['id']=42
        elif fault=='missing_signal':r['signals']=[]
        elif fault=='missing_exit':r['trades'][0].pop('exit_at')
        elif fault=='signal_clock':
            r['signals'][0]['available_at']='2026-11-04T14:49:00+00:00';trace['signal_sha256']=identity(r['signals'][0])
        elif fault=='fee_negative':trace['entry_fee']=-1.
        elif fault=='quantity_bool':trace['quantity']=True
        elif fault=='direction_bool':trace['side']=True
        elif fault=='trade_direction_bool':r['trades'][0]['side']=True
        elif fault=='seed_bool':r['seed']=True
        elif fault=='missing_payload':payload.pop('start')
        elif fault=='metric_bool':r['metrics']['net_profit']=False
        if isinstance(r,dict):trace['trace_sha256']=identity({k:v for k,v in trace.items() if k!='trace_sha256'})
>       with pytest.raises(ValueError):source_module.extract_report(r,payload,CFG.model_dump())
             ^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE ValueError

tests\test_trade_twin_source.py:313: Failed
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_source.py::test_strict_original_report_shape_and_typed_evidence_boundaries[trade_direction_bool]
1 failed, 106 deselected in 5.23s
~~~~

[Original stderr.log](../../verification/runs/20261109T193107063179Z-trade-twins-typed-original-trade-direction-authored-refusal-counterexample/stderr.log)

~~~~text

~~~~

## 20261109T194429774545Z-trade-twins-ten-actual-original-source-cohort-identity-event-trial-and-late-authority-mutations

[Original receipt](../../verification/receipts/20261109T194429774545Z-trade-twins-ten-actual-original-source-cohort-identity-event-trial-and-late-authority-mutations.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T194429774545Z-trade-twins-ten-actual-original-source-cohort-identity-event-trial-and-late-authority-mutations/stdout.log)

~~~~text
{"name": "baseline", "exit_code": 0, "elapsed_seconds": 8.727855700009968, "tests": 12, "failures": 0, "errors": 0, "skipped": 0}
{"name": "whole-executed-cohort", "exit_code": 1, "elapsed_seconds": 5.9523494000022765, "tests": 1, "failures": 1, "errors": 0, "skipped": 0}
{"name": "original-cost-identity", "exit_code": 1, "elapsed_seconds": 6.05335400000331, "tests": 1, "failures": 1, "errors": 0, "skipped": 0}
{"name": "original-signal-identity", "exit_code": 1, "elapsed_seconds": 9.692006800003583, "tests": 1, "failures": 1, "errors": 0, "skipped": 0}
{"name": "original-entry-ledger", "exit_code": 1, "elapsed_seconds": 7.743931600009091, "tests": 1, "failures": 1, "errors": 0, "skipped": 0}
{"name": "original-event-loss", "exit_code": 1, "elapsed_seconds": 15.375721399992472, "tests": 2, "failures": 2, "errors": 0, "skipped": 0}
{"name": "original-attempt-output", "exit_code": 1, "elapsed_seconds": 5.705490199994529, "tests": 1, "failures": 1, "errors": 0, "skipped": 0}
{"name": "original-trial-output", "exit_code": 1, "elapsed_seconds": 6.967098799999803, "tests": 1, "failures": 1, "errors": 0, "skipped": 0}
{"name": "late-original-price", "exit_code": 1, "elapsed_seconds": 13.831971099978546, "tests": 1, "failures": 1, "errors": 0, "skipped": 0}
{"name": "late-original-manifest", "exit_code": 0, "elapsed_seconds": 7.509517900005449, "tests": 1, "failures": 0, "errors": 0, "skipped": 0}
~~~~

[Original stderr.log](../../verification/runs/20261109T194429774545Z-trade-twins-ten-actual-original-source-cohort-identity-event-trial-and-late-authority-mutations/stderr.log)

~~~~text
Traceback (most recent call last):
  File "<workspace>\verification\runs\trade-twins-source-authority-mutations.py", line 35, in <module>
    exec(compile(code,'recorded-original-source-authority-mutation-harness','exec'))
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "recorded-original-source-authority-mutation-harness", line 43, in <module>
AssertionError: late-original-manifest
~~~~

[Original stderr.log](../../verification/runs/20261109T194429774545Z-trade-twins-ten-actual-original-source-cohort-identity-event-trial-and-late-authority-mutations/baseline/stderr.log)

~~~~text

~~~~

[Original stdout.log](../../verification/runs/20261109T194429774545Z-trade-twins-ten-actual-original-source-cohort-identity-event-trial-and-late-authority-mutations/baseline/stdout.log)

~~~~text
............                                                             [100%]

12 passed, 103 deselected in 6.48s

~~~~

[Original stderr.log](../../verification/runs/20261109T194429774545Z-trade-twins-ten-actual-original-source-cohort-identity-event-trial-and-late-authority-mutations/late-original-manifest/stderr.log)

~~~~text

~~~~

[Original stdout.log](../../verification/runs/20261109T194429774545Z-trade-twins-ten-actual-original-source-cohort-identity-event-trial-and-late-authority-mutations/late-original-manifest/stdout.log)

~~~~text
.                                                                        [100%]

1 passed, 114 deselected in 4.20s

~~~~

[Original stderr.log](../../verification/runs/20261109T194429774545Z-trade-twins-ten-actual-original-source-cohort-identity-event-trial-and-late-authority-mutations/late-original-price/stderr.log)

~~~~text

~~~~

[Original stdout.log](../../verification/runs/20261109T194429774545Z-trade-twins-ten-actual-original-source-cohort-identity-event-trial-and-late-authority-mutations/late-original-price/stdout.log)

~~~~text
                    if fault=='job_state':db.execute("UPDATE jobs SET status='failed' WHERE id=?",(job['id'],))

                    else:db.execute("UPDATE events SET details=? WHERE entity_id=? AND kind='result_saved'",(json.dumps(dict(sha256='0'*64)),job['id']))

            return result

        monkeypatch.setattr(source_module,'extract_report',changed)

>       with pytest.raises(StateError):source_module.read_saved_source(lab,job['id'])

             ^^^^^^^^^^^^^^^^^^^^^^^^^

E       Failed: DID NOT RAISE StateError



tests\test_trade_twin_source.py:213: Failed

=========================== short test summary info ===========================

FAILED tests/test_trade_twin_source.py::test_late_original_changes_cannot_become_authorized_source[price_bytes]

1 failed, 114 deselected in 7.80s

~~~~

[Original stderr.log](../../verification/runs/20261109T194429774545Z-trade-twins-ten-actual-original-source-cohort-identity-event-trial-and-late-authority-mutations/original-attempt-output/stderr.log)

~~~~text

~~~~

[Original stdout.log](../../verification/runs/20261109T194429774545Z-trade-twins-ten-actual-original-source-cohort-identity-event-trial-and-late-authority-mutations/original-attempt-output/stdout.log)

~~~~text
                if fault=='trial_state':db.execute("UPDATE trial_plans SET state='computed' WHERE job_id=?",(jid,))

                if fault=='job_state':db.execute("UPDATE jobs SET status='failed' WHERE id=?",(jid,))

                if fault=='view_missing':db.execute("DELETE FROM events WHERE entity_id=? AND kind='result_view_saved'",(jid,))

        before=database_fingerprint(lab)

>       with pytest.raises((StateError,ValueError)):source_module.read_saved_source(lab,jid)

             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

E       Failed: DID NOT RAISE any of (StateError, ValueError)



tests\test_trade_twin_source.py:130: Failed

=========================== short test summary info ===========================

FAILED tests/test_trade_twin_source.py::test_original_storage_guard_faults_refuse_without_new_jobs[attempt_computation]

1 failed, 114 deselected in 3.48s

~~~~

[Original stderr.log](../../verification/runs/20261109T194429774545Z-trade-twins-ten-actual-original-source-cohort-identity-event-trial-and-late-authority-mutations/original-cost-identity/stderr.log)

~~~~text

~~~~

[Original stdout.log](../../verification/runs/20261109T194429774545Z-trade-twins-ten-actual-original-source-cohort-identity-event-trial-and-late-authority-mutations/original-cost-identity/stdout.log)

~~~~text
        elif fault=='wrong_account':r['portfolio']['capital']=99999.

        elif fault=='wrong_core':r['core_hash']='0'*64

        elif fault=='wrong_subject':r['numerical_contract']={}

        if fault.startswith('trace_') and fault!='trace_hash':t['trace_sha256']=identity({k:v for k,v in t.items() if k!='trace_sha256'})

>       with pytest.raises(ValueError):source_module.extract_report(r,job['payload'],CFG.model_dump())

             ^^^^^^^^^^^^^^^^^^^^^^^^^

E       Failed: DID NOT RAISE ValueError



tests\test_trade_twin_source.py:74: Failed

=========================== short test summary info ===========================

FAILED tests/test_trade_twin_source.py::test_report_local_corruptions_cannot_be_rehashed_into_valid_entry_authority[trace_costs]

1 failed, 114 deselected in 3.40s

~~~~

[Original stderr.log](../../verification/runs/20261109T194429774545Z-trade-twins-ten-actual-original-source-cohort-identity-event-trial-and-late-authority-mutations/original-entry-ledger/stderr.log)

~~~~text

~~~~

[Original stdout.log](../../verification/runs/20261109T194429774545Z-trade-twins-ten-actual-original-source-cohort-identity-event-trial-and-late-authority-mutations/original-entry-ledger/stdout.log)

~~~~text
        elif fault=='wrong_account':r['portfolio']['capital']=99999.

        elif fault=='wrong_core':r['core_hash']='0'*64

        elif fault=='wrong_subject':r['numerical_contract']={}

        if fault.startswith('trace_') and fault!='trace_hash':t['trace_sha256']=identity({k:v for k,v in t.items() if k!='trace_sha256'})

>       with pytest.raises(ValueError):source_module.extract_report(r,job['payload'],CFG.model_dump())

             ^^^^^^^^^^^^^^^^^^^^^^^^^

E       Failed: DID NOT RAISE ValueError



tests\test_trade_twin_source.py:74: Failed

=========================== short test summary info ===========================

FAILED tests/test_trade_twin_source.py::test_report_local_corruptions_cannot_be_rehashed_into_valid_entry_authority[trace_ledger]

1 failed, 114 deselected in 5.17s

~~~~

[Original stderr.log](../../verification/runs/20261109T194429774545Z-trade-twins-ten-actual-original-source-cohort-identity-event-trial-and-late-authority-mutations/original-event-loss/stderr.log)

~~~~text

~~~~

[Original stdout.log](../../verification/runs/20261109T194429774545Z-trade-twins-ten-actual-original-source-cohort-identity-event-trial-and-late-authority-mutations/original-event-loss/stdout.log)

~~~~text
        event='trial_computation_started' if kind=='single' else 'trial_checkpoint_saved'

        with lab.store.db() as db:db.execute('DELETE FROM events WHERE entity_id=? AND kind=?',(job['id'],event))

        before=database_fingerprint(lab)

>       with pytest.raises(StateError):source_module.read_saved_source(lab,job['id'])

             ^^^^^^^^^^^^^^^^^^^^^^^^^

E       Failed: DID NOT RAISE StateError



tests\test_trade_twin_source.py:265: Failed

=========================== short test summary info ===========================

FAILED tests/test_trade_twin_source.py::test_missing_original_trial_events_cannot_be_replaced_by_intact_current_rows[single]

FAILED tests/test_trade_twin_source.py::test_missing_original_trial_events_cannot_be_replaced_by_intact_current_rows[search]

2 failed, 113 deselected in 9.06s

~~~~

[Original stderr.log](../../verification/runs/20261109T194429774545Z-trade-twins-ten-actual-original-source-cohort-identity-event-trial-and-late-authority-mutations/original-signal-identity/stderr.log)

~~~~text

~~~~

[Original stdout.log](../../verification/runs/20261109T194429774545Z-trade-twins-ten-actual-original-source-cohort-identity-event-trial-and-late-authority-mutations/original-signal-identity/stdout.log)

~~~~text
        elif fault=='wrong_account':r['portfolio']['capital']=99999.

        elif fault=='wrong_core':r['core_hash']='0'*64

        elif fault=='wrong_subject':r['numerical_contract']={}

        if fault.startswith('trace_') and fault!='trace_hash':t['trace_sha256']=identity({k:v for k,v in t.items() if k!='trace_sha256'})

>       with pytest.raises(ValueError):source_module.extract_report(r,job['payload'],CFG.model_dump())

             ^^^^^^^^^^^^^^^^^^^^^^^^^

E       Failed: DID NOT RAISE ValueError



tests\test_trade_twin_source.py:74: Failed

=========================== short test summary info ===========================

FAILED tests/test_trade_twin_source.py::test_report_local_corruptions_cannot_be_rehashed_into_valid_entry_authority[trace_signal_hash]

1 failed, 114 deselected in 3.11s

~~~~

[Original stderr.log](../../verification/runs/20261109T194429774545Z-trade-twins-ten-actual-original-source-cohort-identity-event-trial-and-late-authority-mutations/original-trial-output/stderr.log)

~~~~text

~~~~

[Original stdout.log](../../verification/runs/20261109T194429774545Z-trade-twins-ten-actual-original-source-cohort-identity-event-trial-and-late-authority-mutations/original-trial-output/stdout.log)

~~~~text
                if fault=='trial_state':db.execute("UPDATE trial_plans SET state='computed' WHERE job_id=?",(jid,))

                if fault=='job_state':db.execute("UPDATE jobs SET status='failed' WHERE id=?",(jid,))

                if fault=='view_missing':db.execute("DELETE FROM events WHERE entity_id=? AND kind='result_view_saved'",(jid,))

        before=database_fingerprint(lab)

>       with pytest.raises((StateError,ValueError)):source_module.read_saved_source(lab,jid)

             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

E       Failed: DID NOT RAISE any of (StateError, ValueError)



tests\test_trade_twin_source.py:130: Failed

=========================== short test summary info ===========================

FAILED tests/test_trade_twin_source.py::test_original_storage_guard_faults_refuse_without_new_jobs[trial_computation]

1 failed, 114 deselected in 4.05s

~~~~

[Original stderr.log](../../verification/runs/20261109T194429774545Z-trade-twins-ten-actual-original-source-cohort-identity-event-trial-and-late-authority-mutations/whole-executed-cohort/stderr.log)

~~~~text

~~~~

[Original stdout.log](../../verification/runs/20261109T194429774545Z-trade-twins-ten-actual-original-source-cohort-identity-event-trial-and-late-authority-mutations/whole-executed-cohort/stdout.log)

~~~~text
        elif fault=='missing_payload':payload.pop('start')

        elif fault=='metric_bool':r['metrics']['net_profit']=False

        elif fault=='omitted_trade':r['trades']=[]

        if isinstance(r,dict):trace['trace_sha256']=identity({k:v for k,v in trace.items() if k!='trace_sha256'})

>       with pytest.raises(ValueError):source_module.extract_report(r,payload,CFG.model_dump())

             ^^^^^^^^^^^^^^^^^^^^^^^^^

E       Failed: DID NOT RAISE ValueError



tests\test_trade_twin_source.py:317: Failed

=========================== short test summary info ===========================

FAILED tests/test_trade_twin_source.py::test_strict_original_report_shape_and_typed_evidence_boundaries[omitted_trade]

1 failed, 114 deselected in 3.48s

~~~~

## 20261109T194937825191Z-trade-twins-ten-actual-source-authority-mutations-with-paired-price-manifest-replacement

[Original receipt](../../verification/receipts/20261109T194937825191Z-trade-twins-ten-actual-source-authority-mutations-with-paired-price-manifest-replacement.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T194937825191Z-trade-twins-ten-actual-source-authority-mutations-with-paired-price-manifest-replacement/stdout.log)

~~~~text
{"name": "baseline", "exit_code": 1, "elapsed_seconds": 13.06295210000826, "tests": 12, "failures": 1, "errors": 0, "skipped": 0}
~~~~

[Original stderr.log](../../verification/runs/20261109T194937825191Z-trade-twins-ten-actual-source-authority-mutations-with-paired-price-manifest-replacement/stderr.log)

~~~~text
Traceback (most recent call last):
  File "<workspace>\verification\runs\trade-twins-source-authority-mutations.py", line 35, in <module>
    exec(compile(code,'recorded-original-source-authority-mutation-harness','exec'))
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "recorded-original-source-authority-mutation-harness", line 38, in <module>
AssertionError
~~~~

[Original stderr.log](../../verification/runs/20261109T194937825191Z-trade-twins-ten-actual-source-authority-mutations-with-paired-price-manifest-replacement/baseline/stderr.log)

~~~~text

~~~~

[Original stdout.log](../../verification/runs/20261109T194937825191Z-trade-twins-ten-actual-source-authority-mutations-with-paired-price-manifest-replacement/baseline/stdout.log)

~~~~text
            p=lab.datasets_root/job['payload']['dataset_id']/'manifest.json';v=json.loads(p.read_text());v['metadata']['provider']='late change';p.write_text(json.dumps(v))

        elif fault=='manifest_and_price':

            folder=lab.datasets_root/job['payload']['dataset_id'];price=folder/'minutes.parquet'

            raw=bytearray(price.read_bytes());raw[-1]^=1;price.write_bytes(raw)

>           p=folder/'manifest.json';v=json.loads(p.read_text());v['parquet_sha256']=hashlib.sha256(raw).hexdigest();p.write_text(json.dumps(v))

                                                                                     ^^^^^^^

E           NameError: name 'hashlib' is not defined. Did you forget to import 'hashlib'?



tests\test_trade_twin_source.py:210: NameError

=========================== short test summary info ===========================

FAILED tests/test_trade_twin_source.py::test_late_original_changes_cannot_become_authorized_source[manifest_and_price]

1 failed, 11 passed, 104 deselected in 10.75s

~~~~

## 20261109T195837781741Z-trade-twins-financial-execution-authored-absence-assertion-before-kernel

[Original receipt](../../verification/receipts/20261109T195837781741Z-trade-twins-financial-execution-authored-absence-assertion-before-kernel.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T195837781741Z-trade-twins-financial-execution-authored-absence-assertion-before-kernel/stdout.log)

~~~~text
F                                                                        [100%]
================================== FAILURES ===================================
________________ test_financial_twin_execution_is_implemented _________________

    def test_financial_twin_execution_is_implemented():
>       assert importlib.util.find_spec('backend.lab.trade_twin_execution') is not None,'Financial twin execution has not been implemented.'
E       AssertionError: Financial twin execution has not been implemented.
E       assert None is not None
E        +  where None = <function find_spec at 0x000001E502FBF060>('backend.lab.trade_twin_execution')
E        +    where <function find_spec at 0x000001E502FBF060> = <module 'importlib.util' (frozen)>.find_spec
E        +      where <module 'importlib.util' (frozen)> = importlib.util

tests\test_trade_twin_execution.py:55: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_execution.py::test_financial_twin_execution_is_implemented
1 failed, 57 deselected in 0.35s
~~~~

[Original stderr.log](../../verification/runs/20261109T195837781741Z-trade-twins-financial-execution-authored-absence-assertion-before-kernel/stderr.log)

~~~~text

~~~~

## 20261109T200047466627Z-trade-twins-financial-kernel-first-independent-decimal-full-book-contracts

[Original receipt](../../verification/receipts/20261109T200047466627Z-trade-twins-financial-kernel-first-independent-decimal-full-book-contracts.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T200047466627Z-trade-twins-financial-kernel-first-independent-decimal-full-book-contracts/stdout.log)

~~~~text
                                                                                                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E                       TypeError: _execute.<locals>.ledger() got multiple values for argument 'amount'

backend\lab\trade_twin_execution.py:184: TypeError
============================== warnings summary ===============================
tests/test_trade_twin_execution.py::test_short_recall_retains_liquidation_and_failed_duration[False-barrier_capped_elapsed_v1]
tests/test_trade_twin_execution.py::test_short_recall_retains_liquidation_and_failed_duration[False-fixed_elapsed_v1]
tests/test_trade_twin_execution.py::test_short_recall_retains_liquidation_and_failed_duration[True-barrier_capped_elapsed_v1]
tests/test_trade_twin_execution.py::test_short_recall_retains_liquidation_and_failed_duration[True-fixed_elapsed_v1]
  <workspace>\.venv\Lib\site-packages\pydantic\main.py:520: UserWarning: Pydantic serializer warnings:
    PydanticSerializationUnexpectedValue(Expected `BorrowScenario` - serialized value may not be as expected [field_name='borrow_scenario', input_value={'name': 'authored recall...: 0.1, 'recall': True}]}, input_type=dict])
    return self.__pydantic_serializer__.to_python(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=============================== tests coverage ================================
_______________ coverage: platform win32, python 3.13.5-final-0 _______________

Coverage JSON written to file <workspace>\verification\runs\20261109T200047466627Z-trade-twins-financial-kernel-first-independent-decimal-full-book-contracts/financial-coverage.json
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_execution.py::test_split_fractional_shares_dividend_entitlement_and_unpaid_cash[False-1]
FAILED tests/test_trade_twin_execution.py::test_split_fractional_shares_dividend_entitlement_and_unpaid_cash[False--1]
FAILED tests/test_trade_twin_execution.py::test_split_fractional_shares_dividend_entitlement_and_unpaid_cash[True-1]
FAILED tests/test_trade_twin_execution.py::test_split_fractional_shares_dividend_entitlement_and_unpaid_cash[True--1]
4 failed, 54 passed, 4 warnings in 8.90s
~~~~

[Original stderr.log](../../verification/runs/20261109T200047466627Z-trade-twins-financial-kernel-first-independent-decimal-full-book-contracts/stderr.log)

~~~~text

~~~~

## 20261109T200235752667Z-trade-twins-financial-prior-volume-staleness-authored-counterexample

[Original receipt](../../verification/receipts/20261109T200235752667Z-trade-twins-financial-prior-volume-staleness-authored-counterexample.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T200235752667Z-trade-twins-financial-prior-volume-staleness-authored-counterexample/stdout.log)

~~~~text
F.                                                                       [100%]
================================== FAILURES ===================================
_ test_stale_or_missing_immediately_prior_completed_volume_cannot_fund_entry[True] _

drop_prior = True

    @pytest.mark.parametrize('drop_prior',[True,False])
    def test_stale_or_missing_immediately_prior_completed_volume_cannot_fund_entry(drop_prior):
        data=frame();match=match_for(data,start=3,end=5)
        if drop_prior:data=data.drop(index=2)
        else:data.loc[2,'timestamp']=data.loc[2,'timestamp']-pd.Timedelta(seconds=30)
        module=importlib.import_module('backend.lab.trade_twin_execution')
        if drop_prior:
            actual=module.execute_twin(data,match,CFG,ZERO,ACCOUNT)
>           assert actual['status']=='failed' and actual['failure']=='Original quantity exceeds prior-minute liquidity'
E           AssertionError: assert ('complete' == 'failed'
E             
E             - failed
E             + complete)

tests\test_trade_twin_execution.py:169: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_execution.py::test_stale_or_missing_immediately_prior_completed_volume_cannot_fund_entry[True]
1 failed, 1 passed, 58 deselected in 2.39s
~~~~

[Original stderr.log](../../verification/runs/20261109T200235752667Z-trade-twins-financial-prior-volume-staleness-authored-counterexample/stderr.log)

~~~~text

~~~~

## 20261109T200650493967Z-trade-twins-financial-full-field-original-artifacts-hand-fees-weekend-dividends-and-30-module-declaration

[Original receipt](../../verification/receipts/20261109T200650493967Z-trade-twins-financial-full-field-original-artifacts-hand-fees-weekend-dividends-and-30-module-declaration.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T200650493967Z-trade-twins-financial-full-field-original-artifacts-hand-fees-weekend-dividends-and-30-module-declaration/stdout.log)

~~~~text
        expected=numerator/Decimal(365*86400)
>       assert abs(result['trade']['borrow']-expected)<Decimal('1e-25')
E       AssertionError: assert Decimal('0.000003805175038051750380517432268') < Decimal('1E-25')
E        +  where Decimal('0.000003805175038051750380517432268') = abs((Decimal('1.2115677321156773211567732115677321156773211567732115677321156773211567732115677') - Decimal('1.211571537290715372907153729')))
E        +  and   Decimal('1E-25') = Decimal('1e-25')

tests\test_trade_twin_execution.py:335: AssertionError
___________ test_trade_twin_core_joins_the_unchanged_numerical_gate ___________

    def test_trade_twin_core_joins_the_unchanged_numerical_gate():
        from verification.check_numerical_coverage import MODULES
>       assert len(MODULES) == 30 and MODULES[-3:] == ['backend/lab/trade_twins.py', 'backend/lab/trade_twin_source.py', 'backend/lab/trade_twin_execution.py']
E       AssertionError: assert (29 == 30)
E        +  where 29 = len(['backend/lab/config.py', 'backend/lab/data.py', 'backend/lab/signals.py', 'backend/lab/engine.py', 'backend/lab/metrics.py', 'backend/lab/service.py', ...])

tests\test_trade_twins.py:325: AssertionError
=============================== tests coverage ================================
_______________ coverage: platform win32, python 3.13.5-final-0 _______________

Coverage JSON written to file <workspace>\verification\runs\20261109T200650493967Z-trade-twins-financial-full-field-original-artifacts-hand-fees-weekend-dividends-and-30-module-declaration/financial-coverage.json
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_execution.py::test_calendar_borrow_has_an_independent_hand_computed_weekend_total
FAILED tests/test_trade_twins.py::test_trade_twin_core_joins_the_unchanged_numerical_gate
2 failed, 273 passed in 48.93s
~~~~

[Original stderr.log](../../verification/runs/20261109T200650493967Z-trade-twins-financial-full-field-original-artifacts-hand-fees-weekend-dividends-and-30-module-declaration/stderr.log)

~~~~text

~~~~

## 20261109T200906145927Z-trade-twins-eleven-actual-financial-accounting-clock-barrier-funding-and-liquidity-mutations

[Original receipt](../../verification/receipts/20261109T200906145927Z-trade-twins-eleven-actual-financial-accounting-clock-barrier-funding-and-liquidity-mutations.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T200906145927Z-trade-twins-eleven-actual-financial-accounting-clock-barrier-funding-and-liquidity-mutations/stdout.log)

~~~~text
{"name": "baseline", "exit_code": 0, "elapsed_seconds": 6.440653800003929, "tests": 28, "failures": 0, "errors": 0, "skipped": 0}
{"name": "original-quantity", "exit_code": 1, "elapsed_seconds": 4.336424799985252, "tests": 8, "failures": 8, "errors": 0, "skipped": 0}
{"name": "sell-value-fee", "exit_code": 1, "elapsed_seconds": 3.777823199983686, "tests": 2, "failures": 2, "errors": 0, "skipped": 0}
{"name": "stop-first-ambiguity", "exit_code": 1, "elapsed_seconds": 4.165263299975777, "tests": 2, "failures": 2, "errors": 0, "skipped": 0}
{"name": "one-tick-through", "exit_code": 1, "elapsed_seconds": 4.156291199993575, "tests": 2, "failures": 2, "errors": 0, "skipped": 0}
{"name": "opening-cutoff-priority", "exit_code": 1, "elapsed_seconds": 4.56570889998693, "tests": 2, "failures": 2, "errors": 0, "skipped": 0}
{"name": "fixed-duration-barriers", "exit_code": 1, "elapsed_seconds": 3.503833199996734, "tests": 6, "failures": 6, "errors": 0, "skipped": 0}
{"name": "fractional-split-quantity", "exit_code": 1, "elapsed_seconds": 3.7281137999962084, "tests": 4, "failures": 4, "errors": 0, "skipped": 0}
~~~~

[Original stderr.log](../../verification/runs/20261109T200906145927Z-trade-twins-eleven-actual-financial-accounting-clock-barrier-funding-and-liquidity-mutations/stderr.log)

~~~~text
Traceback (most recent call last):
  File "<workspace>\verification\runs\trade-twins-financial-mutations.py", line 31, in <module>
    exec(compile(code,'recorded-financial-twin-mutation-harness','exec'))
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "recorded-financial-twin-mutation-harness", line 45, in <module>
AssertionError: ('fractional-split-quantity', [{'message': 'ArithmeticError: Twin cash and complete net profit do not reconcile.'}, {'message': 'ArithmeticError: Twin cash and complete net profit do not reconcile.'}, {'message': 'ArithmeticError: Twin cash and complete net profit do not reconcile.'}, {'message': 'ArithmeticError: Twin cash and complete net profit do not reconcile.'}])
~~~~

[Original stderr.log](../../verification/runs/20261109T200906145927Z-trade-twins-eleven-actual-financial-accounting-clock-barrier-funding-and-liquidity-mutations/baseline/stderr.log)

~~~~text

~~~~

[Original stdout.log](../../verification/runs/20261109T200906145927Z-trade-twins-eleven-actual-financial-accounting-clock-barrier-funding-and-liquidity-mutations/baseline/stdout.log)

~~~~text
............................                                             [100%]

28 passed, 126 deselected in 4.42s

~~~~

[Original stderr.log](../../verification/runs/20261109T200906145927Z-trade-twins-eleven-actual-financial-accounting-clock-barrier-funding-and-liquidity-mutations/fixed-duration-barriers/stderr.log)

~~~~text

~~~~

[Original stdout.log](../../verification/runs/20261109T200906145927Z-trade-twins-eleven-actual-financial-accounting-clock-barrier-funding-and-liquidity-mutations/fixed-duration-barriers/stdout.log)

~~~~text
E         - complete

E         + failed)



tests\test_trade_twin_execution.py:44: AssertionError

=========================== short test summary info ===========================

FAILED tests/test_trade_twin_execution.py::test_barrier_precedence_and_diagnostic_encounters[fixed_elapsed_v1-stop-1]

FAILED tests/test_trade_twin_execution.py::test_barrier_precedence_and_diagnostic_encounters[fixed_elapsed_v1-stop--1]

FAILED tests/test_trade_twin_execution.py::test_barrier_precedence_and_diagnostic_encounters[fixed_elapsed_v1-gap_stop-1]

FAILED tests/test_trade_twin_execution.py::test_barrier_precedence_and_diagnostic_encounters[fixed_elapsed_v1-gap_stop--1]

FAILED tests/test_trade_twin_execution.py::test_barrier_precedence_and_diagnostic_encounters[fixed_elapsed_v1-close_stop-1]

FAILED tests/test_trade_twin_execution.py::test_barrier_precedence_and_diagnostic_encounters[fixed_elapsed_v1-close_stop--1]

6 failed, 148 deselected in 1.82s

~~~~

[Original stderr.log](../../verification/runs/20261109T200906145927Z-trade-twins-eleven-actual-financial-accounting-clock-barrier-funding-and-liquidity-mutations/fractional-split-quantity/stderr.log)

~~~~text

~~~~

[Original stdout.log](../../verification/runs/20261109T200906145927Z-trade-twins-eleven-actual-financial-accounting-clock-barrier-funding-and-liquidity-mutations/fractional-split-quantity/stdout.log)

~~~~text
        outstanding=sum((r['amount'] for r in receivables),zero);profit=result['trade']['net_pnl'];residual=cash+outstanding-initial-profit

        if abs(residual)>D('0.0000001'):

>           raise ArithmeticError('Twin cash and complete net profit do not reconcile.')

E           ArithmeticError: Twin cash and complete net profit do not reconcile.



backend\lab\trade_twin_execution.py:232: ArithmeticError

=========================== short test summary info ===========================

FAILED tests/test_trade_twin_execution.py::test_split_fractional_shares_dividend_entitlement_and_unpaid_cash[False-1]

FAILED tests/test_trade_twin_execution.py::test_split_fractional_shares_dividend_entitlement_and_unpaid_cash[False--1]

FAILED tests/test_trade_twin_execution.py::test_split_fractional_shares_dividend_entitlement_and_unpaid_cash[True-1]

FAILED tests/test_trade_twin_execution.py::test_split_fractional_shares_dividend_entitlement_and_unpaid_cash[True--1]

4 failed, 150 deselected in 1.98s

~~~~

[Original stderr.log](../../verification/runs/20261109T200906145927Z-trade-twins-eleven-actual-financial-accounting-clock-barrier-funding-and-liquidity-mutations/one-tick-through/stderr.log)

~~~~text

~~~~

[Original stdout.log](../../verification/runs/20261109T200906145927Z-trade-twins-eleven-actual-financial-accounting-clock-barrier-funding-and-liquidity-mutations/one-tick-through/stdout.log)

~~~~text
E        +  and   <class 'str'> = type('2026-11-04T14:36:00+00:00')

E         

E         - 2026-11-04T14:36:00+00:00

E         ?                ^

E         + 2026-11-04T14:33:00+00:00

E         ?                ^)



tests\test_trade_twin_execution.py:44: AssertionError

=========================== short test summary info ===========================

FAILED tests/test_trade_twin_execution.py::test_barrier_precedence_and_diagnostic_encounters[barrier_capped_elapsed_v1-target_touch-1]

FAILED tests/test_trade_twin_execution.py::test_barrier_precedence_and_diagnostic_encounters[barrier_capped_elapsed_v1-target_touch--1]

2 failed, 152 deselected in 2.24s

~~~~

[Original stderr.log](../../verification/runs/20261109T200906145927Z-trade-twins-eleven-actual-financial-accounting-clock-barrier-funding-and-liquidity-mutations/opening-cutoff-priority/stderr.log)

~~~~text

~~~~

[Original stdout.log](../../verification/runs/20261109T200906145927Z-trade-twins-eleven-actual-financial-accounting-clock-barrier-funding-and-liquidity-mutations/opening-cutoff-priority/stdout.log)

~~~~text
E            +  where True = <built-in function isfinite>(Decimal('110.01'))

E            +    where <built-in function isfinite> = math.isfinite

E            +  and   Decimal('0.01') = abs((Decimal('110.01') - Decimal('110.00')))

E            +    where Decimal('110.01') = Decimal('110.01')

E            +      where '110.01' = str(Decimal('110.01'))

E            +  and   Decimal('1E-7') = Decimal('0.0000001')



tests\test_trade_twin_execution.py:43: AssertionError

=========================== short test summary info ===========================

FAILED tests/test_trade_twin_execution.py::test_opening_cutoff_precedes_new_opening_gap_barriers[barrier_capped_elapsed_v1-1]

FAILED tests/test_trade_twin_execution.py::test_opening_cutoff_precedes_new_opening_gap_barriers[barrier_capped_elapsed_v1--1]

2 failed, 152 deselected in 2.71s

~~~~

[Original stderr.log](../../verification/runs/20261109T200906145927Z-trade-twins-eleven-actual-financial-accounting-clock-barrier-funding-and-liquidity-mutations/original-quantity/stderr.log)

~~~~text

~~~~

[Original stdout.log](../../verification/runs/20261109T200906145927Z-trade-twins-eleven-actual-financial-accounting-clock-barrier-funding-and-liquidity-mutations/original-quantity/stdout.log)

~~~~text


tests\test_trade_twin_execution.py:43: AssertionError

=========================== short test summary info ===========================

FAILED tests/test_trade_twin_execution.py::test_hand_elapsed_accounts[barrier_capped_elapsed_v1-open-1]

FAILED tests/test_trade_twin_execution.py::test_hand_elapsed_accounts[barrier_capped_elapsed_v1-open--1]

FAILED tests/test_trade_twin_execution.py::test_hand_elapsed_accounts[barrier_capped_elapsed_v1-close-1]

FAILED tests/test_trade_twin_execution.py::test_hand_elapsed_accounts[barrier_capped_elapsed_v1-close--1]

FAILED tests/test_trade_twin_execution.py::test_hand_elapsed_accounts[fixed_elapsed_v1-open-1]

FAILED tests/test_trade_twin_execution.py::test_hand_elapsed_accounts[fixed_elapsed_v1-open--1]

FAILED tests/test_trade_twin_execution.py::test_hand_elapsed_accounts[fixed_elapsed_v1-close-1]

FAILED tests/test_trade_twin_execution.py::test_hand_elapsed_accounts[fixed_elapsed_v1-close--1]

8 failed, 146 deselected in 2.47s

~~~~

[Original stderr.log](../../verification/runs/20261109T200906145927Z-trade-twins-eleven-actual-financial-accounting-clock-barrier-funding-and-liquidity-mutations/sell-value-fee/stderr.log)

~~~~text

~~~~

[Original stdout.log](../../verification/runs/20261109T200906145927Z-trade-twins-eleven-actual-financial-accounting-clock-barrier-funding-and-liquidity-mutations/sell-value-fee/stdout.log)

~~~~text
E            +  where True = <built-in function isfinite>(Decimal('-11.600'))

E            +    where <built-in function isfinite> = math.isfinite

E            +  and   Decimal('0.099960') = abs((Decimal('-11.600') - Decimal('-11.699960')))

E            +    where Decimal('-11.600') = Decimal('-11.600')

E            +      where '-11.600' = str(Decimal('-11.600'))

E            +  and   Decimal('1E-7') = Decimal('0.0000001')



tests\test_trade_twin_execution.py:43: AssertionError

=========================== short test summary info ===========================

FAILED tests/test_trade_twin_execution.py::test_each_fee_has_a_hand_calculated_total_without_borrow[1]

FAILED tests/test_trade_twin_execution.py::test_each_fee_has_a_hand_calculated_total_without_borrow[-1]

2 failed, 152 deselected in 1.87s

~~~~

[Original stderr.log](../../verification/runs/20261109T200906145927Z-trade-twins-eleven-actual-financial-accounting-clock-barrier-funding-and-liquidity-mutations/stop-first-ambiguity/stderr.log)

~~~~text

~~~~

[Original stdout.log](../../verification/runs/20261109T200906145927Z-trade-twins-eleven-actual-financial-accounting-clock-barrier-funding-and-liquidity-mutations/stop-first-ambiguity/stdout.log)

~~~~text
E            +  where True = <built-in function isfinite>(Decimal('96.00'))

E            +    where <built-in function isfinite> = math.isfinite

E            +  and   Decimal('6.01') = abs((Decimal('96.00') - Decimal('102.01')))

E            +    where Decimal('96.00') = Decimal('96.00')

E            +      where '96.00' = str(Decimal('96.00'))

E            +  and   Decimal('1E-7') = Decimal('0.0000001')



tests\test_trade_twin_execution.py:43: AssertionError

=========================== short test summary info ===========================

FAILED tests/test_trade_twin_execution.py::test_barrier_precedence_and_diagnostic_encounters[barrier_capped_elapsed_v1-ambiguous-1]

FAILED tests/test_trade_twin_execution.py::test_barrier_precedence_and_diagnostic_encounters[barrier_capped_elapsed_v1-ambiguous--1]

2 failed, 152 deselected in 2.11s

~~~~

## 20261109T201009374946Z-trade-twins-current-complete-backend-regression-and-thirty-numerical-module-coverage

[Original receipt](../../verification/receipts/20261109T201009374946Z-trade-twins-current-complete-backend-regression-and-thirty-numerical-module-coverage.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T201009374946Z-trade-twins-current-complete-backend-regression-and-thirty-numerical-module-coverage/stdout.log)

~~~~text
ERROR tests/test_spread_faults.py::test_batch_parser_rejects_complete_and_partial_corrupt_records[early_end]
ERROR tests/test_spread_faults.py::test_batch_parser_rejects_complete_and_partial_corrupt_records[bad_family]
ERROR tests/test_spread_faults.py::test_batch_parser_rejects_complete_and_partial_corrupt_records[bad_ordinal]
ERROR tests/test_spread_faults.py::test_batch_parser_rejects_complete_and_partial_corrupt_records[bad_count]
ERROR tests/test_spread_faults.py::test_batch_parser_rejects_complete_and_partial_corrupt_records[missing_field]
ERROR tests/test_spread_faults.py::test_batch_parser_rejects_complete_and_partial_corrupt_records[incomplete_config]
ERROR tests/test_spread_faults.py::test_batch_parser_rejects_complete_and_partial_corrupt_records[wrong_config_family]
ERROR tests/test_spread_faults.py::test_batch_parser_rejects_complete_and_partial_corrupt_records[extra_batch]
ERROR tests/test_spread_faults.py::test_batch_parser_rejects_complete_and_partial_corrupt_records[bad_json]
ERROR tests/test_spread_faults.py::test_batch_parser_rejects_complete_and_partial_corrupt_records[bad_gzip]
ERROR tests/test_spread_faults.py::test_invalid_context_is_not_coerced_or_ignored[patch0]
ERROR tests/test_spread_faults.py::test_invalid_context_is_not_coerced_or_ignored[patch1]
ERROR tests/test_spread_faults.py::test_invalid_context_is_not_coerced_or_ignored[patch2]
ERROR tests/test_spread_faults.py::test_invalid_context_is_not_coerced_or_ignored[patch3]
ERROR tests/test_spread_faults.py::test_invalid_context_is_not_coerced_or_ignored[patch4]
ERROR tests/test_spread_faults.py::test_invalid_context_is_not_coerced_or_ignored[patch5]
ERROR tests/test_spread_faults.py::test_invalid_context_is_not_coerced_or_ignored[patch6]
ERROR tests/test_spread_faults.py::test_invalid_context_is_not_coerced_or_ignored[patch7]
ERROR tests/test_spread_faults.py::test_bad_probe_replay_never_computes_new_signals[not_structured]
ERROR tests/test_spread_faults.py::test_bad_probe_replay_never_computes_new_signals[not_started]
ERROR tests/test_spread_faults.py::test_bad_probe_replay_never_computes_new_signals[invalid_successor]
ERROR tests/test_spread_faults.py::test_bad_probe_replay_never_computes_new_signals[extra_suffix]
ERROR tests/test_spread_faults.py::test_failed_and_within_batch_duplicates_are_not_recomputed_or_counted_as_success
2564 passed, 4 warnings, 78 errors in 4338.52s (1:12:18)
~~~~

[Original stderr.log](../../verification/runs/20261109T201009374946Z-trade-twins-current-complete-backend-regression-and-thirty-numerical-module-coverage/stderr.log)

~~~~text

~~~~

## 20261109T202118194565Z-trade-twins-uninstalled-causal-setup-atr-feature-prototype-independent-asof-split-and-future-invariance

[Original receipt](../../verification/receipts/20261109T202118194565Z-trade-twins-uninstalled-causal-setup-atr-feature-prototype-independent-asof-split-and-future-invariance.json); command exit `2`.

[Original stdout.log](../../verification/runs/20261109T202118194565Z-trade-twins-uninstalled-causal-setup-atr-feature-prototype-independent-asof-split-and-future-invariance/stdout.log)

~~~~text

=================================== ERRORS ====================================
__ ERROR collecting verification/runs/test_trade_twin_features_prototype.py ___
ImportError while importing test module '<workspace>\verification\runs\test_trade_twin_features_prototype.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
<user-home>\AppData\Local\Programs\Python\Python313\Lib\importlib\__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\verification\runs\test_trade_twin_features_prototype.py:13: in <module>
    spec=importlib.util.spec_from_file_location('owned_candidate_prototype',path);prototype=importlib.util.module_from_spec(spec);spec.loader.exec_module(prototype)
                                                                                                                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\verification\runs\trade_twin_features_draft.py:13: in <module>
    from backend.lab.trade_twins import TwinMoment,MAX_CLOCK_MINUTES,MAX_MOMENTS
E   ModuleNotFoundError: No module named 'backend.lab.trade_twins'
=========================== short test summary info ===========================
ERROR ..\..\..\verification\runs\test_trade_twin_features_prototype.py
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 1.82s
~~~~

[Original stderr.log](../../verification/runs/20261109T202118194565Z-trade-twins-uninstalled-causal-setup-atr-feature-prototype-independent-asof-split-and-future-invariance/stderr.log)

~~~~text

~~~~

## 20261109T203636149747Z-trade-twins-uninstalled-exact-decimal-financial-grading-below-float-resolution-ties-and-complete-denominators

[Original receipt](../../verification/receipts/20261109T203636149747Z-trade-twins-uninstalled-exact-decimal-financial-grading-below-float-resolution-ties-and-complete-denominators.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T203636149747Z-trade-twins-uninstalled-exact-decimal-financial-grading-below-float-resolution-ties-and-complete-denominators/stdout.log)

~~~~text

plan = PreparedTwins(sources=(SourceTrade(trade_id='precision-boundary', symbol='SPY', side=1, entry_at='2026-11-04T14:45:00+...aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', plan_hash='5874f4c0417c286f7acd7fc05dcd5d8bd34c93b7c15fba02fa50df89c5715040')
seed = 42, policy = 'barrier_capped_elapsed_v1'
results = <generator object rows at 0x000002665C7D43D0>, cancel = None

    def summarize_financial(plan,seed,policy,results,cancel=None):
        _integer(seed,0,2**31-1,'Seed')
        if policy not in EXECUTION_POLICIES:raise ValueError('Choose a declared interpretation.')
        real=sum((Decimal(str(s.net_profit)) for s in plan.sources),Decimal(0))
        seen=bytearray(TOTAL_SETS);observed=complete=failed=exceedances=0
        for value in results:
            if cancel and cancel():raise InterruptedError('Exact financial grading canceled.')
            if not plan.eligible:raise ValueError('An ineligible original cohort cannot have financial outcomes.')
>           row=CanonicalOutcome.model_validate(value)
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           pydantic_core._pydantic_core.ValidationError: 1 validation error for CanonicalOutcome
E           net_profit
E             Value error, Financial total is not finite canonical Decimal text. [type=value_error, input_value='0.00000000000000000000000001', input_type=str]
E               For further information visit https://errors.pydantic.dev/2.14/v/value_error

..\..\..\verification\runs\trade_twin_decimal_grading_draft.py:32: ValidationError
=========================== short test summary info ===========================
FAILED ::test_exact_large_profit_comparison_keeps_sub_float_differences[0.00000000000000000000000001-0]
1 failed, 26 passed in 8.17s
~~~~

[Original stderr.log](../../verification/runs/20261109T203636149747Z-trade-twins-uninstalled-exact-decimal-financial-grading-below-float-resolution-ties-and-complete-denominators/stderr.log)

~~~~text

~~~~

## 20261109T203830004487Z-trade-twins-exact-grading-authored-default-decimal-context-cohort-sum-counterexample

[Original receipt](../../verification/receipts/20261109T203830004487Z-trade-twins-exact-grading-authored-default-decimal-context-cohort-sum-counterexample.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T203830004487Z-trade-twins-exact-grading-authored-default-decimal-context-cohort-sum-counterexample/stdout.log)

~~~~text
...........................F                                             [100%]
================================== FAILURES ===================================
_____ test_cohort_baseline_sum_does_not_depend_on_default_decimal_context _____

plan = PreparedTwins(sources=(SourceTrade(trade_id='precision-boundary', symbol='SPY', side=1, entry_at='2026-11-04T14:45:00+...aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', plan_hash='5874f4c0417c286f7acd7fc05dcd5d8bd34c93b7c15fba02fa50df89c5715040')

    def test_cohort_baseline_sum_does_not_depend_on_default_decimal_context(plan):
        second=plan.sources[0].model_copy(update=dict(trade_id='tiny-source',net_profit=1e-30))
>       exact=prepare_plan([*plan.sources,second],plan.moments,dict(plan.clock),plan.start,plan.end,plan.parent_identity)
                                                                    ^^^^^^^^^^
E       AttributeError: 'PreparedTwins' object has no attribute 'clock'. Did you mean: 'clocks'?

..\..\..\verification\runs\test_trade_twin_decimal_grading_prototype.py:72: AttributeError
=========================== short test summary info ===========================
FAILED ::test_cohort_baseline_sum_does_not_depend_on_default_decimal_context
1 failed, 27 passed in 6.60s
~~~~

[Original stderr.log](../../verification/runs/20261109T203830004487Z-trade-twins-exact-grading-authored-default-decimal-context-cohort-sum-counterexample/stderr.log)

~~~~text

~~~~

## 20261109T203916532173Z-trade-twins-exact-grading-corrected-authored-cohort-sum-precision-counterexample

[Original receipt](../../verification/receipts/20261109T203916532173Z-trade-twins-exact-grading-corrected-authored-cohort-sum-precision-counterexample.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T203916532173Z-trade-twins-exact-grading-corrected-authored-cohort-sum-precision-counterexample/stdout.log)

~~~~text
F                                                                        [100%]
================================== FAILURES ===================================
_____ test_cohort_baseline_sum_does_not_depend_on_default_decimal_context _____

plan = PreparedTwins(sources=(SourceTrade(trade_id='precision-boundary', symbol='SPY', side=1, entry_at='2026-11-04T14:45:00+...aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', plan_hash='5874f4c0417c286f7acd7fc05dcd5d8bd34c93b7c15fba02fa50df89c5715040')

    def test_cohort_baseline_sum_does_not_depend_on_default_decimal_context(plan):
        second=plan.sources[0].model_copy(update=dict(trade_id='tiny-source',net_profit=1e-30))
        exact=prepare_plan([*plan.sources,second],plan.moments,dict(plan.clocks),plan.start,plan.end,plan.parent_identity)
        result=grade.summarize_financial(exact,42,'barrier_capped_elapsed_v1',rows(exact,'10000000000.0'))
>       assert result['exceedances']==0 and result['adapted_pass'] is True
E       assert (10000 == 0)

..\..\..\verification\runs\test_trade_twin_decimal_grading_prototype.py:74: AssertionError
=========================== short test summary info ===========================
FAILED ::test_cohort_baseline_sum_does_not_depend_on_default_decimal_context
1 failed, 27 deselected in 4.99s
~~~~

[Original stderr.log](../../verification/runs/20261109T203916532173Z-trade-twins-exact-grading-corrected-authored-cohort-sum-precision-counterexample/stderr.log)

~~~~text

~~~~

## 20261109T211558078496Z-trade-twins-next-stage-production-component-absence-and-actual-original-profit-sum-red-contract

[Original receipt](../../verification/receipts/20261109T211558078496Z-trade-twins-next-stage-production-component-absence-and-actual-original-profit-sum-red-contract.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T211558078496Z-trade-twins-next-stage-production-component-absence-and-actual-original-profit-sum-red-contract/stdout.log)

~~~~text
        costs=Costs(commission_per_share=0,spread_bps=0,slippage_bps=0,borrow_annual=0)
        job=lab.create_experiment(Experiment(dataset_id=manifest['id'],start=day,end=day,strategy=cfg,costs=costs,portfolio=Portfolio(tick_size=1e-34)))
        assert Worker(lab).run_once() and lab.store.job(job['id'])['status']=='completed'
        report=lab.result(job['id'])['report'];assert len(report['trades'])==2
        amounts=[Fraction(str(t['net_pnl'])) for t in report['trades']]
        assert min(amounts)>0 and max(amounts)>10**10 and min(amounts)<Fraction('1e-20')
        fraction=sum(amounts,Fraction(0))
        with localcontext() as context:
            context.prec=1024
            expected=Decimal(fraction.numerator)/Decimal(fraction.denominator)
        original=read_saved_source(lab,job['id'])
        assert original['original_saved_store_authority_verified'] and len(original['sources'])==2
>       assert Decimal(original['source_profit'])==expected,'Original closed-profit sum lost the tiny executed trade.'
E       AssertionError: Original closed-profit sum lost the tiny executed trade.
E       assert Decimal('2499999975000.000000000000000') == Decimal('2499999975000.0000000000000000000000000000009999999999999405')
E        +  where Decimal('2499999975000.000000000000000') = Decimal('2499999975000.000000000000000')

tests\test_trade_twin_preparation.py:47: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_preparation.py::test_verified_preparation_components_are_installed_as_production_modules[trade_twin_features]
FAILED tests/test_trade_twin_preparation.py::test_verified_preparation_components_are_installed_as_production_modules[trade_twin_amounts]
FAILED tests/test_trade_twin_preparation.py::test_verified_preparation_components_are_installed_as_production_modules[trade_twin_results]
FAILED tests/test_trade_twin_preparation.py::test_actual_original_account_retains_tiny_profit_beside_large_trade
4 failed in 5.88s
~~~~

[Original stderr.log](../../verification/runs/20261109T211558078496Z-trade-twins-next-stage-production-component-absence-and-actual-original-profit-sum-red-contract/stderr.log)

~~~~text

~~~~

## 20261109T212324826313Z-trade-twins-next-features-authored-bounded-validation-cancel-and-final-return-contracts

[Original receipt](../../verification/receipts/20261109T212324826313Z-trade-twins-next-features-authored-bounded-validation-cancel-and-final-return-contracts.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T212324826313Z-trade-twins-next-features-authored-bounded-validation-cancel-and-final-return-contracts/stdout.log)

~~~~text
F.                                                                       [100%]
================================== FAILURES ===================================
________ test_cancellation_is_bounded_during_original_price_validation ________

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x000002666D0AF6F0>

    def test_cancellation_is_bounded_during_original_price_validation(monkeypatch):
        frame=rows();yielded=0;original=pd.DataFrame.itertuples
        def observed(self,*args,**kwargs):
            nonlocal yielded
            for row in original(self,*args,**kwargs):
                yielded+=1
                yield row
        monkeypatch.setattr(pd.DataFrame,'itertuples',observed)
        with pytest.raises(InterruptedError):prototype.candidate_features(frame,Strategy(timeframe='1m'),['SPY'],'2026-11-04','2026-11-04',lambda:yielded>=101)
>       assert yielded<=101,'Cancellation waited until after unbounded original-row validation.'
E       AssertionError: Cancellation waited until after unbounded original-row validation.
E       assert 781 <= 101

tests\test_trade_twin_features.py:157: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_features.py::test_cancellation_is_bounded_during_original_price_validation
1 failed, 1 passed, 48 deselected in 2.93s
~~~~

[Original stderr.log](../../verification/runs/20261109T212324826313Z-trade-twins-next-features-authored-bounded-validation-cancel-and-final-return-contracts/stderr.log)

~~~~text

~~~~

## 20261109T213226103308Z-trade-twins-baseline-2642-actual-case-lineage-and-unchanged-numerical-source-coverage-reconciliation

[Original receipt](../../verification/receipts/20261109T213226103308Z-trade-twins-baseline-2642-actual-case-lineage-and-unchanged-numerical-source-coverage-reconciliation.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T213226103308Z-trade-twins-baseline-2642-actual-case-lineage-and-unchanged-numerical-source-coverage-reconciliation/stdout.log)

~~~~text
  "original_receipt": "20261109T201009374946Z-trade-twins-current-complete-backend-regression-and-thirty-numerical-module-coverage",
  "followup_receipt": "20261109T212549227966Z-trade-twins-original-78-spread-case-followup-with-exact-current-source-isolation",
  "preimage_receipt": "20261109T212547601751Z-trade-twins-original-failed-spread-isolation-fixture-byte-preimage",
  "original_global_command_exit_code": 1,
  "single_all_green_invocation": false,
  "tests": {
    "tests": 2642,
    "passed": 2642,
    "unresolved": 0
  },
  "original_passing_bodies": 2564,
  "corrected_fixture_cases": 78,
  "source_files_verified": 220,
  "only_change": "tests/test_spread.py",
  "exact_guard_correction_verified": true,
  "original_fixture_sha256": "719f232c452e496367838091068830f64479ff5e6b734678cc6b431cd447e1d6",
  "current_fixture_sha256": "5de67b09c07d0f430bbf1581b353e1fc97d7712daeb61637fb73de9085161f6d",
  "fixture_bindings_verified": 50,
  "actual_coverage_db_sha256": "956d4a1b8d894c5325cb805838221869cff0ae7ea2fb2c55ef43716d2ff953eb",
  "actual_databases_reconcile_with_original_json": true,
  "all30_module_gate_pass": false,
  "final_single_all_green_invocation_still_required": true,
  "final_acceptance_certified": false
}
~~~~

[Original stderr.log](../../verification/runs/20261109T213226103308Z-trade-twins-baseline-2642-actual-case-lineage-and-unchanged-numerical-source-coverage-reconciliation/stderr.log)

~~~~text
Traceback (most recent call last):
  File "<workspace>\verification\runs\reconcile-trade-twins-baseline-regression.py", line 84, in <module>
    assert value['all30_module_gate_pass'],[m for m in modules if not m['gate_pass']]
           ~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: [{'module': 'backend/lab/spread_jobs.py', 'sha256': '32c043607696aca2e3e89c5801a534acfe02faa95d448e4b6749c3f965dddea9', 'statements': {'covered': 329, 'total': 334, 'required_percent': 95}, 'branches': {'covered': 194, 'total': 228, 'required_percent': 90}, 'exclusions': [], 'gate_pass': False}]
~~~~

## 20261109T214838099141Z-trade-twins-thirteen-actual-current-production-preparation-and-original-sum-mutations

[Original receipt](../../verification/receipts/20261109T214838099141Z-trade-twins-thirteen-actual-current-production-preparation-and-original-sum-mutations.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T214838099141Z-trade-twins-thirteen-actual-current-production-preparation-and-original-sum-mutations/stdout.log)

~~~~text

~~~~

[Original stderr.log](../../verification/runs/20261109T214838099141Z-trade-twins-thirteen-actual-current-production-preparation-and-original-sum-mutations/stderr.log)

~~~~text
Traceback (most recent call last):
  File "<workspace>\verification\runs\mutate-next-trade-twin-preparation.py", line 34, in <module>
    raw=(source/path).read_bytes();assert raw.count(needle.encode())==1,name;compile(raw.replace(needle.encode(),replacement.encode(),1),name,'exec')
                                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: source-validation-cancel
~~~~

## 20261109T220826879601Z-trade-twins-durable-original-reservation-authored-absence-contract

[Original receipt](../../verification/receipts/20261109T220826879601Z-trade-twins-durable-original-reservation-authored-absence-contract.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T220826879601Z-trade-twins-durable-original-reservation-authored-absence-contract/stdout.log)

~~~~text
F                                                                        [100%]
================================== FAILURES ===================================
_____________ test_durable_trade_twin_reservation_is_implemented ______________

    def test_durable_trade_twin_reservation_is_implemented():
>       assert importlib.util.find_spec('backend.lab.trade_twin_jobs') is not None, 'Original trade-twin reservation is not implemented.'
E       AssertionError: Original trade-twin reservation is not implemented.
E       assert None is not None
E        +  where None = <function find_spec at 0x000002799166F060>('backend.lab.trade_twin_jobs')
E        +    where <function find_spec at 0x000002799166F060> = <module 'importlib.util' (frozen)>.find_spec
E        +      where <module 'importlib.util' (frozen)> = importlib.util

tests\test_trade_twin_jobs.py:15: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_jobs.py::test_durable_trade_twin_reservation_is_implemented
1 failed in 1.38s
~~~~

[Original stderr.log](../../verification/runs/20261109T220826879601Z-trade-twins-durable-original-reservation-authored-absence-contract/stderr.log)

~~~~text

~~~~

## 20261109T220948795814Z-trade-twins-first-original-atomic-reservation-and-20001-frozen-occurrences

[Original receipt](../../verification/receipts/20261109T220948795814Z-trade-twins-first-original-atomic-reservation-and-20001-frozen-occurrences.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T220948795814Z-trade-twins-first-original-atomic-reservation-and-20001-frozen-occurrences/stdout.log)

~~~~text
                db.execute('INSERT INTO trade_twin_links VALUES(?,?,?)', (parent_id, part, child_id))
                store.event('trade_twins_frozen', parent_id, dict(child_id=child_id, **payload['twin_parent']), db)
                _cancel(cancel);db.execute('COMMIT')
            return store.job(child_id)
        except (StateError, InterruptedError):
            raise
        except (sqlite3.DatabaseError, KeyError, TypeError, ValueError) as error:
>           raise StateError('Original trade-twin reservation is missing, corrupt or incompatible; no replacement is authorized.') from error
E           backend.lab.store.StateError: Original trade-twin reservation is missing, corrupt or incompatible; no replacement is authorized.

backend\lab\trade_twin_jobs.py:152: StateError
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_jobs.py::test_original_reservation_freezes_both_complete_policies_before_candidate_work
FAILED tests/test_trade_twin_jobs.py::test_original_reservation_is_atomic_across_concurrent_and_canceled_requests
FAILED tests/test_trade_twin_jobs.py::test_damaged_original_reservations_refuse_replacement[link]
FAILED tests/test_trade_twin_jobs.py::test_damaged_original_reservations_refuse_replacement[event]
FAILED tests/test_trade_twin_jobs.py::test_damaged_original_reservations_refuse_replacement[child]
FAILED tests/test_trade_twin_jobs.py::test_damaged_original_reservations_refuse_replacement[inputs]
FAILED tests/test_trade_twin_jobs.py::test_damaged_original_reservations_refuse_replacement[plan]
FAILED tests/test_trade_twin_jobs.py::test_damaged_original_reservations_refuse_replacement[reverse_index]
FAILED tests/test_trade_twin_jobs.py::test_damaged_original_reservations_refuse_replacement[event_index]
FAILED tests/test_trade_twin_jobs.py::test_damaged_original_reservations_refuse_replacement[event_details]
FAILED tests/test_trade_twin_jobs.py::test_damaged_original_reservations_refuse_replacement[child_payload]
11 failed, 10 passed in 130.18s (0:02:10)
~~~~

[Original stderr.log](../../verification/runs/20261109T220948795814Z-trade-twins-first-original-atomic-reservation-and-20001-frozen-occurrences/stderr.log)

~~~~text

~~~~

## 20261109T221411064643Z-trade-twins-authored-late-parent-and-protected-scope-revalidation-counterexamples

[Original receipt](../../verification/receipts/20261109T221411064643Z-trade-twins-authored-late-parent-and-protected-scope-revalidation-counterexamples.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T221411064643Z-trade-twins-authored-late-parent-and-protected-scope-revalidation-counterexamples/stdout.log)

~~~~text
        scopes = lab.guard.protected_scopes
        state = {'changed': False}
        def protected(db):
            yield from scopes(db)
            if state['changed'] and change == 'protected_scope':
                yield {'id': 'late', 'status': 'registered'}, dict(symbols=['SPY'], holdout={'start': parent['payload']['start'], 'end': parent['payload']['end']})
        def late(*args, **kwargs):
            result = reader(*args, **kwargs)
            if change == 'parent_status':
                with lab.store.db() as db:
                    db.execute("UPDATE jobs SET status='failed' WHERE id=?", (parent['id'],))
            state['changed'] = True
            return result
        monkeypatch.setattr(lab.guard, 'protected_scopes', protected)
        monkeypatch.setattr(jobs, 'read_saved_source', late)
>       with pytest.raises((StateError, ResearchError)):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE any of (StateError, ResearchError)

tests\test_trade_twin_jobs.py:150: Failed
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_jobs.py::test_revalidation_rechecks_late_parent_state_and_protected_scope[parent_status]
FAILED tests/test_trade_twin_jobs.py::test_revalidation_rechecks_late_parent_state_and_protected_scope[protected_scope]
2 failed in 6.80s
~~~~

[Original stderr.log](../../verification/runs/20261109T221411064643Z-trade-twins-authored-late-parent-and-protected-scope-revalidation-counterexamples/stderr.log)

~~~~text

~~~~

## 20261109T221453097324Z-trade-twins-original-reservation-and-revalidation-late-state-scope-and-all-links

[Original receipt](../../verification/receipts/20261109T221453097324Z-trade-twins-original-reservation-and-revalidation-late-state-scope-and-all-links.json); command exit `4`.

[Original stdout.log](../../verification/runs/20261109T221453097324Z-trade-twins-original-reservation-and-revalidation-late-state-scope-and-all-links/stdout.log)

~~~~text

no tests ran in 0.39s
~~~~

[Original stderr.log](../../verification/runs/20261109T221453097324Z-trade-twins-original-reservation-and-revalidation-late-state-scope-and-all-links/stderr.log)

~~~~text
ERROR: file or directory not found: tests/test_research.py

~~~~

## 20261109T222930510042Z-trade-twins-owned-durable-preparation-authored-absence-contract

[Original receipt](../../verification/receipts/20261109T222930510042Z-trade-twins-owned-durable-preparation-authored-absence-contract.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T222930510042Z-trade-twins-owned-durable-preparation-authored-absence-contract/stdout.log)

~~~~text
F                                                                        [100%]
================================== FAILURES ===================================
______________ test_owned_trade_twin_preparation_is_implemented _______________

    def test_owned_trade_twin_preparation_is_implemented():
>       assert importlib.util.find_spec('backend.lab.trade_twin_preparation') is not None, 'Durable original trade-twin preparation is not implemented.'
E       AssertionError: Durable original trade-twin preparation is not implemented.
E       assert None is not None
E        +  where None = <function find_spec at 0x00000227A88EF060>('backend.lab.trade_twin_preparation')
E        +    where <function find_spec at 0x00000227A88EF060> = <module 'importlib.util' (frozen)>.find_spec
E        +      where <module 'importlib.util' (frozen)> = importlib.util

tests\test_trade_twin_durable_preparation.py:12: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_durable_preparation.py::test_owned_trade_twin_preparation_is_implemented
1 failed in 2.10s
~~~~

[Original stderr.log](../../verification/runs/20261109T222930510042Z-trade-twins-owned-durable-preparation-authored-absence-contract/stderr.log)

~~~~text

~~~~

## 20261109T223312917680Z-trade-twins-authored-real-corporate-action-and-closing-original-authority-preparation-counterexamples

[Original receipt](../../verification/receipts/20261109T223312917680Z-trade-twins-authored-real-corporate-action-and-closing-original-authority-preparation-counterexamples.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T223312917680Z-trade-twins-authored-real-corporate-action-and-closing-original-authority-preparation-counterexamples/stdout.log)

~~~~text
preparation = <module 'backend.lab.trade_twin_preparation' from '<workspace>\\data\\dev026\\next-src\\backend\\lab\\trade_twin_preparation.py'>
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x00000210B71AB820>

    def test_closing_original_authority_failure_preserves_uncommitted_attempt_and_never_seals(original, preparation, monkeypatch):
        lab, parent, _ = original
        child = jobs.create(lab, parent['id']);owner = 'closing-failure'
        claimed = claim(lab, child, owner)
        verify = preparation.verify_child
        calls = []
        def changed(*args, **kwargs):
            calls.append(True)
            if len(calls) > 1:
                raise StateError('Injected closing original authority failure.')
            return verify(*args, **kwargs)
        monkeypatch.setattr(preparation, 'verify_child', changed)
>       with pytest.raises(StateError, match='closing original'):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE StateError

tests\test_trade_twin_durable_preparation.py:128: Failed
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_durable_preparation.py::test_real_original_corporate_actions_are_bound_to_preparation
FAILED tests/test_trade_twin_durable_preparation.py::test_closing_original_authority_failure_preserves_uncommitted_attempt_and_never_seals
2 failed in 11.26s
~~~~

[Original stderr.log](../../verification/runs/20261109T223312917680Z-trade-twins-authored-real-corporate-action-and-closing-original-authority-preparation-counterexamples/stderr.log)

~~~~text

~~~~

## 20261109T224803451606Z-trade-twins-six-actual-owned-preparation-source-cohort-actions-plan-authority-and-atomic-seal-mutations

[Original receipt](../../verification/receipts/20261109T224803451606Z-trade-twins-six-actual-owned-preparation-source-cohort-actions-plan-authority-and-atomic-seal-mutations.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T224803451606Z-trade-twins-six-actual-owned-preparation-source-cohort-actions-plan-authority-and-atomic-seal-mutations/stdout.log)

~~~~text
{"name": "missing-original-seal-repair", "assertion_killed": true, "counts": {"tests": 1, "failures": 1, "errors": 0, "skipped": 0}}
{"name": "drop-original-cohort", "assertion_killed": true, "counts": {"tests": 1, "failures": 1, "errors": 0, "skipped": 0}}
{"name": "ignore-authoritative-actions", "assertion_killed": true, "counts": {"tests": 1, "failures": 1, "errors": 0, "skipped": 0}}
~~~~

[Original stderr.log](../../verification/runs/20261109T224803451606Z-trade-twins-six-actual-owned-preparation-source-cohort-actions-plan-authority-and-atomic-seal-mutations/stderr.log)

~~~~text
  File "<user-home>\AppData\Local\Programs\Python\Python313\Lib\subprocess.py", line 554, in run
    with Popen(*popenargs, **kwargs) as process:
         ~~~~~^^^^^^^^^^^^^^^^^^^^^^
  File "<user-home>\AppData\Local\Programs\Python\Python313\Lib\subprocess.py", line 1039, in __init__
    self._execute_child(args, executable, preexec_fn, close_fds,
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                        pass_fds, cwd, env,
                        ^^^^^^^^^^^^^^^^^^^
    ...<5 lines>...
                        gid, gids, uid, umask,
                        ^^^^^^^^^^^^^^^^^^^^^^
                        start_new_session, process_group)
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<user-home>\AppData\Local\Programs\Python\Python313\Lib\subprocess.py", line 1554, in _execute_child
    hp, ht, pid, tid = _winapi.CreateProcess(executable, args,
                       ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^
                             # no special security
                             ^^^^^^^^^^^^^^^^^^^^^
    ...<4 lines>...
                             cwd,
                             ^^^^
                             startupinfo)
                             ^^^^^^^^^^^^
NotADirectoryError: [WinError 267] The directory name is invalid
~~~~

## 20261109T230348013448Z-trade-twins-paired-financial-parts-authored-missing-implementation-contract

[Original receipt](../../verification/receipts/20261109T230348013448Z-trade-twins-paired-financial-parts-authored-missing-implementation-contract.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T230348013448Z-trade-twins-paired-financial-parts-authored-missing-implementation-contract/stdout.log)

~~~~text
F                                                                        [100%]
================================== FAILURES ===================================
____________ test_original_paired_financial_parts_are_implemented _____________

    def test_original_paired_financial_parts_are_implemented():
>       assert importlib.util.find_spec('backend.lab.trade_twin_parts') is not None, 'Original paired financial parts are not implemented.'
E       AssertionError: Original paired financial parts are not implemented.
E       assert None is not None
E        +  where None = <function find_spec at 0x000001698CCAF060>('backend.lab.trade_twin_parts')
E        +    where <function find_spec at 0x000001698CCAF060> = <module 'importlib.util' (frozen)>.find_spec
E        +      where <module 'importlib.util' (frozen)> = importlib.util

tests\test_trade_twin_parts.py:14: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_parts.py::test_original_paired_financial_parts_are_implemented
1 failed in 1.92s
~~~~

[Original stderr.log](../../verification/runs/20261109T230348013448Z-trade-twins-paired-financial-parts-authored-missing-implementation-contract/stderr.log)

~~~~text

~~~~

## 20261109T232017136670Z-trade-twins-complete-owned-worker-authored-missing-dispatch-contract

[Original receipt](../../verification/receipts/20261109T232017136670Z-trade-twins-complete-owned-worker-authored-missing-dispatch-contract.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T232017136670Z-trade-twins-complete-owned-worker-authored-missing-dispatch-contract/stdout.log)

~~~~text
F                                                                        [100%]
================================== FAILURES ===================================
____________ test_complete_paired_trade_twin_worker_is_implemented ____________

    def test_complete_paired_trade_twin_worker_is_implemented():
>       assert importlib.util.find_spec('backend.lab.trade_twin_worker') is not None, 'Complete original trade-twin worker is not implemented.'
E       AssertionError: Complete original trade-twin worker is not implemented.
E       assert None is not None
E        +  where None = <function find_spec at 0x0000024CF324F060>('backend.lab.trade_twin_worker')
E        +    where <function find_spec at 0x0000024CF324F060> = <module 'importlib.util' (frozen)>.find_spec
E        +      where <module 'importlib.util' (frozen)> = importlib.util

tests\test_trade_twin_worker.py:13: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_worker.py::test_complete_paired_trade_twin_worker_is_implemented
1 failed in 2.10s
~~~~

[Original stderr.log](../../verification/runs/20261109T232017136670Z-trade-twins-complete-owned-worker-authored-missing-dispatch-contract/stderr.log)

~~~~text

~~~~

## 20261109T233216663791Z-trade-twins-authored-bounded-original-book-validation-and-midunit-authority-counterexamples

[Original receipt](../../verification/receipts/20261109T233216663791Z-trade-twins-authored-bounded-original-book-validation-and-midunit-authority-counterexamples.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T233216663791Z-trade-twins-authored-bounded-original-book-validation-and-midunit-authority-counterexamples/stdout.log)

~~~~text
            result=entry(*args,**kwargs)
            if result is not None and not changed:
                changed.append(True)
                with lab.store.db() as db:
                    event=db.execute("SELECT id,details FROM events WHERE entity_id=? AND kind='twin_part_committed'",(job['id'],)).fetchone()
                    if damage=='original_event_identity':
                        new_id=db.execute('SELECT MAX(id)+100 FROM events').fetchone()[0]
                        db.execute('UPDATE events SET id=? WHERE id=?',(new_id,event['id']))
                        db.execute('UPDATE trade_twin_part_index SET event_id=? WHERE job_id=? AND part=0',(new_id,job['id']))
                    else:
                        import json
                        path=journal.folder/json.loads(event['details'])['filename']
                        path.write_bytes(path.read_bytes()+b'changed during verified cache use')
            return result
        monkeypatch.setattr(journal,'_entry',altered)
>       with pytest.raises(StateError):journal.execute(1)
             ^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE StateError

tests\test_trade_twin_parts.py:251: Failed
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_parts.py::test_one_unit_bounds_repeated_full_original_part_validation_without_omitting_book_checks
FAILED tests/test_trade_twin_parts.py::test_origin_authority_cannot_change_during_a_unit_even_when_book_bytes_are_cached[original_event_identity]
2 failed, 1 passed in 39.02s
~~~~

[Original stderr.log](../../verification/runs/20261109T233216663791Z-trade-twins-authored-bounded-original-book-validation-and-midunit-authority-counterexamples/stderr.log)

~~~~text

~~~~

## 20261109T235306560862Z-trade-twins-identical-original-and-random-cashflow-strict-baseline-precision-counterexamples

[Original receipt](../../verification/receipts/20261109T235306560862Z-trade-twins-identical-original-and-random-cashflow-strict-baseline-precision-counterexamples.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261109T235306560862Z-trade-twins-identical-original-and-random-cashflow-strict-baseline-precision-counterexamples/stdout.log)

~~~~text
        manifest=save_dataset(lab.datasets_root,frame,dict(input_kind='synthetic',provider='exact source-baseline counterexample',corporate_actions_complete=True))
        regular=prepare_data(normalize(frame)[0]);signal=sig(regular,at=20)
        monkeypatch.setattr(service,'generate_signals',lambda *a,**k:[signal])
        parent=lab.create_experiment(Experiment(dataset_id=manifest['id'],start='2026-11-04',end='2026-11-04',strategy=CFG,costs=ZERO,portfolio=ACCOUNT))
        assert Worker(lab).run_once() and lab.store.job(parent['id'])['status']=='completed'
        original=read_saved_source(lab,parent['id'])
        child=create(lab,parent['id']);owner='baseline-proof';job=lab.store.claim(owner)
        prepared=prepare(lab,job,owner);draw=draw_set(prepared['plan'],job['payload']['seed'],0)
        book=execute_twin(prepared['regular'],draw['matches'][0],job['payload']['strategy'],job['payload']['costs'],job['payload']['portfolio'],prepared['actions'])
        assert book['status']=='complete'
        real=lab.report(parent['id'])['trades'][0]
        assert Decimal(str(real['entry_price']))==book['trade']['entry_price']
        assert Decimal(str(real['exit_price']))==book['trade']['exit_price']
        assert Decimal(str(real['entry_quantity']))==book['trade']['entry_quantity']
>       assert Decimal(original['source_profit'])==book['net_profit'], 'Identical filled prices/quantity/costs must tie under the exact grading contract.'
E       AssertionError: Identical filled prices/quantity/costs must tie under the exact grading contract.
E       assert Decimal('4.8999999999997215') == Decimal('4.900')
E        +  where Decimal('4.8999999999997215') = Decimal('4.8999999999997215')

tests\test_trade_twin_baseline_precision.py:38: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_baseline_precision.py::test_original_and_twin_identical_filled_cashflows_have_the_same_exact_baseline[99.9]
FAILED tests/test_trade_twin_baseline_precision.py::test_original_and_twin_identical_filled_cashflows_have_the_same_exact_baseline[100.1]
2 failed in 9.61s
~~~~

[Original stderr.log](../../verification/runs/20261109T235306560862Z-trade-twins-identical-original-and-random-cashflow-strict-baseline-precision-counterexamples/stderr.log)

~~~~text

~~~~

## 20261110T000510462732Z-source-cashflow-auditor-authored-absence-before-canonical-baseline-implementation

[Original receipt](../../verification/receipts/20261110T000510462732Z-source-cashflow-auditor-authored-absence-before-canonical-baseline-implementation.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261110T000510462732Z-source-cashflow-auditor-authored-absence-before-canonical-baseline-implementation/stdout.log)

~~~~text
F                                                                        [100%]
================================== FAILURES ===================================
____________ test_original_source_cashflow_auditor_is_implemented _____________

    def test_original_source_cashflow_auditor_is_implemented():
>       assert importlib.util.find_spec('backend.lab.source_cashflows') is not None, 'Canonical original executed-cashflow audit is not implemented.'
E       AssertionError: Canonical original executed-cashflow audit is not implemented.
E       assert None is not None
E        +  where None = <function find_spec at 0x0000028565E9F060>('backend.lab.source_cashflows')
E        +    where <function find_spec at 0x0000028565E9F060> = <module 'importlib.util' (frozen)>.find_spec
E        +      where <module 'importlib.util' (frozen)> = importlib.util

tests\test_source_cashflows.py:9: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_source_cashflows.py::test_original_source_cashflow_auditor_is_implemented
1 failed in 0.41s
~~~~

[Original stderr.log](../../verification/runs/20261110T000510462732Z-source-cashflow-auditor-authored-absence-before-canonical-baseline-implementation/stderr.log)

~~~~text

~~~~

## 20261110T001231583982Z-source-cashflows-first-canonical-original-audit-and-identical-financial-ties

[Original receipt](../../verification/receipts/20261110T001231583982Z-source-cashflows-first-canonical-original-audit-and-identical-financial-ties.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261110T001231583982Z-source-cashflows-first-canonical-original-audit-and-identical-financial-ties/stdout.log)

~~~~text
            current_manifest=read_manifest(lab.datasets_root,payload['dataset_id'])
            if identity(current_manifest)!=payload['dataset_manifest_hash']:
                raise StateError('Original source manifest changed during extraction.')
            lab.guard.access(symbols,warmup,payload['end'],'trade_twin_source',record=False)
            if file_hash(lab.datasets_root/payload['dataset_id']/'minutes.parquet')!=current_manifest['parquet_sha256']:
                raise StateError('Original price bytes changed during extraction.')
            lab.borrow_input(payload['dataset_id'],Costs(**payload['costs']),payload['start'],payload['end'],symbols=symbols)
            lab.news_input(payload,[cfg],payload['start'],payload['end'])
            _cancel(cancel);require_current_source()
            if job['kind']=='spread_accounts':verify_child(lab,job,cancel)
            return result|dict(job_id=jid,part=part,authority=binding,authority_hash=identity(binding),
                original_saved_store_authority_verified=True,assumptions=dict(configuration=configuration,costs=payload['costs'],portfolio=payload['portfolio'],
                dataset_id=payload['dataset_id'],dataset_manifest_hash=payload['dataset_manifest_hash'],start=payload['start'],end=payload['end'],seed=payload['seed']))
        except (StateError,InterruptedError):raise
        except (OSError,ValueError,TypeError,KeyError,OverflowError) as error:
>           raise StateError('Original account authority is missing, corrupt or incompatible; no source was authorized.') from error
E           backend.lab.store.StateError: Original account authority is missing, corrupt or incompatible; no source was authorized.

backend\lab\trade_twin_source.py:287: StateError
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_baseline_precision.py::test_original_and_twin_identical_filled_cashflows_have_the_same_exact_baseline[99.9]
FAILED tests/test_trade_twin_baseline_precision.py::test_original_and_twin_identical_filled_cashflows_have_the_same_exact_baseline[100.1]
FAILED tests/test_trade_twin_preparation.py::test_actual_original_account_retains_tiny_profit_beside_large_trade
3 failed, 8 passed in 5.47s
~~~~

[Original stderr.log](../../verification/runs/20261110T001231583982Z-source-cashflows-first-canonical-original-audit-and-identical-financial-ties/stderr.log)

~~~~text

~~~~

## 20261110T001925270510Z-current-owned-worker-10000-paired-financial-sets-original-checkpoints-independent-books-and-resources

[Original receipt](../../verification/receipts/20261110T001925270510Z-current-owned-worker-10000-paired-financial-sets-original-checkpoints-independent-books-and-resources.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261110T001925270510Z-current-owned-worker-10000-paired-financial-sets-original-checkpoints-independent-books-and-resources/stdout.log)

~~~~text

~~~~

[Original stderr.log](../../verification/runs/20261110T001925270510Z-current-owned-worker-10000-paired-financial-sets-original-checkpoints-independent-books-and-resources/stderr.log)

~~~~text
Traceback (most recent call last):
  File "<workspace>\verification\runs\check-current-owned-twins-10000.py", line 123, in <module>
    assert states.get('checkpointed')==20001,states
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: {'completed': 20001}
~~~~

## 20261110T002256806219Z-trade-twins-authored-api-route-absence-and-source-assumption-boundary

[Original receipt](../../verification/receipts/20261110T002256806219Z-trade-twins-authored-api-route-absence-and-source-assumption-boundary.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261110T002256806219Z-trade-twins-authored-api-route-absence-and-source-assumption-boundary/stdout.log)

~~~~text
F                                                                        [100%]
================================== FAILURES ===================================
______________ test_trade_twin_continuation_route_is_implemented ______________

original = (<starlette.testclient.TestClient object at 0x0000019DC9FA27B0>, <backend.lab.service.Lab object at 0x0000019DC9E8C2F0...ind': 'synthetic', 'policy_version': 1, ...}, 'dataset_id': '672ddbd98f1332e74dacf449', ...}, 'status': 'queued', ...})

    def test_trade_twin_continuation_route_is_implemented(original):
        client,lab,parent=original
        response=client.post('/api/jobs/'+parent['id']+'/trade-twins',json={'part':0})
>       assert response.status_code==202,response.text
E       AssertionError: {"detail":"Not Found"}
E       assert 404 == 202
E        +  where 404 = <Response [404 Not Found]>.status_code

tests\test_trade_twin_api.py:26: AssertionError
============================== warnings summary ===============================
..\..\..\.venv\Lib\site-packages\fastapi\testclient.py:1
  <workspace>\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_api.py::test_trade_twin_continuation_route_is_implemented
1 failed, 1 warning in 9.75s
~~~~

[Original stderr.log](../../verification/runs/20261110T002256806219Z-trade-twins-authored-api-route-absence-and-source-assumption-boundary/stderr.log)

~~~~text

~~~~

## 20261110T003025012143Z-trade-twins-real-browser-source-continuation-cancel-resume-reopen-and-mobile-empty-cohort

[Original receipt](../../verification/receipts/20261110T003025012143Z-trade-twins-real-browser-source-continuation-cancel-resume-reopen-and-mobile-empty-cohort.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261110T003025012143Z-trade-twins-real-browser-source-continuation-cancel-resume-reopen-and-mobile-empty-cohort/stdout.log)

~~~~text
Error: Cannot find module '@playwright/test'
Require stack:
- <workspace>\verification\runs\trade-twin-browser-tests\flow.spec.ts
- <workspace>\frontend\node_modules\playwright\lib\common\index.js
- <workspace>\frontend\node_modules\playwright\lib\program.js
- <workspace>\frontend\node_modules\@playwright\test\cli.js

   at flow.spec.ts:1

> 1 | import {test,expect} from '@playwright/test';
    | ^
  2 | import {writeFile} from 'node:fs/promises';
  3 |
  4 | test('original saved account queues cancels resumes and reopens its actual ineligible comparison',async({page},info)=>{
    at Object.<anonymous> (<workspace>\verification\runs\trade-twin-browser-tests\flow.spec.ts:1:1)
Error: No tests found

{"review_output": "verification/runs/20261110T003025012143Z-trade-twins-real-browser-source-continuation-cancel-resume-reopen-and-mobile-empty-cohort/browser", "child_exit_code": 1, "privacy_policy": 1, "raw_capture_id": "6e530828760d4df2812eb04eae841a7c"}
~~~~

[Original stderr.log](../../verification/runs/20261110T003025012143Z-trade-twins-real-browser-source-continuation-cancel-resume-reopen-and-mobile-empty-cohort/stderr.log)

~~~~text

~~~~

## 20261110T003044742139Z-trade-twins-real-browser-explicit-locked-runner-cancel-resume-reopen-and-mobile-empty-cohort

[Original receipt](../../verification/receipts/20261110T003044742139Z-trade-twins-real-browser-explicit-locked-runner-cancel-resume-reopen-and-mobile-empty-cohort.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261110T003044742139Z-trade-twins-real-browser-explicit-locked-runner-cancel-resume-reopen-and-mobile-empty-cohort/stdout.log)

~~~~text

~~~~

[Original stderr.log](../../verification/runs/20261110T003044742139Z-trade-twins-real-browser-explicit-locked-runner-cancel-resume-reopen-and-mobile-empty-cohort/stderr.log)

~~~~text
Traceback (most recent call last):
  File "<workspace>\verification\runs\run-current-trade-twin-browser.py", line 62, in <module>
    if __name__=='__main__':raise SystemExit(main())
                                             ~~~~^^
  File "<workspace>\verification\runs\run-current-trade-twin-browser.py", line 50, in main
    exitcode=browser_run(['exec','--','playwright','test','--config=../verification/runs/trade-twin-browser.config.ts'])
  File "<workspace>\verification\frontend_check.py", line 43, in browser_run
    print((review/'runner-stdout.log').read_text(encoding='utf-8'),end='')
    ~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<user-home>\AppData\Local\Programs\Python\Python313\Lib\encodings\cp1252.py", line 19, in encode
    return codecs.charmap_encode(input,self.errors,encoding_table)[0]
           ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'charmap' codec can't encode characters in position 1833-1890: character maps to <undefined>
~~~~

## 20261110T003215314961Z-original-cashflow-and-grading-eight-actual-mutations-with-green-assertion-baseline

[Original receipt](../../verification/receipts/20261110T003215314961Z-original-cashflow-and-grading-eight-actual-mutations-with-green-assertion-baseline.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261110T003215314961Z-original-cashflow-and-grading-eight-actual-mutations-with-green-assertion-baseline/stdout.log)

~~~~text

~~~~

[Original stderr.log](../../verification/runs/20261110T003215314961Z-original-cashflow-and-grading-eight-actual-mutations-with-green-assertion-baseline/stderr.log)

~~~~text
Traceback (most recent call last):
  File "<workspace>\verification\runs\mutate-original-cashflow-baseline.py", line 37, in <module>
    if name=='baseline':assert result.returncode==0 and counts['failures']==counts['errors']==counts['skipped']==0,counts
                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: {'tests': 1, 'failures': 0, 'errors': 1, 'skipped': 0}
~~~~

## 20261110T003249342972Z-original-cashflow-eight-actual-assertion-mutations-with-required-independent-fixture

[Original receipt](../../verification/receipts/20261110T003249342972Z-original-cashflow-eight-actual-assertion-mutations-with-required-independent-fixture.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261110T003249342972Z-original-cashflow-eight-actual-assertion-mutations-with-required-independent-fixture/stdout.log)

~~~~text
{"name": "baseline", "exit_code": 0, "counts": {"tests": 89, "failures": 0, "errors": 0, "skipped": 0}, "mutation": null, "assertion_killed": false}
{"name": "float-baseline", "exit_code": 1, "counts": {"tests": 89, "failures": 17, "errors": 0, "skipped": 0}, "mutation": {"path": "backend/lab/source_cashflows.py", "original_sha256": "eaf380d33333fcaeab2394222e809b01ea659b6cac2d625efef9926a1b78a7c9", "mutant_sha256": "3b0d913571cf6542880b728b5fd9cea8a380d354ebbfa276354c7577aac23d0b", "needle": "net = gross+distributions-borrow-entry_fee-exit_fee", "replacement": "net = _number(trade['net_pnl'])"}, "assertion_killed": true}
~~~~

[Original stderr.log](../../verification/runs/20261110T003249342972Z-original-cashflow-eight-actual-assertion-mutations-with-required-independent-fixture/stderr.log)

~~~~text
Traceback (most recent call last):
  File "<workspace>\verification\runs\mutate-original-cashflow-baseline.py", line 42, in <module>
    assert any('AssertionError' in text or 'DID NOT RAISE' in text for text in failures),(name,'No assertion kill',failures[:1])
           ~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: ('drop-fees', 'No assertion kill', ['audit = <module \'backend.lab.source_cashflows\' from \'<user-home>\\\\Downloads\\\\price_action_strategies_ai_pathway\\\\data\\\\dev026\\\\cfm\\\\20261110T003249342972Z\\\\drop-fees\\\\backend\\\\lab\\\\source_cashflows.py\'>\nside = 1, order = \'next_open\'\n\n    @pytest.mark.parametrize(\'side\',[1,-1])\n    @pytest.mark.parametrize(\'order\',[\'next_open\',\'same_close\',\'limit\'])\n    def test_every_fee_reconciles_actual_original_observed_fills(audit,side,order):\n        from backend.lab.config import Costs\n        costs=Costs(commission_per_share=.017,minimum_commission=.031,fixed_fee_per_order=.027,sell_fee_per_dollar=.00013,spread_bps=3,slippage_bps=2,borrow_annual=0)\n        data,original,cost=observed(side=side,order=order,costs=costs)\n>       result=audit.audit_fills(data,original.trades,original.entry_traces,cost,[], \'b\'*64)\n               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n\ntests\\test_source_cashflows.py:62: \n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _\nbackend\\lab\\source_cashflows.py:153: in audit_fills\n    validate_audit(value, trades, entry_traces, cost.model_dump(), dataset_manifest_hash)\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _\n\nvalue = {\'version\': 1, \'policy\': \'decimal80-observed-fills-v1\', \'input_hash\': \'293265aaf5e04fce7a9b77d38289dd51e55daf6d5bb88076aa52edcdcd57edee\', \'actions_hash\': \'4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945\', ...}\ntrades = [{\'id\': \'known\', \'symbol\': \'SPY\', \'strategy_id\': \'94051904bc25ddad2242dc61b8f01ff89a887bb91f76c9f4396ed3b3eb8c1b4d\', \'family\': \'change_of_character\', ...}]\ntraces = [{\'version\': 1, \'trade_id\': \'known\', \'symbol\': \'SPY\', \'side\': 1, ...}]\ncosts = {\'commission_per_share\': 0.017, \'minimum_commission\': 0.031, \'fixed_fee_per_order\': 0.027, \'sell_fee_per_dollar\': 0.00013, ...}\nmanifest_hash = \'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\'\n\n    def validate_audit(value, trades, traces, costs, manifest_hash):\n        """Check the saved original audit without reading prices or recomputing orders.\n    \n        Original report/trial/attempt authority must additionally be verified by its\n        caller. A self-consistent digest is not evidence of original computation.\n        """\n        if (not isinstance(value, dict) or set(value) != {\'version\', \'policy\', \'input_hash\', \'actions_hash\', \'trades\', \'net_profit\', \'reported_net_profit\', \'difference\', \'audit_sha256\'}\n                or type(value[\'version\']) is not int or value[\'version\'] != 1 or value[\'policy\'] != POLICY\n                or value[\'audit_sha256\'] != identity({k: v for k, v in value.items() if k != \'audit_sha256\'})\n                or value[\'input_hash\'] != _input_hash(trades, traces, costs, manifest_hash)):\n            raise ValueError(\'Original canonical cash-flow audit is unavailable or differs; create a new compatible source account.\')\n        original = {t[\'id\']: t for t in trades}; records = value[\'trades\']\n        if not isinstance(records, list) or len(original) != len(trades) or len(records) != len(trades) or {t.get(\'id\') for t in records if isinstance(t, dict)} != set(original):\n            raise ValueError(\'Original cash-flow audit cohort differs.\')\n        cost = Costs(**costs); output = {}\n        with localcontext() as context:\n            context.prec = 80\n            for record in records:\n                if set(record) != {\'id\', *FIELDS}:\n                    raise ValueError(\'Original cash-flow audit trade shape differs.\')\n                amounts = {key: read_amount(record[key]) for key in FIELDS}; trade = original[record[\'id\']]\n                for key in FIELDS:\n                    if key in trade and abs(amounts[key]-_number(trade[key])) > TOLERANCE:\n>                       raise ValueError(\'Canonical executed cash flow does not reconcile with the original \'+key+\'.\')\nE                       ValueError: Canonical executed cash flow does not reconcile with the original net_pnl.\n\nbackend\\lab\\source_cashflows.py:181: ValueError'])
~~~~

## 20261110T004046159260Z-trade-twins-current-combined-matching-original-cashflows-finance-durability-api-and-exact-grading

[Original receipt](../../verification/receipts/20261110T004046159260Z-trade-twins-current-combined-matching-original-cashflows-finance-durability-api-and-exact-grading.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261110T004046159260Z-trade-twins-current-combined-matching-original-cashflows-finance-durability-api-and-exact-grading/stdout.log)

~~~~text
..................................                                       [100%]
================================== FAILURES ===================================
___________ test_trade_twin_core_joins_the_unchanged_numerical_gate ___________

    def test_trade_twin_core_joins_the_unchanged_numerical_gate():
        from verification.check_numerical_coverage import MODULES
>       assert len(MODULES) == 37 and MODULES[-10:] == ['backend/lab/trade_twins.py', 'backend/lab/trade_twin_source.py', 'backend/lab/trade_twin_execution.py', 'backend/lab/trade_twin_features.py', 'backend/lab/trade_twin_amounts.py', 'backend/lab/trade_twin_results.py', 'backend/lab/trade_twin_jobs.py', 'backend/lab/trade_twin_preparation.py', 'backend/lab/trade_twin_parts.py', 'backend/lab/trade_twin_worker.py']
E       AssertionError: assert (38 == 37)
E        +  where 38 = len(['backend/lab/config.py', 'backend/lab/data.py', 'backend/lab/signals.py', 'backend/lab/engine.py', 'backend/lab/metrics.py', 'backend/lab/service.py', ...])

tests\test_trade_twins.py:325: AssertionError
============================== warnings summary ===============================
..\..\..\.venv\Lib\site-packages\fastapi\testclient.py:1
  <workspace>\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=============================== tests coverage ================================
_______________ coverage: platform win32, python 3.13.5-final-0 _______________

Coverage JSON written to file <workspace>\verification\runs\20261110T004046159260Z-trade-twins-current-combined-matching-original-cashflows-finance-durability-api-and-exact-grading/current-trade-twin-combined-coverage.json
=========================== short test summary info ===========================
FAILED tests/test_trade_twins.py::test_trade_twin_core_joins_the_unchanged_numerical_gate
1 failed, 753 passed, 1 warning in 1104.44s (0:18:24)
~~~~

[Original stderr.log](../../verification/runs/20261110T004046159260Z-trade-twins-current-combined-matching-original-cashflows-finance-durability-api-and-exact-grading/stderr.log)

~~~~text

~~~~

## 20261110T005237189034Z-trade-twins-saved-evidence-manifest-authored-absence-before-implementation

[Original receipt](../../verification/receipts/20261110T005237189034Z-trade-twins-saved-evidence-manifest-authored-absence-before-implementation.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261110T005237189034Z-trade-twins-saved-evidence-manifest-authored-absence-before-implementation/stdout.log)

~~~~text
F                                                                        [100%]
================================== FAILURES ===================================
_____________ test_original_book_evidence_manifest_is_implemented _____________

    def test_original_book_evidence_manifest_is_implemented():
>       assert importlib.util.find_spec('backend.lab.trade_twin_evidence') is not None,'Original-bound book inspection manifests are not implemented.'
E       AssertionError: Original-bound book inspection manifests are not implemented.
E       assert None is not None
E        +  where None = <function find_spec at 0x00000210ED46F060>('backend.lab.trade_twin_evidence')
E        +    where <function find_spec at 0x00000210ED46F060> = <module 'importlib.util' (frozen)>.find_spec
E        +      where <module 'importlib.util' (frozen)> = importlib.util

tests\test_trade_twin_evidence.py:7: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_evidence.py::test_original_book_evidence_manifest_is_implemented
1 failed in 1.89s
~~~~

[Original stderr.log](../../verification/runs/20261110T005237189034Z-trade-twins-saved-evidence-manifest-authored-absence-before-implementation/stderr.log)

~~~~text

~~~~

## 20261110T005605730363Z-trade-twins-original-manifest-member-binding-computation-events-and-paired-part-regression

[Original receipt](../../verification/receipts/20261110T005605730363Z-trade-twins-original-manifest-member-binding-computation-events-and-paired-part-regression.json); command exit `4`.

[Original stdout.log](../../verification/runs/20261110T005605730363Z-trade-twins-original-manifest-member-binding-computation-events-and-paired-part-regression/stdout.log)

~~~~text

no tests ran in 0.64s
~~~~

[Original stderr.log](../../verification/runs/20261110T005605730363Z-trade-twins-original-manifest-member-binding-computation-events-and-paired-part-regression/stderr.log)

~~~~text
ERROR: file or directory not found: tests/test_trial_ledger.py

~~~~

## 20261110T005626036153Z-trade-twins-original-evidence-member-computation-and-paired-owned-worker-regression

[Original receipt](../../verification/receipts/20261110T005626036153Z-trade-twins-original-evidence-member-computation-and-paired-owned-worker-regression.json); command exit `4`.

[Original stdout.log](../../verification/runs/20261110T005626036153Z-trade-twins-original-evidence-member-computation-and-paired-owned-worker-regression/stdout.log)

~~~~text

no tests ran in 0.62s
~~~~

[Original stderr.log](../../verification/runs/20261110T005626036153Z-trade-twins-original-evidence-member-computation-and-paired-owned-worker-regression/stderr.log)

~~~~text
ERROR: file or directory not found: tests/test_trials.py

~~~~

## 20261110T005648114464Z-trade-twins-original-financial-member-evidence-computation-and-existing-trial-registry

[Original receipt](../../verification/receipts/20261110T005648114464Z-trade-twins-original-financial-member-evidence-computation-and-existing-trial-registry.json); command exit `2`.

[Original stdout.log](../../verification/runs/20261110T005648114464Z-trade-twins-original-financial-member-evidence-computation-and-existing-trial-registry/stdout.log)

~~~~text
........................................................................ [ 81%]
................                                                         [100%]
88 passed in 320.94s (0:05:20)
~~~~

[Original stderr.log](../../verification/runs/20261110T005648114464Z-trade-twins-original-financial-member-evidence-computation-and-existing-trial-registry/stderr.log)

~~~~text

~~~~

## 20261110T011406925725Z-trade-twins-first-real-saved-view-pages-repair-complete-zip-no-recomputation-and-api-bounds

[Original receipt](../../verification/receipts/20261110T011406925725Z-trade-twins-first-real-saved-view-pages-repair-complete-zip-no-recomputation-and-api-bounds.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261110T011406925725Z-trade-twins-first-real-saved-view-pages-repair-complete-zip-no-recomputation-and-api-bounds/stdout.log)

~~~~text
E       fixture 'client_lab' not found
>       available fixtures: anyio_backend, anyio_backend_name, anyio_backend_options, cache, capfd, capfdbinary, caplog, capsys, capsysbinary, capteesys, cov, doctest_namespace, empty, free_tcp_port, free_tcp_port_factory, free_udp_port, free_udp_port_factory, full_day, monkeypatch, no_cover, original, prepared_day, pytestconfig, record_property, record_testsuite_property, record_xml_attribute, recwarn, subtests, tmp_path, tmp_path_factory, tmpdir, tmpdir_factory
>       use 'pytest --fixtures [testpath]' for help on them.

<workspace>\data\dev026\evidence-src\tests\test_trade_twin_api.py:12
============================== warnings summary ===============================
..\..\..\.venv\Lib\site-packages\fastapi\testclient.py:1
  <workspace>\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
ERROR tests/test_trade_twin_views.py::test_real_ineligible_saved_pages_repair_and_complete_zip_are_not_financial_work
ERROR tests/test_trade_twin_views.py::test_saved_api_page_arguments_are_strict_before_work[query0]
ERROR tests/test_trade_twin_views.py::test_saved_api_page_arguments_are_strict_before_work[query1]
ERROR tests/test_trade_twin_views.py::test_saved_api_page_arguments_are_strict_before_work[query2]
ERROR tests/test_trade_twin_views.py::test_saved_api_page_arguments_are_strict_before_work[query3]
ERROR tests/test_trade_twin_views.py::test_saved_api_page_arguments_are_strict_before_work[query4]
ERROR tests/test_trade_twin_views.py::test_saved_api_page_arguments_are_strict_before_work[query5]
ERROR tests/test_trade_twin_views.py::test_saved_api_page_arguments_are_strict_before_work[query6]
ERROR tests/test_trade_twin_views.py::test_saved_api_page_arguments_are_strict_before_work[query7]
ERROR tests/test_trade_twin_views.py::test_wrong_job_unfinished_child_and_missing_derived_view_never_create_evidence
ERROR tests/test_trade_twin_views.py::test_source_parent_cannot_be_changed_by_caller_at_repair
2 passed, 1 warning, 11 errors in 16.18s
~~~~

[Original stderr.log](../../verification/runs/20261110T011406925725Z-trade-twins-first-real-saved-view-pages-repair-complete-zip-no-recomputation-and-api-bounds/stderr.log)

~~~~text

~~~~

## 20261110T014907015802Z-trade-twins-saved-only-view-empty-source-zip-csv-offline-report-and-original-lifecycle

[Original receipt](../../verification/receipts/20261110T014907015802Z-trade-twins-saved-only-view-empty-source-zip-csv-offline-report-and-original-lifecycle.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261110T014907015802Z-trade-twins-saved-only-view-empty-source-zip-csv-offline-report-and-original-lifecycle/stdout.log)

~~~~text
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x000001DF46373BB0>

    def test_real_ineligible_saved_pages_repair_and_complete_zip_are_not_financial_work(empty,monkeypatch):
        client,lab,parent,child=empty;before=fingerprints(lab,child['id'])
        def forbidden(*a,**k):raise AssertionError('Saved inspection/export must perform no financial or price recomputation.')
        monkeypatch.setattr('backend.lab.trade_twin_parts.execute_twin',forbidden)
        monkeypatch.setattr(lab,'_evaluation_input',forbidden)
        for policy in ['barrier_capped_elapsed_v1','fixed_elapsed_v1']:
            response=client.get('/api/jobs/'+child['id']+'/trade-twins/sets',params={'policy':policy})
>           assert response.status_code==200,response.text
E           AssertionError: {"detail":"Saved financial inspection evidence is missing, corrupt or incompatible; no financial result was recomputed."}
E           assert 409 == 200
E            +  where 409 = <Response [409 Conflict]>.status_code

tests\test_trade_twin_views.py:39: AssertionError
============================== warnings summary ===============================
..\..\..\.venv\Lib\site-packages\fastapi\testclient.py:1
  <workspace>\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_views.py::test_real_ineligible_saved_pages_repair_and_complete_zip_are_not_financial_work
1 failed, 12 passed, 1 warning in 35.01s
~~~~

[Original stderr.log](../../verification/runs/20261110T014907015802Z-trade-twins-saved-only-view-empty-source-zip-csv-offline-report-and-original-lifecycle/stderr.log)

~~~~text

~~~~

## 20261110T015043280147Z-trade-twins-direct-original-saved-view-error-chain-before-http-envelope

[Original receipt](../../verification/receipts/20261110T015043280147Z-trade-twins-direct-original-saved-view-error-chain-before-http-envelope.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261110T015043280147Z-trade-twins-direct-original-saved-view-error-chain-before-http-envelope/stdout.log)

~~~~text
            path=(original.folder/'views'/filename).resolve()
            # Each requested row/chunk is proved against originals. Hashing the whole
            # potentially large derived database on every page is unnecessary.
            cache=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True);cache.row_factory=sqlite3.Row
            cache.execute('PRAGMA query_only=ON');cache.execute('BEGIN')
            header=cache.execute('SELECT substr(value,1,65537),length(CAST(value AS BLOB)) FROM header').fetchall()
            if len(header)!=1 or header[0][1]>65536 or json.loads(header[0][0])!=original.header:raise StateError('Saved financial view header differs from original evidence.')
            if cache.execute('SELECT COUNT(*) FROM sets').fetchone()[0]!=2*original.header['expected_sets']:raise StateError('Saved financial view has missing or surplus set rows.')
            yield original,cache
            original.guard()
        except (OSError,sqlite3.DatabaseError,ValueError,KeyError,TypeError) as error:
>           raise StateError('Saved financial inspection evidence is missing, corrupt or incompatible; no financial result was recomputed.') from error
E           backend.lab.store.StateError: Saved financial inspection evidence is missing, corrupt or incompatible; no financial result was recomputed.

backend\lab\trade_twin_views.py:283: StateError
============================== warnings summary ===============================
..\..\..\.venv\Lib\site-packages\fastapi\testclient.py:1
  <workspace>\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_trade_twin_views.py::test_real_ineligible_saved_pages_repair_and_complete_zip_are_not_financial_work
1 failed, 1 warning in 11.68s
~~~~

[Original stderr.log](../../verification/runs/20261110T015043280147Z-trade-twins-direct-original-saved-view-error-chain-before-http-envelope/stderr.log)

~~~~text

~~~~

## 20261110T021154839695Z-trade-twins-actual-completed-positive-original-pages-books-full-export-and-tamper-counterexamples

[Original receipt](../../verification/receipts/20261110T021154839695Z-trade-twins-actual-completed-positive-original-pages-books-full-export-and-tamper-counterexamples.json); command exit `2`.

[Original stdout.log](../../verification/runs/20261110T021154839695Z-trade-twins-actual-completed-positive-original-pages-books-full-export-and-tamper-counterexamples/stdout.log)

~~~~text

=================================== ERRORS ====================================
________________________ ERROR collecting test session ________________________
ImportError while importing test module '<workspace>\verification\runs\twin-saved-evidence-positive.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
<user-home>\AppData\Local\Programs\Python\Python313\Lib\importlib\__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\verification\runs\twin-saved-evidence-positive.py:14: in <module>
    from backend.lab.trade_twin_views import repair_view
E   ModuleNotFoundError: No module named 'backend.lab.trade_twin_views'
============================== warnings summary ===============================
..\..\..\.venv\Lib\site-packages\fastapi\testclient.py:1
  <workspace>\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
ERROR 
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 warning, 1 error in 4.11s
~~~~

[Original stderr.log](../../verification/runs/20261110T021154839695Z-trade-twins-actual-completed-positive-original-pages-books-full-export-and-tamper-counterexamples/stderr.log)

~~~~text

~~~~

## 20261110T021238116079Z-trade-twins-positive-saved-evidence-correct-staged-imports-all-pages-complete-export-and-origin-faults

[Original receipt](../../verification/receipts/20261110T021238116079Z-trade-twins-positive-saved-evidence-correct-staged-imports-all-pages-complete-export-and-origin-faults.json); command exit `2`.

[Original stdout.log](../../verification/runs/20261110T021238116079Z-trade-twins-positive-saved-evidence-correct-staged-imports-all-pages-complete-export-and-origin-faults/stdout.log)

~~~~text
=================================== ERRORS ====================================
________________________ ERROR collecting test session ________________________
..\..\..\verification\runs\twin-saved-evidence-positive.py:12: in <module>
    assert Path(backend.__file__).resolve().is_relative_to((Path(__file__).resolve().parents[2]/'data/dev026/evidence-src').resolve()),'The verification must import the staged backend, never the installed app.'
E   AssertionError: The verification must import the staged backend, never the installed app.
E   assert False
E    +  where False = is_relative_to(WindowsPath('<workspace>/data/dev026/evidence-src'))
E    +    where is_relative_to = WindowsPath('<workspace>/backend/__init__.py').is_relative_to
E    +      where WindowsPath('<workspace>/backend/__init__.py') = resolve()
E    +        where resolve = WindowsPath('<workspace>/backend/__init__.py').resolve
E    +          where WindowsPath('<workspace>/backend/__init__.py') = <class 'pathlib._local.Path'>('<workspace>\\backend\\__init__.py')
E    +            where '<workspace>\\backend\\__init__.py' = <module 'backend' from '<workspace>\\backend\\__init__.py'>.__file__
E    +    and   WindowsPath('<workspace>/data/dev026/evidence-src') = resolve()
E    +      where resolve = (WindowsPath('<workspace>') / 'data/dev026/evidence-src').resolve
============================== warnings summary ===============================
..\..\..\.venv\Lib\site-packages\fastapi\testclient.py:1
  <workspace>\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
ERROR  - AssertionError: The verification must import the staged backend, nev...
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 warning, 1 error in 1.54s
~~~~

[Original stderr.log](../../verification/runs/20261110T021238116079Z-trade-twins-positive-saved-evidence-correct-staged-imports-all-pages-complete-export-and-origin-faults/stderr.log)

~~~~text

~~~~

## 20261110T021327181166Z-trade-twins-positive-saved-evidence-explicit-stage-config-all-original-pages-zip-and-tampering

[Original receipt](../../verification/receipts/20261110T021327181166Z-trade-twins-positive-saved-evidence-explicit-stage-config-all-original-pages-zip-and-tampering.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261110T021327181166Z-trade-twins-positive-saved-evidence-explicit-stage-config-all-original-pages-zip-and-tampering/stdout.log)

~~~~text
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=============================== tests coverage ================================
_______________ coverage: platform win32, python 3.13.5-final-0 _______________

Coverage JSON written to file <workspace>\verification\runs\20261110T021327181166Z-trade-twins-positive-saved-evidence-explicit-stage-config-all-original-pages-zip-and-tampering/saved-positive-coverage.json
=========================== short test summary info ===========================
ERROR ::test_all_20000_actual_original_outcomes_are_returned_in_bounded_api_pages
ERROR ::test_actual_members_and_every_array_match_complete_original_books - T...
ERROR ::test_complete_positive_zip_csv_and_standalone_report_have_no_missing_originals
ERROR ::test_rehashed_derived_views_and_damaged_originals_are_refused[derived_row]
ERROR ::test_rehashed_derived_views_and_damaged_originals_are_refused[derived_and_trial]
ERROR ::test_rehashed_derived_views_and_damaged_originals_are_refused[derived_chunk]
ERROR ::test_rehashed_derived_views_and_damaged_originals_are_refused[derived_book_manifest]
ERROR ::test_rehashed_derived_views_and_damaged_originals_are_refused[missing_set]
ERROR ::test_rehashed_derived_views_and_damaged_originals_are_refused[missing_computation]
ERROR ::test_rehashed_derived_views_and_damaged_originals_are_refused[computation_order]
ERROR ::test_rehashed_derived_views_and_damaged_originals_are_refused[checkpoint]
ERROR ::test_rehashed_derived_views_and_damaged_originals_are_refused[original_part]
ERROR ::test_rehashed_derived_views_and_damaged_originals_are_refused[part_index]
ERROR ::test_rehashed_derived_views_and_damaged_originals_are_refused[book_index]
ERROR ::test_rehashed_derived_views_and_damaged_originals_are_refused[trial_state]
ERROR ::test_rehashed_derived_views_and_damaged_originals_are_refused[root_bytes]
ERROR ::test_rehashed_derived_views_and_damaged_originals_are_refused[part_order]
37 warnings, 17 errors in 36.82s
~~~~

[Original stderr.log](../../verification/runs/20261110T021327181166Z-trade-twins-positive-saved-evidence-explicit-stage-config-all-original-pages-zip-and-tampering/stderr.log)

~~~~text

~~~~

## 20261110T021554790354Z-trade-twins-real-desktop-mobile-original-set-book-inspector-full-zip-and-obsolete-response-ownership

[Original receipt](../../verification/receipts/20261110T021554790354Z-trade-twins-real-desktop-mobile-original-set-book-inspector-full-zip-and-obsolete-response-ownership.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261110T021554790354Z-trade-twins-real-desktop-mobile-original-set-book-inspector-full-zip-and-obsolete-response-ownership/stdout.log)

~~~~text
      42 |   const response=page.waitForResponse(r=>r.url().endsWith('/api/jobs/'+jid+'/trade-twins/export'));
      43 |   await inspector.getByRole('link',{name:'Download complete saved evidence ZIP',exact:true}).click();
      44 |   const [file,http]=await Promise.all([download,response]);
        at <workspace>\verification\runs\twin-inspector-browser-tests\inspector.spec.ts:41:23

    attachment #1: screenshot (image/png) ──────────────────────────────────────────────────────────
    ..\verification\runs\20261110T021554790354Z-trade-twins-real-desktop-mobile-original-set-book-inspector-full-zip-and-obsolete-response-ownership\browser\artifacts\inspector-actual-original--e3440-port-and-response-ownership-mobile390\test-failed-1.png
    ────────────────────────────────────────────────────────────────────────────────────────────────

    Error Context: ..\verification\runs\20261110T021554790354Z-trade-twins-real-desktop-mobile-original-set-book-inspector-full-zip-and-obsolete-response-ownership\browser\artifacts\inspector-actual-original--e3440-port-and-response-ownership-mobile390\error-context.md

    attachment #3: trace (application/zip) ─────────────────────────────────────────────────────────
    ..\verification\runs\20261110T021554790354Z-trade-twins-real-desktop-mobile-original-set-book-inspector-full-zip-and-obsolete-response-ownership\browser\artifacts\inspector-actual-original--e3440-port-and-response-ownership-mobile390\trace.zip
    Usage:

        npx playwright show-trace ..\verification\runs\20261110T021554790354Z-trade-twins-real-desktop-mobile-original-set-book-inspector-full-zip-and-obsolete-response-ownership\browser\artifacts\inspector-actual-original--e3440-port-and-response-ownership-mobile390\trace.zip

    ────────────────────────────────────────────────────────────────────────────────────────────────

  3 failed
    [desktop1920] › ..\verification\runs\twin-inspector-browser-tests\inspector.spec.ts:6:1 › actual original sets members books complete export and response ownership 
    [desktop1280] › ..\verification\runs\twin-inspector-browser-tests\inspector.spec.ts:6:1 › actual original sets members books complete export and response ownership 
    [mobile390] › ..\verification\runs\twin-inspector-browser-tests\inspector.spec.ts:6:1 › actual original sets members books complete export and response ownership 
{"review_output": "verification/runs/20261110T021554790354Z-trade-twins-real-desktop-mobile-original-set-book-inspector-full-zip-and-obsolete-response-ownership/browser", "child_exit_code": 1, "privacy_policy": 1, "raw_capture_id": "c790da35e6164721a5a1eaf7d0d9f0ec"}
~~~~

[Original stderr.log](../../verification/runs/20261110T021554790354Z-trade-twins-real-desktop-mobile-original-set-book-inspector-full-zip-and-obsolete-response-ownership/stderr.log)

~~~~text
(node:53388) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
(node:37220) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
(node:29276) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
~~~~

## 20261110T021644867002Z-trade-twins-positive-original-all-20000-pages-complete-csv-zip-and-rehashed-view-faults

[Original receipt](../../verification/receipts/20261110T021644867002Z-trade-twins-positive-original-all-20000-pages-complete-csv-zip-and-rehashed-view-faults.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261110T021644867002Z-trade-twins-positive-original-all-20000-pages-complete-csv-zip-and-rehashed-view-faults/stdout.log)

~~~~text
    return ConfigDict()
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

::test_rehashed_derived_views_and_damaged_originals_are_refused[missing_set]
  <user-home>\AppData\Local\Programs\Python\Python313\Lib\copyreg.py:99: ResourceWarning: unclosed database in <sqlite3.Connection object at 0x0000013A28D3DF30>
    return cls.__new__(cls, *args)
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

::test_rehashed_derived_views_and_damaged_originals_are_refused[missing_computation]
  <user-home>\AppData\Local\Programs\Python\Python313\Lib\typing.py:1423: ResourceWarning: unclosed database in <sqlite3.Connection object at 0x0000013A28B7F1F0>
    def __init__(self, origin, args, *, inst=True, name=None):
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=============================== tests coverage ================================
_______________ coverage: platform win32, python 3.13.5-final-0 _______________

Coverage JSON written to file <workspace>\verification\runs\20261110T021644867002Z-trade-twins-positive-original-all-20000-pages-complete-csv-zip-and-rehashed-view-faults/saved-positive-coverage.json
=========================== short test summary info ===========================
FAILED ::test_rehashed_derived_views_and_damaged_originals_are_refused[part_order]
1 failed, 16 passed, 6 warnings in 233.08s (0:03:53)
~~~~

[Original stderr.log](../../verification/runs/20261110T021644867002Z-trade-twins-positive-original-all-20000-pages-complete-csv-zip-and-rehashed-view-faults/stderr.log)

~~~~text

~~~~

## 20261110T022126792700Z-trade-twins-real-inspector-complete-verified-download-desktop-mobile-and-selection-ownership

[Original receipt](../../verification/receipts/20261110T022126792700Z-trade-twins-real-inspector-complete-verified-download-desktop-mobile-and-selection-ownership.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261110T022126792700Z-trade-twins-real-inspector-complete-verified-download-desktop-mobile-and-selection-ownership/stdout.log)

~~~~text
      43 |   await inspector.getByRole('link',{name:'Download complete saved evidence ZIP',exact:true}).click();
      44 |   const [file,http]=await Promise.all([download,response]);
      45 |   expect(http.status()).toBe(200);
        at <workspace>\verification\runs\twin-inspector-browser-tests\inspector.spec.ts:42:23

    attachment #1: screenshot (image/png) ──────────────────────────────────────────────────────────
    ..\verification\runs\20261110T022126792700Z-trade-twins-real-inspector-complete-verified-download-desktop-mobile-and-selection-ownership\browser\artifacts\inspector-actual-original--e3440-port-and-response-ownership-mobile390\test-failed-1.png
    ────────────────────────────────────────────────────────────────────────────────────────────────

    Error Context: ..\verification\runs\20261110T022126792700Z-trade-twins-real-inspector-complete-verified-download-desktop-mobile-and-selection-ownership\browser\artifacts\inspector-actual-original--e3440-port-and-response-ownership-mobile390\error-context.md

    attachment #3: trace (application/zip) ─────────────────────────────────────────────────────────
    ..\verification\runs\20261110T022126792700Z-trade-twins-real-inspector-complete-verified-download-desktop-mobile-and-selection-ownership\browser\artifacts\inspector-actual-original--e3440-port-and-response-ownership-mobile390\trace.zip
    Usage:

        npx playwright show-trace ..\verification\runs\20261110T022126792700Z-trade-twins-real-inspector-complete-verified-download-desktop-mobile-and-selection-ownership\browser\artifacts\inspector-actual-original--e3440-port-and-response-ownership-mobile390\trace.zip

    ────────────────────────────────────────────────────────────────────────────────────────────────

  3 failed
    [desktop1920] › ..\verification\runs\twin-inspector-browser-tests\inspector.spec.ts:6:1 › actual original sets members books complete export and response ownership 
    [desktop1280] › ..\verification\runs\twin-inspector-browser-tests\inspector.spec.ts:6:1 › actual original sets members books complete export and response ownership 
    [mobile390] › ..\verification\runs\twin-inspector-browser-tests\inspector.spec.ts:6:1 › actual original sets members books complete export and response ownership 
{"review_output": "verification/runs/20261110T022126792700Z-trade-twins-real-inspector-complete-verified-download-desktop-mobile-and-selection-ownership/browser", "child_exit_code": 1, "privacy_policy": 1, "raw_capture_id": "9e42865435e1411fa06d4d3613230f0e"}
~~~~

[Original stderr.log](../../verification/runs/20261110T022126792700Z-trade-twins-real-inspector-complete-verified-download-desktop-mobile-and-selection-ownership/stderr.log)

~~~~text
(node:44428) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
(node:46844) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
(node:52504) Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.
(Use `node --trace-warnings ...` to show where the warning was created)
~~~~

## 20261110T022418931452Z-trade-twins-authored-original-preparation-manifest-and-publication-causality-counterexamples

[Original receipt](../../verification/receipts/20261110T022418931452Z-trade-twins-authored-original-preparation-manifest-and-publication-causality-counterexamples.json); command exit `1`.

[Original stdout.log](../../verification/runs/20261110T022418931452Z-trade-twins-authored-original-preparation-manifest-and-publication-causality-counterexamples/stdout.log)

~~~~text
                else:db.execute('UPDATE events SET id=(SELECT MAX(id)+1 FROM events) WHERE id=?',(event,))
        if fault=='original_part':
            part=next((lab.output_path(JID).parent/'twins/parts').glob('part-000000-*.json.gz'));part.write_bytes(part.read_bytes()+b'corrupt')
        elif fault=='root_bytes':lab.output_path(JID).write_bytes(lab.output_path(JID).read_bytes()+b'corrupt')
        endpoint=f'/api/jobs/{JID}/trade-twins/sets/0/books/0' if fault in {'derived_chunk','derived_book_manifest','book_index'} else f'/api/jobs/{JID}/trade-twins/sets'
        response=browser.post(f'/api/jobs/{JID}/trade-twins/repair-view',json={}) if fault=='prep_order' else browser.get(endpoint,params=dict(policy=policy))
>       assert response.status_code==409,(fault,response.text[:1000])
E       AssertionError: ('publication_order', '{"job_id":"3b9f36b31fee4bae838f5a2f6e638049","policy":"barrier_capped_elapsed_v1","rows":[{"out..."error":null,"net_profit":"0.000","plan_hash":"0a3557aa06a41d6277de1f9a761eebb9ab887e6fcbd4d2b97e3c1cc373d00945","pol')
E       assert 200 == 409
E        +  where 200 = <Response [200 OK]>.status_code

..\..\..\verification\runs\twin-saved-evidence-positive.py:191: AssertionError
============================== warnings summary ===============================
..\..\..\.venv\Lib\site-packages\fastapi\testclient.py:1
  <workspace>\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED ::test_rehashed_derived_views_and_damaged_originals_are_refused[prep_order]
FAILED ::test_rehashed_derived_views_and_damaged_originals_are_refused[manifest_event]
FAILED ::test_rehashed_derived_views_and_damaged_originals_are_refused[manifest_order]
FAILED ::test_rehashed_derived_views_and_damaged_originals_are_refused[publication_order]
4 failed, 17 deselected, 1 warning in 50.26s
~~~~

[Original stderr.log](../../verification/runs/20261110T022418931452Z-trade-twins-authored-original-preparation-manifest-and-publication-causality-counterexamples/stderr.log)

~~~~text

~~~~

## 20261110T023025000612Z-trade-twins-original-publication-preparation-part-causality-fixed-and-real-empty-view-export-regression

[Original receipt](../../verification/receipts/20261110T023025000612Z-trade-twins-original-publication-preparation-part-causality-fixed-and-real-empty-view-export-regression.json); command exit `2`.

[Original stdout.log](../../verification/runs/20261110T023025000612Z-trade-twins-original-publication-preparation-part-causality-fixed-and-real-empty-view-export-regression/stdout.log)

~~~~text

=================================== ERRORS ====================================
_______________ ERROR collecting tests/test_trade_twin_views.py _______________
ImportError while importing test module '<workspace>\data\dev026\evidence-src\tests\test_trade_twin_views.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
tests\test_trade_twin_views.py:4: in <module>
    from test_trade_twin_api import original
E   ModuleNotFoundError: No module named 'test_trade_twin_api'
============================== warnings summary ===============================
..\..\..\.venv\Lib\site-packages\fastapi\testclient.py:1
  <workspace>\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
ERROR tests/test_trade_twin_views.py
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
16 deselected, 1 warning, 1 error in 3.29s
~~~~

[Original stderr.log](../../verification/runs/20261110T023025000612Z-trade-twins-original-publication-preparation-part-causality-fixed-and-real-empty-view-export-regression/stderr.log)

~~~~text

~~~~

