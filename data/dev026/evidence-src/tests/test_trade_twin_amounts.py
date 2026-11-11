"""Canonical saved money, full finite sums and explicit initial working bounds."""
from decimal import Decimal,localcontext
from fractions import Fraction
import pytest
from backend.lab import trade_twin_amounts as money

@pytest.mark.parametrize('text',['0','-0','0.00','1.001','-14.99','1E-300','1E+308','9'*1024,'0E-4096'])
def test_canonical_amount_roundtrip_keeps_the_original_decimal_value(text):
    value=money.read_amount(text)
    assert money.canonical_amount(value)==text and Fraction(value)==Fraction(Decimal(text))

@pytest.mark.parametrize('bad',[True,False,None,[],{},'','invalid','NaN','Infinity','-Infinity','1E+4097','0E-4097','9'*1025])
def test_nonfinite_invalid_and_oversized_amounts_refuse(bad):
    with pytest.raises(ValueError):money.canonical_amount(bad)

@pytest.mark.parametrize('bad',[1,1.,Decimal('1'),True,' 1','+1','001','1e3','1.0e2'])
def test_original_saved_money_refuses_numeric_and_alternate_spelling(bad):
    with pytest.raises(ValueError):money.read_amount(bad)

@pytest.mark.parametrize('values',[[1e100,1e-100,-1e100],[1e-100,-1e100,1e100],['10000000000.0','1E-300'],[Decimal('0.00000013'),Decimal('-0.00000012')],[]])
def test_sum_matches_independent_fraction_under_adverse_ambient_precision(values):
    expected=sum((Fraction(str(v)) for v in values),Fraction(0))
    with localcontext() as context:
        context.prec=2
        actual=money.exact_total(values)
        assert context.prec==2
    assert Fraction(actual)==expected

def test_complete_original_cohort_bound_never_sums_a_subset():
    assert money.exact_total('0' for _ in range(20000))==0
    with pytest.raises(ValueError,match='no subset'):money.exact_total('0' for _ in range(20001))

def test_sum_can_refuse_a_result_outside_saved_amount_bounds_without_rounding():
    with pytest.raises(ValueError,match='text working bound'):money.exact_total(['9'*1024,'1'])
    with pytest.raises(ValueError,match='exponent working bound'):money.exact_total(['1E+4096']*10)
