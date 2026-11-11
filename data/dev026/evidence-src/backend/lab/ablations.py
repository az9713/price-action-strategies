"""Paired complete-calendar dollar comparisons of independent strategy accounts."""
import math
import numpy as np
import pandas as pd
from .config import Strategy,Portfolio,identity
from .data import DataError,schedule
from .metrics import block_interval

MONEY_TOLERANCE=1e-7

def _validate_account(report):
    days=list(schedule(report['start'],report['end']))
    if [r['date'] for r in report['equity']]!=days or not days:raise DataError('Ablation accounts need the complete identical eligible-session calendar.')
    capital=Portfolio(**report['portfolio']).capital
    equity=np.array([capital,*[r['equity'] for r in report['equity']]],float)
    if not np.isfinite(equity).all():raise DataError('Ablation equity must be finite.')
    daily=np.diff(equity);metrics=report['metrics']
    trade_pnl=np.array([t['net_pnl'] for t in report['trades']],float)
    if (len(metrics['daily_pnl'])!=len(daily) or not np.isfinite(metrics['daily_pnl']).all() or
        not np.isfinite(trade_pnl).all() or abs(float(trade_pnl.sum())-float(daily.sum()))>MONEY_TOLERANCE or
        not np.allclose(daily,metrics['daily_pnl'],rtol=0,atol=MONEY_TOLERANCE) or
        not math.isfinite(metrics['net_profit']) or abs(float(daily.sum())-metrics['net_profit'])>MONEY_TOLERANCE or
        metrics['trades']!=len(report['trades'])):raise DataError('Ablation account statistics do not reconcile to its complete equity calendar.')
    cfg=Strategy(**report['config'])
    if report['config_id']!=identity(cfg):raise DataError('Ablation configuration identity mismatch.')
    decisions=set()
    for signal in report['signals']:
        at=pd.Timestamp(signal['available_at'])
        if at.tz is None or signal['side'] not in {-1,1}:raise DataError('Ablation signal decisions require explicit clocks and direction.')
        if report['start']<=at.tz_convert('America/New_York').strftime('%Y-%m-%d')<=report['end']:
            decisions.add((signal['symbol'],at.tz_convert('UTC').isoformat(),signal['side']))
    return cfg,daily,decisions

def paired_comparison(baseline,alternative,field,seed=42):
    for key in ['dataset_id','dataset_manifest_hash','core_hash','start','end','costs','portfolio','news_dates','news_calendar']:
        if baseline.get(key)!=alternative.get(key):raise DataError('Ablation accounts have incompatible '+key+'.')
    base,daily_a,signals_a=_validate_account(baseline);other,daily_b,signals_b=_validate_account(alternative)
    differences=[k for k,v in base.model_dump().items() if v!=other.model_dump()[k]]
    if differences!=[field]:raise DataError('Compared accounts must differ in exactly the declared public strategy field.')
    if (baseline['news_dates'] is not None or base.news!='trade' or other.news!='trade') and baseline.get('news_calendar') is None:
        raise DataError('Ablation news comparisons require the versioned calendar contract.')
    delta=daily_b-daily_a;net=float(delta.sum())
    if not math.isfinite(net) or abs(net-(alternative['metrics']['net_profit']-baseline['metrics']['net_profit']))>MONEY_TOLERANCE:
        raise DataError('Paired daily differences do not reconcile to the account difference.')
    # A sample that fits into one circular block is always resampled in full;
    # its total has artificial zero variance, not informative uncertainty.
    enough=len(delta)>5 and bool(baseline['trades']) and bool(alternative['trades'])
    interval=block_interval(delta,seed=seed) if enough else None
    return dict(field=field,baseline_config_id=identity(base),alternative_config_id=identity(other),
        baseline_value=base.model_dump()[field],alternative_value=other.model_dump()[field],
        baseline_trigger=base.trigger,alternative_trigger=other.trigger,
        baseline_trades=len(baseline['trades']),alternative_trades=len(alternative['trades']),
        baseline_signals=len(signals_a),alternative_signals=len(signals_b),common_decision_signals=len(signals_a&signals_b),
        baseline_only_signals=len(signals_a-signals_b),alternative_only_signals=len(signals_b-signals_a),
        baseline_net_profit=baseline['metrics']['net_profit'],alternative_net_profit=alternative['metrics']['net_profit'],
        net_difference=net,paired_pnl_interval=interval,sessions=len(delta),
        daily_differences=[dict(date=r['date'],difference=float(value)) for r,value in zip(baseline['equity'],delta)],
        status='Descriptive paired comparison' if enough else 'Need at least6 sessions and executed trades in both accounts for five-session block uncertainty',
        limitations=['Each account regenerates its own signals, fills and risk sizing. Trades are not paired by position in a list.',
            'The complete session calendar includes zero-trade sessions. Interval is descriptive and not adjusted for selecting among many strategies.',
            'Changing a public timeframe/trigger field can change an inferred trigger. Both effective triggers are reported.'])
