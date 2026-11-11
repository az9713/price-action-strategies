"""Bounded exact finite-decimal totals and canonical financial persistence.

No global Decimal context changes and no conversion through binary floats.
The initial working bounds reject visibly; no trade or amount is truncated.
"""
from decimal import Decimal,InvalidOperation,localcontext

MAX_AMOUNT_TEXT=1024
MAX_AMOUNT_EXPONENT=4096
MAX_TOTAL_TERMS=20000


def _finite(value):
    if isinstance(value,bool) or not isinstance(value,(str,int,float,Decimal)):
        raise ValueError('Financial amount must be an explicit finite number.')
    try:amount=Decimal(str(value))
    except (InvalidOperation,ValueError) as error:
        raise ValueError('Financial amount is not a Decimal.') from error
    if not amount.is_finite():
        raise ValueError('Financial amount must be finite.')
    if abs(amount.adjusted())>MAX_AMOUNT_EXPONENT or abs(amount.as_tuple().exponent)>MAX_AMOUNT_EXPONENT:
        raise ValueError('Financial amount exponent working bound exceeded.')
    if len(str(amount))>MAX_AMOUNT_TEXT:
        raise ValueError('Canonical financial amount text working bound exceeded.')
    return amount


def canonical_amount(value):
    """Encode an internal finite amount without changing its decimal value."""
    return str(_finite(value))


def read_amount(value):
    """Require an original canonical string; numeric/alternate spellings refuse."""
    if not isinstance(value,str) or len(value)>MAX_AMOUNT_TEXT:
        raise ValueError('Saved financial amount requires bounded canonical Decimal text.')
    amount=_finite(value)
    if str(amount)!=value:
        raise ValueError('Saved financial amount is not canonical Decimal text.')
    return amount


def exact_total(values):
    """Retain every finite term, including exponent gaps and cancellation."""
    amounts=[]
    for value in values:
        amounts.append(_finite(value))
        if len(amounts)>MAX_TOTAL_TERMS:
            raise ValueError('Financial total term working bound exceeded; no subset was summed.')
    if not amounts:
        return Decimal(0)
    precision=max(80,max(v.adjusted() for v in amounts)-min(v.as_tuple().exponent for v in amounts)+len(str(len(amounts)))+2)
    with localcontext() as context:
        context.prec=precision
        total=sum(amounts,Decimal(0))
    return _finite(total)
