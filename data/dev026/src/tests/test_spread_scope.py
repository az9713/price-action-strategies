"""Instrument-subset loader compatibility and source-integrity boundaries."""
import pytest
from test_spread_probe import owned
from backend.lab.data import load_dataset,save_dataset,DataError
from backend.lab.config import identity
from backend.lab.evaluation_cache import evaluation_cache

@pytest.mark.parametrize('symbols',[[],['SPY','SPY'],['MISSING'],('SPY',),'SPY',False,[['SPY']]])
def test_bad_subset_rejects_before_authorization_or_data_loading(owned,monkeypatch,symbols):
    lab,m,context,cfg=owned
    def forbidden(*a,**k):raise AssertionError('Bad instrument selection reached authorization or data')
    monkeypatch.setattr(lab.guard,'access',forbidden);monkeypatch.setattr('backend.lab.service.load_window',forbidden)
    with pytest.raises(DataError):lab._evaluation_input(m['id'],context['start'],context['end'],expected_manifest=context['dataset_manifest_hash'],symbols=symbols)

def test_symbol_order_is_canonical_and_distinct_from_the_legacy_full_source_key(owned,monkeypatch):
    from backend.lab import service
    lab,m,context,cfg=owned;original=service.load_window;calls=[]
    def counted(*a,**k):calls.append(k.get('symbols'));return original(*a,**k)
    monkeypatch.setattr(service,'load_window',counted)
    args=(m['id'],context['start'],context['end'])
    with evaluation_cache(lab.root):
        first=lab._evaluation_input(*args,symbols=['SPY','QQQ'])[1]
        second=lab._evaluation_input(*args,symbols=['QQQ','SPY'])[1]
        legacy=lab._evaluation_input(*args)[1]
    assert first.equals(second) and first.equals(legacy)
    assert calls==[['QQQ','SPY'],None]

def test_unselected_incomplete_symbol_does_not_change_whole_source_rejection(owned):
    lab,m,context,cfg=owned;frame,_=load_dataset(lab.datasets_root,m['id'])
    bad_index=frame.loc[frame.symbol=='QQQ'].index[0];frame=frame.drop(bad_index)
    subset=save_dataset(lab.datasets_root,frame,dict(input_kind='synthetic',source='Owned missing secondary minute'),start='2026-10-05',end='2026-10-30')
    assert not subset['quality']['eligible']
    scope=context|dict(dataset_id=subset['id'],dataset_manifest_hash=identity(subset))
    result=lab.spread_signal_probe(scope,cfg);assert result['signal_count']>=40
    with pytest.raises(DataError):lab._evaluation_input(subset['id'],'2026-10-05','2026-10-30')

def test_subset_cache_still_hashes_the_entire_original_source_file(owned):
    lab,m,context,cfg=owned
    with evaluation_cache(lab.root):
        lab.spread_signal_probe(context,cfg)
        path=lab.datasets_root/m['id']/'minutes.parquet';raw=path.read_bytes();path.write_bytes(b'X'+raw[1:])
        with pytest.raises(DataError):lab.spread_signal_probe(context,cfg)
