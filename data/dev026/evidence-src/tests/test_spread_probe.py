"""Actual guarded primary-instrument signal generation; no profit computation."""
from pathlib import Path
import hashlib,json,os
import numpy as np,pandas as pd,pytest
from backend.lab.config import Strategy,identity,canonical
from backend.lab.data import save_dataset,schedule,atomic_json,load_dataset,DataError
from backend.lab.service import Lab
from backend.lab.models import Study
from backend.lab.research import ResearchError

def receipt_artifact(name,value):
    if os.environ.get('PA_EVIDENCE_RUN_DIR'):
        p=Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'spread-actual-primary-signals'/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(canonical(value),encoding='utf-8')

@pytest.fixture
def owned(tmp_path):
    lab=Lab(tmp_path);rows=[]
    closes=json.loads((Path(__file__).resolve().parents[1]/'verification/fixtures/strategy-baselines.json').read_text())['common_closes']
    for day,(opened,closed) in schedule('2026-10-05','2026-10-30').items():
        times=pd.date_range(opened,closed,freq='min',inclusive='left')
        for symbol in ['SPY','QQQ']:
            values=np.resize(np.array(closes+[200.,200.,100.]),len(times)) if symbol=='SPY' else np.full(len(times),100.)
            rows.append(pd.DataFrame(dict(symbol=symbol,timestamp=times,open=values-.02,high=values+.1,low=values-.1,close=values,volume=10000.)))
    manifest=save_dataset(lab.datasets_root,pd.concat(rows,ignore_index=True),dict(input_kind='synthetic',source='Repeated authored strict-pivot geometry; flat secondary instrument'),start='2026-10-05',end='2026-10-30')
    context=dict(dataset_id=manifest['id'],dataset_manifest_hash=identity(manifest),primary_symbol='SPY',start='2026-10-19',end='2026-10-30')
    cfg=Strategy(family='break_of_structure',timeframe='1m',swing_strength=2,direction='long')
    return lab,manifest,context,cfg

def test_actual_probe_preserves_primary_warmup_full_signal_evidence_without_accounts(owned,monkeypatch):
    lab,m,context,cfg=owned
    def forbidden(*a,**k):raise AssertionError('Signal qualification executed P&L')
    monkeypatch.setattr('backend.lab.service.simulate',forbidden);monkeypatch.setattr('backend.lab.service.summary',forbidden)
    result=lab.spread_signal_probe(context,cfg)
    assert result['signal_count']>=40 and result['excluded_warmup_signals']>0
    assert result['signal_count']==sum(context['start']<=pd.Timestamp(s['available_at']).tz_convert('America/New_York').date().isoformat()<=context['end'] for s in result['signals'])
    assert all(s['symbol']=='SPY' for s in result['signals'])
    assert result['context']==context and result['dataset_context']['symbols']==['QQQ','SPY']
    assert not {'metrics','trades','ledger','equity'}&set(result)
    other=lab.spread_signal_probe(context|{'primary_symbol':'QQQ'},cfg);assert other['signal_count']==0 and other['signals']==[]
    receipt_artifact('primary-complete-signals.json',result);receipt_artifact('secondary-flat-complete-signals.json',other)

@pytest.mark.parametrize('fault',['unknown_primary','manifest','protected','news_missing'])
def test_probe_rejects_invalid_scope_before_price_load(owned,monkeypatch,fault):
    lab,m,context,cfg=owned
    if fault=='unknown_primary':context=context|{'primary_symbol':'TSLA'}
    elif fault=='manifest':context=context|{'dataset_manifest_hash':'0'*64}
    elif fault=='news_missing':cfg=cfg.model_copy(update={'news':'skip'})
    else:
        lab.register_study(Study(name='Owned untouched final',dataset_id=m['id'],discovery={'start':'2026-10-05','end':'2026-10-09'},validation={'start':'2026-10-12','end':'2026-10-16'},holdout={'start':'2026-10-19','end':'2026-10-30'},configurations=[cfg],minimum_trades=1))
    def forbidden(*a,**k):raise AssertionError('Invalid/protected probe reached price loading')
    monkeypatch.setattr('backend.lab.service.load_window',forbidden)
    with pytest.raises((DataError,ResearchError)):lab.spread_signal_probe(context,cfg)

