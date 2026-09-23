"""Reusable bounded Decimal parsing and arithmetic independent of ambient context."""

import re
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_UP, localcontext


_DECIMAL_LEXEME = re.compile(
    r"[+-]?(?:(?:[0-9]+(?:\.[0-9]*)?)|(?:\.[0-9]+))(?:[eE][+-]?[0-9]+)?\Z"
)
_TOTAL_CONTEXT = Context(prec=64, rounding=ROUND_HALF_UP)


def parse_decimal(value, *, minimum=None, maximum=None, max_integral_digits=18, max_fractional_digits=4):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    if isinstance(value, int):
        if value.bit_length() > 64:
            return None
        lexeme = str(value)
    elif isinstance(value, str):
        lexeme = value
    else:
        lexeme = str(value)
    if len(lexeme) > 128 or _DECIMAL_LEXEME.fullmatch(lexeme) is None:
        return None
    try:
        parsed = Decimal(lexeme)
    except InvalidOperation:
        return None
    if not parsed.is_finite():
        return None

    _sign, raw_digits, exponent = parsed.as_tuple()
    digits = list(raw_digits)
    if any(digits):
        while digits and digits[-1] == 0:
            digits.pop()
            exponent += 1
        adjusted = len(digits) + exponent - 1
        if max(adjusted + 1, 0) > max_integral_digits:
            return None
        if max(-exponent, 0) > max_fractional_digits:
            return None
    if minimum is not None and parsed < minimum:
        return None
    if maximum is not None and parsed > maximum:
        return None
    return parsed


def quantize_product(left, multiplier, quantum="0.01"):
    with localcontext(_TOTAL_CONTEXT):
        return (left * multiplier).quantize(Decimal(quantum))


def fixed_decimal(value, places=2):
    return format(value, ".{}f".format(places))
