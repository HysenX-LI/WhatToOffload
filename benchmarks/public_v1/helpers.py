"""Neutral helper supplied identically to both construction arms and agent baselines."""
from decimal import Decimal, InvalidOperation


def money(value):
    if not isinstance(value, str):
        raise ValueError("price must be a decimal string")
    try:
        result = Decimal(value)
    except InvalidOperation:
        raise ValueError("invalid price") from None
    if not result.is_finite() or result < 0 or result != result.quantize(Decimal("0.01")):
        raise ValueError("price must be finite, nonnegative and cent-exact")
    return result