def test_actual_probe_artifact_hash_anchors_replayed_qualification(owned,tmp_path):
    from backend.lab.spread import SpreadSettings,freeze_plan,select
    lab,m,context,cfg=owned
    # Small explicitly configured integration sample, retaining the actual40-signal threshold.
    s=SpreadSettings(families=['break_of_structure'],timeframes=['1m'],per_family=1,batch_size=40,max_batches_per_family=2)
    plan=freeze_plan(tmp_path/'proposals',s);events=[];artifacts={}
    def probe(value):
        result=lab.spread_signal_probe(context,Strategy(**value));raw=canonical(result).encode();digest=hashlib.sha256(raw).hexdigest()
        path=tmp_path/(digest+'.json');path.write_bytes(raw);artifacts[digest]=path
        receipt_artifact(digest+'.json',result)
        return dict(signal_count=result['signal_count'],evidence_sha256=digest)
    def authorize():
        lab.guard.access(m['quality']['symbols'],m['quality']['start'],context['end'],'spread_probe_test',record=False)
        for digest,path in artifacts.items():assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    result=select(plan,context,probe,events.append,authorize=authorize)
    assert result['complete'] and len(result['selected'])==1
    for event in events:
        if event['kind']=='probe_completed':
            saved=json.loads(artifacts[event['evidence']['evidence_sha256']].read_text())
            assert saved['signal_count']==event['evidence']['signal_count'] and saved['context']==context
    def unexpected(*a):raise AssertionError('Committed primary signals were recomputed')
    resumed=select(plan,context,unexpected,lambda e:None,authorize=authorize,replay=events)
    assert resumed['selected']==result['selected'] and resumed['probe_computations']==0 and resumed['reused_probes']==len(artifacts)
    receipt_artifact('actual-qualified-selection-and-replay.json',dict(scope='Actual synthetic primary signals with40 threshold; one selected version, not full40000 source scale or selected-account P&L',context=context,result=result,replayed=resumed,events=events,probe_artifact_hashes=list(artifacts)))

def test_primary_probe_does_not_open_another_instruments_sealed_dates(owned,monkeypatch):
    lab,m,context,cfg=owned;raw,_=load_dataset(lab.datasets_root,m['id'])
    secondary=save_dataset(lab.datasets_root,raw.loc[raw.symbol=='QQQ'],dict(input_kind='synthetic',source='Owned secondary-only frozen study'),start='2026-10-05',end='2026-10-30')
    lab.register_study(Study(name='Unopened secondary',dataset_id=secondary['id'],discovery={'start':'2026-10-05','end':'2026-10-09'},validation={'start':'2026-10-12','end':'2026-10-16'},holdout={'start':'2026-10-19','end':'2026-10-30'},configurations=[cfg],minimum_trades=1))
    from backend.lab import service
    original=service.load_window;predicates=[]
    def selected(*a,**k):predicates.append(k.get('symbols'));assert k['symbols']==['SPY'];return original(*a,**k)
    monkeypatch.setattr(service,'load_window',selected)
    result=lab.spread_signal_probe(context,cfg);assert result['signal_count']>=40 and predicates==[['SPY']]
    assert result['signal_scope']['symbols']==['SPY']
    with lab.store.db() as db:assert db.execute("SELECT COUNT(*) FROM viewed_windows WHERE symbol='QQQ'").fetchone()[0]==0

def test_primary_subset_cache_cannot_reuse_another_instrument_frame(owned,monkeypatch):
    from backend.lab.evaluation_cache import evaluation_cache
    from backend.lab import service
    lab,m,context,cfg=owned;original=service.load_window;predicates=[]
    def selected(*a,**k):predicates.append(k.get('symbols'));return original(*a,**k)
    monkeypatch.setattr(service,'load_window',selected)
    with evaluation_cache(lab.root):
        a=lab.spread_signal_probe(context,cfg);b=lab.spread_signal_probe(context|{'primary_symbol':'QQQ'},cfg);c=lab.spread_signal_probe(context,cfg)
    assert a==c and a['signal_count']>=40 and b['signal_count']==0
    assert predicates==[['SPY'],['QQQ']]

def test_frozen_news_context_and_hash_are_checked_before_prices(owned,monkeypatch):
    from backend.lab.news import NewsCalendar
    lab,m,context,cfg=owned;calendar=lab.news.save(NewsCalendar(name='Owned synthetic calendar',start='2026-10-05',end='2026-10-30',mode='synthetic',complete=True,events=[]))
    frozen=context|dict(news_calendar_id=calendar['id'],news_calendar_hash=identity(calendar))
    result=lab.spread_signal_probe(frozen,cfg.model_copy(update={'news':'skip'}));assert result['context']==frozen and result['news_calendar']==calendar
    def forbidden(*a,**k):raise AssertionError('Changed news hash reached price loading')
    monkeypatch.setattr('backend.lab.service.load_window',forbidden)
    with pytest.raises(DataError):lab.spread_signal_probe(frozen|{'news_calendar_hash':'f'*64},cfg)
