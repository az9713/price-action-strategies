"""Marked-capital statistics. Undefined statistics remain null with explicit notes."""
import numpy as np
from numbers import Integral
from scipy.stats import norm,skew,kurtosis

def summary(simulation,capital,annual_risk_free=0.0):
    try:
        with np.errstate(over='raise',invalid='raise',divide='raise'):
            return _summary(simulation,capital,annual_risk_free)
    except (FloatingPointError,OverflowError) as error:
        raise ValueError('Metric arithmetic exceeds the finite numerical range.') from error

def _summary(simulation,capital,annual_risk_free):
    equity=np.array([x['equity'] for x in simulation.equity],float)
    pnl=np.array([x['net_pnl'] for x in simulation.trades],float)
    if not np.isfinite(capital) or capital<=0 or not np.isfinite(annual_risk_free):
        raise ValueError('Metrics require positive finite capital and a finite risk-free assumption.')
    if equity.ndim!=1 or pnl.ndim!=1 or not np.isfinite(equity).all() or not np.isfinite(pnl).all():
        raise ValueError('Metrics require finite one-dimensional equity and trade P&L.')
    values=np.r_[capital,equity]
    returns=np.full(len(equity),np.nan)
    np.divide(np.diff(values),values[:-1],out=returns,where=values[:-1]>0)
    excess=returns-annual_risk_free/252
    solvent=bool((values>0).all())
    sigma=float(excess.std(ddof=1)) if len(excess)>1 and solvent else 0.
    profit=float(pnl[pnl>0].sum());loss=float(-pnl[pnl<0].sum())
    drawdown=values/np.maximum.accumulate(values)-1
    output=dict(net_profit=float(values[-1]-capital),total_return=float(values[-1]/capital-1),
        marked_sharpe=float(excess.mean()/sigma*np.sqrt(252)) if sigma>0 else None,
        max_drawdown=float(-drawdown.min()),trades=len(pnl),win_rate=float((pnl>0).mean()) if len(pnl) else None,
        profit_factor=profit/loss if loss else None,positive_profit=bool(values[-1]>capital),
        daily_returns=[float(r) if np.isfinite(r) else None for r in returns],daily_pnl=np.diff(values).tolist(),
        undefined=[])
    if not solvent:
        output['undefined'].append('Nonpositive equity makes percentage-return Sharpe undefined; dollar P&L and drawdown remain reported. Returns with nonpositive starting equity are null.')
    elif not sigma: output['undefined'].append('Sharpe needs at least two varying daily returns.')
    if not loss: output['undefined'].append('Profit factor is undefined without losing trades; it is not a passing badge.')
    if not len(pnl): output['undefined'].append('No executed trades; win rate is undefined.')
    by_day=np.diff(values)
    top=np.sort(by_day)[-min(10,len(by_day)):]
    output['profit_without_ten_best_days']=float(by_day.sum()-top.sum())
    output['best_day_profit']=float(by_day.max()) if len(by_day) else None
    output['risk_basis']='Daily marked equity / defined capital; calendar complete eligible sessions including no-trade days.'
    return output

def deflated_sharpe_from_moments(sharpe,observations,skewness,raw_kurtosis,trials,trial_sharpe_std):
    """DSR with explicitly supplied, per-observation moments and trial dispersion.

    This entry point supports independently published moment examples. It does not
    invent returns or infer independent trials from the configuration count.
    """
    inputs=[sharpe,skewness,raw_kurtosis,trials,trial_sharpe_std]
    if (not isinstance(observations,Integral) or isinstance(observations,bool) or observations<4 or
        not np.isfinite(inputs).all() or trials<1 or trial_sharpe_std<0): return None
    euler=.5772156649015329
    # Inverse survival avoids cancellation in 1-1/N for large trial counts.
    threshold=0. if trials==1 else trial_sharpe_std*((1-euler)*norm.isf(1/trials)+euler*norm.isf((1/trials)/np.e))
    denominator=1-skewness*sharpe+(raw_kurtosis-1)/4*sharpe*sharpe
    if denominator<=0 or not np.isfinite(denominator) or not np.isfinite(threshold): return None
    value=float(norm.cdf((sharpe-threshold)*np.sqrt(observations-1)/np.sqrt(denominator)))
    return value if np.isfinite(value) else None

def deflated_sharpe(returns,trials,trial_sharpe_std):
    """Bailey/Lopez de Prado PSR versus expected maximum, in per-observation units.

    Effective independent trial count and cross-trial SR standard deviation are inputs,
    not silently inferred from raw configuration count. No annualization inside formula.
    """
    r=np.asarray(returns,float)
    if r.ndim!=1 or len(r)<4 or not np.isfinite(r).all() or r.std(ddof=1)==0:
        return None
    sr=float(r.mean()/r.std(ddof=1))
    return deflated_sharpe_from_moments(sr,len(r),float(skew(r,bias=False)),
        float(kurtosis(r,fisher=False,bias=False)),trials,trial_sharpe_std)

def block_interval(daily_pnl,seed=42,resamples=2000,block=5):
    x=np.asarray(daily_pnl,float)
    if x.ndim!=1 or not np.isfinite(x).all(): raise ValueError('Bootstrap needs finite daily P&L, not a matrix.')
    if (not isinstance(resamples,Integral) or isinstance(resamples,bool) or not 2<=resamples<=100000 or
        not isinstance(block,Integral) or isinstance(block,bool) or not 1<=block<=100000):
        raise ValueError('Bootstrap needs 2–100000 resamples and 1–100000 sessions per block, both integers.')
    if not isinstance(seed,Integral) or isinstance(seed,bool) or not 0<=seed<=2**64-1:
        raise ValueError('Bootstrap seed must be an unsigned 64-bit integer.')
    if len(x)<2: return None
    rng=np.random.default_rng(seed)
    effective=min(block,len(x));blocks=int(np.ceil(len(x)/effective))
    batch=max(1,min(128,2000000//(blocks*effective)))
    totals=np.empty(resamples)
    for offset in range(0,resamples,batch):
        size=min(batch,resamples-offset)
        starts=rng.integers(0,len(x),size=(size,blocks))
        indices=(starts[:,:,None]+np.arange(effective))%len(x)
        totals[offset:offset+size]=x[indices.reshape(size,-1)[:,:len(x)]].sum(axis=1)
    return dict(low=float(np.quantile(totals,.025)),high=float(np.quantile(totals,.975)),
                unit='dollars',method='circular moving blocks of daily P&L',block_sessions=block,resamples=resamples,seed=seed)
