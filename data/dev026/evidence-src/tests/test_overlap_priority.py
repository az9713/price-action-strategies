from decimal import Decimal
import pandas as pd
import pytest
from conftest import minute_frame
from backend.lab.config import Strategy
from backend.lab.data import normalize,prepare
from backend.lab.signals import generate_signals

def reflected(frame):
    result=frame.copy()
    for to,source in [('open','open'),('close','close'),('high','low'),('low','high')]:
        result[to]=frame[source].map(lambda value:float(Decimal(300)-Decimal(str(value))))
    return result

def triangle(equal_anchors=False):
    raw=minute_frame('2026-10-05').iloc[:20].copy()
    raw[['open','high','low','close']]=[104.4,106.,103.,104.5]
    if equal_anchors:
        edits={8:(110,100),14:(108,102),15:(106,103.5),16:(106,103.6),17:(105.9,103.7),18:(105.8,103.8),19:(108.1,101.9)}
    else:
        edits={5:(110,103),6:(108,102),7:(107,101),8:(106,100),9:(106.5,101),10:(107,102),11:(108,103),12:(107,103.1),13:(106.5,102.5),
            14:(106.4,102),15:(106.3,103.1),16:(106,103.3),17:(105.6,103.6),18:(105,103.8),19:(105.5,103.5)}
    for i,(high,low) in edits.items(): raw.loc[i,['high','low']]=[high,low]
    return prepare(normalize(raw)[0])

@pytest.mark.parametrize('side',[1,-1])
def test_newest_line_anchor_priority_is_mirror_symmetric(side):
    frame=triangle()
    if side<0: frame=reflected(frame)
    cfg=Strategy(family='trend_line',timeframe='1m',direction='both',swing_strength=2)
    matches=[s for s in generate_signals(frame,cfg) if s.source_index==19]
    assert len(matches)==1 and matches[0].side==side
    level=Decimal(102)+Decimal(2)/Decimal(6)*Decimal(5)
    if side<0: level=Decimal(300)-level
    assert matches[0].level==pytest.approx(float(level),abs=1e-9)

@pytest.mark.parametrize('family',['trend_line','level_bounce'])
def test_equally_fresh_opposite_candidates_are_ambiguous(family):
    frame=triangle(True)
    for candidate in [frame,reflected(frame)]:
        cfg=Strategy(family=family,timeframe='1m',direction='both',swing_strength=2)
        assert not [s for s in generate_signals(candidate,cfg) if s.source_index==19]

def gap_context_frame():
    closes=[100,101,103,105,102,100,103,106,110,112,108,105,108,114]
    raw=minute_frame('2026-10-05').iloc[:26].copy()
    for i,close in enumerate(closes): raw.loc[i,['open','high','low','close']]=[close-.02,close+.1,close-.1,close]
    raw.loc[5,'low']=94.6;raw.loc[11,'low']=98.2
    edits={14:[100,100.1,99.9,100],15:[100.5,112,100,108],16:[106,109,105,108],17:[110,112,109,111],
        18:[111,112,110,111],19:[110,111,109,110],20:[111,112,110,111],21:[110,111,109,110],
        22:[105.5,106,105.2,105.5],23:[105.5,105.9,105.1,105.5],24:[105.5,105.8,105.2,105.5],25:[105.5,105.8,105.2,105.5]}
    for i,values in edits.items(): raw.loc[i,['open','high','low','close']]=values
    return prepare(normalize(raw)[0])

@pytest.mark.parametrize('side',[1,-1])
def test_opposite_gap_cannot_erase_an_existing_same_side_confluence(side):
    frame=gap_context_frame()
    if side<0: frame=reflected(frame)
    common={'family':'trend_line','timeframe':'1m','direction':'long' if side>0 else 'short','swing_strength':2}
    baseline=[s for s in generate_signals(frame,Strategy(**common)) if s.source_index==23]
    assert len(baseline)==1 and baseline[0].level==pytest.approx(105 if side>0 else 195)
    filtered=[s for s in generate_signals(frame,Strategy(**common,gap_confluence=True)) if s.source_index==23]
    assert len(filtered)==1
