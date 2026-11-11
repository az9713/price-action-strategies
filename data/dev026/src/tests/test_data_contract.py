import numpy as np
import pandas as pd
import pytest
from backend.lab.data import normalize,audit,prepare,aggregate,schedule,Action,save_dataset,load_dataset,DataError
from conftest import minute_frame

def test_identical_duplicate_and_order_are_recorded(full_day):
    source=pd.concat([full_day.iloc[::-1],full_day.iloc[[0]]],ignore_index=True)
    actual,report=normalize(source)
    assert len(actual)==390
    assert report=={'identical_duplicates_removed':1,'reordered':True}
    assert actual.timestamp.is_monotonic_increasing

def test_conflicting_duplicate_rejected(full_day):
    extra=full_day.iloc[[0]].copy();extra['volume']=3
    with pytest.raises(DataError,match='Conflicting'): normalize(pd.concat([full_day,extra]))

@pytest.mark.parametrize('column,value',[('low',0),('high',99),('volume',-1),('close',np.nan),('open',np.inf)])
def test_invalid_prices_rejected(full_day,column,value):
    full_day.loc[0,column]=value
    with pytest.raises(DataError): normalize(full_day)

def test_naive_requires_mapping(full_day):
    full_day['timestamp']=full_day.timestamp.dt.tz_localize(None)
    with pytest.raises(DataError,match='timezone'): normalize(full_day)
    assert normalize(full_day,'UTC')[0].timestamp.dt.tz is not None

def test_nonminute_rejected(full_day):
    full_day.loc[0,'timestamp']+=pd.Timedelta(seconds=1)
    with pytest.raises(DataError,match='exact minutes'): normalize(full_day)

def test_alias_and_conflicting_schema(full_day):
    alias=full_day.rename(columns=dict(timestamp='t',open='o',high='h',low='l',close='c',volume='v'))
    pd.testing.assert_frame_equal(normalize(full_day)[0],normalize(alias)[0])
    alias['open']=100
    with pytest.raises(DataError,match='Ambiguous'): normalize(alias)

def test_holiday_early_close_and_gap_count():
    frame=pd.concat([minute_frame('2026-11-25'),minute_frame('2026-11-27')],ignore_index=True)
    quality=audit(normalize(frame)[0],'2026-11-25','2026-11-27')
    assert quality['eligible'] and [x['expected'] for x in quality['sessions']]==[390,210]
    bad=audit(normalize(frame.drop(index=2))[0],'2026-11-25','2026-11-27')
    assert bad['missing_minutes']==1 and not bad['eligible']

def test_calendar_dst():
    assert schedule('2026-10-30','2026-10-30')['2026-10-30'][0].hour==13
    assert schedule('2026-11-02','2026-11-02')['2026-11-02'][0].hour==14

@pytest.mark.parametrize('tf,count,last_duration',[('1m',390,1),('5m',78,5),('15m',26,15),('1h',7,30),('4h',2,150),('1d',1,390)])
def test_aggregation_expected_volume_and_timing(prepared_day,tf,count,last_duration):
    bars=aggregate(prepared_day,tf)
    assert len(bars)==count and bars.complete.all()
    assert bars.volume.sum()==3_900_000
    assert bars.iloc[-1].duration_minutes==last_duration
    assert bars.iloc[-1].available_at==pd.Timestamp('2026-11-05T21:00Z')
    assert (bars.available_at>bars.timestamp).all()

def test_four_hour_remainder_on_early_close():
    regular=prepare(normalize(minute_frame('2026-11-27'))[0])
    bars=aggregate(regular,'4h')
    assert len(bars)==1 and bars.iloc[0].duration_minutes==210
    assert bool(bars.iloc[0].partial_length)

def test_incomplete_bar_not_made_complete(prepared_day):
    bars=aggregate(prepared_day.drop(index=4),'5m')
    assert not bool(bars.iloc[0].complete) and bars.iloc[0]['count']==4

def test_forward_split_normalization_uses_past_events_only():
    first=minute_frame('2026-11-04',close=[100]);second=minute_frame('2026-11-05',close=[50])
    raw,_=normalize(pd.concat([first,second]))
    regular=prepare(raw,[Action('SPY','2026-11-05','split',2)])
    bars=aggregate(regular,'1d')
    assert bars.close.tolist()==[100,100] and bars.factor.tolist()==[1,2]
    future=prepare(raw,[Action('SPY','2026-11-06','split',2)])
    assert future.factor.eq(1).all()

def test_immutable_store_parquet_roundtrip_and_tamper(tmp_path,full_day):
    original,_=normalize(full_day)
    manifest=save_dataset(tmp_path,original,{'source':'synthetic'})
    actual,loaded=load_dataset(tmp_path,manifest['id'])
    pd.testing.assert_frame_equal(actual,original)
    assert loaded['quality']['eligible']
    path=tmp_path/manifest['id']/'minutes.parquet'
    path.write_bytes(path.read_bytes()+b'corruption')
    with pytest.raises(DataError,match='hash mismatch'): load_dataset(tmp_path,manifest['id'])

def test_dataset_id_blocks_traversal(tmp_path):
    with pytest.raises(DataError,match='Invalid dataset'): load_dataset(tmp_path,'../.env')

def test_manifest_tampering_rejected(tmp_path,full_day):
    import json
    manifest=save_dataset(tmp_path,full_day,{'source':'synthetic'})
    path=tmp_path/manifest['id']/'manifest.json'
    value=json.loads(path.read_text());value['metadata']['source']='fake-provider'
    path.write_text(json.dumps(value))
    with pytest.raises(DataError,match='manifest hash'): load_dataset(tmp_path,manifest['id'])

def test_timezone_offsets_across_dst_are_valid(full_day):
    frame=full_day.iloc[:2].copy()
    frame['timestamp']=['2026-10-30T09:30:00-04:00','2026-11-02T09:30:00-05:00']
    actual,_=normalize(frame)
    assert actual.timestamp.dt.hour.tolist()==[13,14]

def test_weekend_only_is_explicit_no_session():
    frame=pd.DataFrame([{'symbol':'SPY','timestamp':'2026-11-07T14:30:00Z','open':100,'high':101,'low':99,'close':100,'volume':100}])
    with pytest.raises(DataError,match='No regular'): audit(normalize(frame)[0])

def test_explicit_symbol_selection_reaudits_and_retains_parent(tmp_path,full_day):
    from backend.lab.data import select_dataset
    other=full_day.copy();other['symbol']='QQQ';other=other.drop(index=2)
    parent=save_dataset(tmp_path,pd.concat([full_day,other]),{'source':'synthetic'})
    assert not parent['quality']['eligible']
    selected=select_dataset(tmp_path,parent['id'],['SPY'])
    assert selected['quality']['eligible']
    assert selected['metadata']['selection']['parent_id']==parent['id']
    assert not load_dataset(tmp_path,parent['id'])[1]['quality']['eligible']
