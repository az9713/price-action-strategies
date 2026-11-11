import numpy as np
import pandas as pd
import pytest
from backend.lab.data import schedule,normalize,prepare

def minute_frame(day='2026-11-05',symbol='SPY',close=None):
    opened,closed=schedule(day,day)[day]
    index=pd.date_range(opened,closed,freq='min',inclusive='left')
    values=np.full(len(index),100.) if close is None else np.resize(np.asarray(close,float),len(index))
    return pd.DataFrame(dict(symbol=symbol,timestamp=index,open=values,high=values+.1,low=values-.1,close=values,volume=10000.))

@pytest.fixture
def full_day(): return minute_frame()

@pytest.fixture
def prepared_day(full_day): return prepare(normalize(full_day)[0])
