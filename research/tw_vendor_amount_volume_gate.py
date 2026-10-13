"""Offline Shioaji OHLC/Amount/Volume dimensional sanity check.

A diagnostic for published examples or *authorized* vendor payloads, NOT
proof of vendor volume units, bar labels, auction semantics, or trade fills.
Do not use this as an automated trading data admission decision.
"""
from decimal import Decimal, InvalidOperation


def _positive_decimal(value, label):
    if isinstance(value, bool):
        raise ValueError(f"{label}: boolean not allowed")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{label}: invalid number") from exc
    if not number.is_finite() or number <= 0:
        raise ValueError(f"{label}: must be finite and positive")
    return number


def classify_amount_volume(*, low, high, volume, amount, lot_size=1000):
    """Compare implied VWAP under two *hypotheses*, not a feed certification.

    `volume` is either shares or board lots; `amount` is assumed TWD turnover.
    Reject malformed inputs; do not silently assume the board-lot hypothesis.
    This function is intended for normal board-lot equity examples only.
    """
    lo = _positive_decimal(low, 'low')
    hi = _positive_decimal(high, 'high')
    vol = _positive_decimal(volume, 'volume')
    amt = _positive_decimal(amount, 'amount')
    if lo > hi:
        raise ValueError('low exceeds high')
    if isinstance(lot_size, bool) or not isinstance(lot_size, int) or lot_size <= 1:
        raise ValueError('lot_size must be an integer > 1')
    vwap_if_shares = amt / vol
    vwap_if_lots = amt / (vol * Decimal(lot_size))
    shares_plausible = lo <= vwap_if_shares <= hi
    lots_plausible = lo <= vwap_if_lots <= hi
    if shares_plausible and lots_plausible:
        classification = 'BOTH_PLAUSIBLE_UNRESOLVED'
    elif shares_plausible:
        classification = 'SHARES_ONLY_DOCUMENTATION_CONSISTENT'
    elif lots_plausible:
        classification = 'LOTS_ONLY_DOCUMENTATION_CONSISTENT'
    else:
        classification = 'NEITHER_PLAUSIBLE_REJECT_UNITS_OR_FIELDS'
    return {
        'classification': classification,
        'implied_vwap_if_shares': str(vwap_if_shares),
        'implied_vwap_if_lots': str(vwap_if_lots),
        'plausible_if_shares': shares_plausible,
        'plausible_if_lots': lots_plausible,
        'lot_size_hypothesis': lot_size,
        'data_gate': 'BLOCKED_NEEDS_AUTHENTICATED_TICKS_AND_OFFICIAL_RECONCILIATION',
        'strategy_gate': 'BLOCKED',
    }
