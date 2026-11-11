"""Small independent stdlib statistical oracles; no production or SciPy imports."""
import math
from statistics import NormalDist, mean, stdev


def sharpe_from_equity(capital, equity, annual_risk_free=0):
    values = [capital, *equity]
    returns = [(new-old)/old for old,new in zip(values,values[1:])]
    excess = [value-annual_risk_free/252 for value in returns]
    return mean(excess)/stdev(excess)*math.sqrt(252)


def dsr_from_moments(sharpe, observations, skewness, raw_kurtosis, trials, trial_sharpe_std):
    normal = NormalDist()
    gamma = 0.5772156649015329
    benchmark = 0 if trials == 1 else trial_sharpe_std * (
        (1-gamma)*normal.inv_cdf(1-1/trials) + gamma*normal.inv_cdf(1-1/(trials*math.e)))
    variance = 1-skewness*sharpe+(raw_kurtosis-1)*sharpe**2/4
    return normal.cdf((sharpe-benchmark)*math.sqrt((observations-1)/variance))


def linear_quantile(values, probability):
    ordered = sorted(values)
    rank = (len(ordered)-1)*probability
    lower = math.floor(rank)
    upper = math.ceil(rank)
    return ordered[lower]+(ordered[upper]-ordered[lower])*(rank-lower)
