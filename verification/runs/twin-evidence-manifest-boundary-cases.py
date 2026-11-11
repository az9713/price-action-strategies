"""Complete/failed original book schemas and hash-consistent malformed manifests."""
import copy
import pytest
from test_trade_twin_evidence import evidence, book, independent_hash


@pytest.mark.parametrize('fault', ['not_a_book', 'missing_field', 'non_list_array'])
def test_complete_book_schema_cannot_be_replaced_by_a_partial_summary(evidence, book, fault):
    bad = copy.deepcopy(book)
    if fault == 'not_a_book':
        bad = []
    elif fault == 'missing_field':
        del bad['financing']
    else:
        bad['ledger'] = {'0': bad['ledger'][0]}
    with pytest.raises(ValueError):
        evidence.book_manifest(bad)


def test_actual_failed_liquidity_book_keeps_all_rejection_evidence(evidence):
    from test_trade_twin_execution import frame, match_for, execute
    from backend.lab.trade_twin_parts import freeze
    bars = frame()
    bars.loc[:, 'volume'] = 0
    actual = execute(bars, match_for(bars))
    assert actual['status'] == 'failed' and actual['trade'] is None
    assert actual['failure'] and actual['net_profit'] is None
    value = freeze(actual)
    manifest = evidence.book_manifest(value)
    assert manifest['scalar_fields']['status'] == 'failed'
    assert manifest['scalar_fields']['failure'] == value['failure']
    for kind in evidence.ARRAYS:
        assert manifest['counts'][kind] == len(value[kind])
        for index, offset in enumerate(range(0, len(value[kind]), 25)):
            assert evidence.verify_chunk(manifest, kind, index, value[kind][offset:offset+25]) == value[kind][offset:offset+25]


@pytest.mark.parametrize('fault', ['complete_no_trade', 'complete_with_failure', 'unknown_status', 'failed_with_profit', 'failed_without_reason', 'count_negative', 'count_boolean', 'count_string', 'hashes_not_list', 'count_sequence_mismatch', 'chunk_digest_malformed'])
def test_even_hash_consistent_bound_manifests_must_have_complete_financial_semantics(evidence, book, fault):
    value = evidence.book_manifest(book)
    scalar = value['scalar_fields']
    if fault == 'complete_no_trade': scalar['trade'] = None
    elif fault == 'complete_with_failure': scalar['failure'] = 'concealed failure'
    elif fault == 'unknown_status': scalar['status'] = 'partial'
    elif fault == 'failed_with_profit': scalar.update(status='failed', net_profit='0', failure='failed')
    elif fault == 'failed_without_reason': scalar.update(status='failed', net_profit=None, failure=None)
    elif fault == 'count_negative': value['counts']['ledger'] = -1
    elif fault == 'count_boolean': value['counts']['ledger'] = True
    elif fault == 'count_string': value['counts']['ledger'] = '2'
    elif fault == 'hashes_not_list': value['arrays']['ledger'] = {}
    elif fault == 'count_sequence_mismatch': value['arrays']['ledger'] = []
    else: value['arrays']['ledger'][0] = 'X'*64
    # A self-consistent digest does not make a malformed financial record valid.
    with pytest.raises(ValueError):
        evidence.verify_manifest(value, independent_hash(value), independent_hash(book))


def test_cancellation_during_chunking_and_after_complete_validation_returns_no_manifest(evidence, book):
    book['ledger'] = [{'amount': str(i)} for i in range(80)]
    for stop_at in [2, 4, 6]:
        seen = []
        def canceled():
            seen.append(True)
            return len(seen) >= stop_at
        with pytest.raises(InterruptedError):
            evidence.book_manifest(book, canceled)
        assert len(seen) == stop_at
