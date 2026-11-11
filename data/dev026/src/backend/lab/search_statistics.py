"""Prespecified DSR sensitivity over every account in one completed search."""
import math
import re
import warnings
import numpy as np
from scipy.stats import skew,kurtosis
from .models import SearchStatistics
from .metrics import deflated_sharpe_from_moments
from .config import identity
from .data import DataError

POLICY_VERSION=1


def moments(returns):
    empty=dict(observations=len(returns) if isinstance(returns,list) else 0,daily_sharpe=None,skewness=None,raw_kurtosis=None)
    if not isinstance(returns,list) or any(type(x) not in (float,int) or not math.isfinite(x) for x in returns):
        return empty,'invalid_returns'
    if len(returns)<4:return empty,'insufficient_observations'
    values=np.asarray(returns,float)
    with np.errstate(all='ignore'),warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter('always',RuntimeWarning)
        sigma=float(values.std(ddof=1));average=float(values.mean())
        if not math.isfinite(sigma) or not math.isfinite(average):return empty,'nonfinite_moments'
        if sigma==0:return empty,'zero_return_variance'
        sr=average/sigma;sk=float(skew(values,bias=False));ku=float(kurtosis(values,fisher=False,bias=False))
    if notices or not all(math.isfinite(x) for x in [sr,sk,ku]):return empty,'nonfinite_moments'
    return dict(observations=len(returns),daily_sharpe=sr,skewness=sk,raw_kurtosis=ku),None


def build_search_statistics(rows,policy:SearchStatistics,sampling=None,cancel=None):
    if not isinstance(rows,list) or not rows:raise DataError('Search statistics require completed configuration rows.')
    settings=policy.resolve(len(rows));measured=[];seen=set();parts=set()
    for index,row in enumerate(rows):
        if cancel and index%64==0 and cancel():raise InterruptedError('Search statistics canceled while reading saved account metrics.')
        if (not isinstance(row,dict) or not isinstance(row.get('metrics'),dict) or
            type(row.get('part')) is not int or row['part']<0 or row['part'] in parts or
            not isinstance(row.get('config_id'),str) or not re.fullmatch('[a-f0-9]{64}',row['config_id']) or row['config_id'] in seen or
            not isinstance(row.get('report_sha256'),str) or not re.fullmatch('[a-f0-9]{64}',row['report_sha256'])):
            raise DataError('Malformed or duplicate completed search account.')
        profit=row['metrics'].get('net_profit')
        if type(profit) not in (float,int) or not math.isfinite(profit):raise DataError('Search account profit must be finite.')
        seen.add(row['config_id']);parts.add(row['part'])
        value,reason=moments(row['metrics'].get('daily_returns'));measured.append((row,value,reason))
    sharpes=[m['daily_sharpe'] for _,m,reason in measured if reason is None]
    if settings.dispersion_mode=='assumed':dispersion=settings.trial_sharpe_std
    else:
        with np.errstate(all='ignore'):
            dispersion=float(np.std(sharpes,ddof=1)) if len(sharpes)>1 else None
        if dispersion is not None and not math.isfinite(dispersion):dispersion=None
    accounts=[]
    for index,(row,value,reason) in enumerate(measured):
        if cancel and index%64==0 and cancel():raise InterruptedError('Search statistics canceled before complete sensitivity publication.')
        sensitivity=[]
        for trials in settings.effective_trials:
            undefined=reason;score=None
            if undefined is None:
                if trials>1 and dispersion is None:undefined='dispersion_unavailable'
                else:
                    score=deflated_sharpe_from_moments(value['daily_sharpe'],value['observations'],value['skewness'],value['raw_kurtosis'],trials,0 if trials==1 else dispersion)
                    if score is None:undefined='invalid_model_variance'
            sensitivity.append(dict(effective_trials=trials,score=score,undefined_reason=undefined))
        accounts.append(dict(part=row['part'],config_id=row['config_id'],source_part_sha256=row['report_sha256'],
            net_profit=row['metrics']['net_profit'],**value,sensitivity=sensitivity))
    limitations=[
        'Effective independent trial counts are prespecified sensitivity assumptions, never inferred from raw configuration counts.',
        'This diagnostic covers this search only; undisclosed prior searches and manual selection are not corrected.',
        'Daily-return moments and a sampling approximation do not establish serial independence, future profitability or a global error guarantee.',
        'All complete accounts, including losses and undefined scores, remain in the cohort. No candidate gate uses this score.',
        'The single-trial scenario has a zero search benchmark and does not require cross-trial dispersion.',
    ]
    if dispersion==0:limitations.append('Zero cross-trial dispersion makes sensitivity mechanically flat; it does not establish absence of overfitting.')
    return dict(policy_version=POLICY_VERSION,role='derived_search_diagnostic',settings=settings.model_dump(),
        return_unit='per-session marked-equity percentage return; zero risk-free assumption; no annualization inside DSR',
        raw_configurations=len(rows),finite_sharpe_accounts=len(sharpes),trial_sharpe_std=dispersion,
        raw_generation={key:None if sampling is None else sampling.get(key) for key in ['attempts','unique','duplicates','rejected']},
        account_manifest_hash=identity([dict(part=r['part'],config_id=r['config_id'],sha256=r['report_sha256']) for r in rows]),
        accounts=accounts,limitations=limitations,source='https://davidhbailey.com/dhbpapers/deflated-sharpe.pdf')
