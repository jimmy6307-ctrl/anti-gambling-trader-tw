"""Shioaji historical tick timestamp documentation QA (not a feed validator).

The vendor's example shows nanosecond epoch values beside naive local-clock
strings. Do not guess the timezone convention from a documentation example.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
TAIPEI = ZoneInfo('Asia/Taipei')


def inspect_epoch_vs_displayed(ts_ns: int, displayed_naive: str) -> dict:
    """Classify whether documented ns epoch agrees with the printed clock.

    Every outcome remains BLOCKED until live tick and official auction checks.
    """
    if isinstance(ts_ns, bool) or not isinstance(ts_ns, int) or not 10**18 <= ts_ns < 2 * 10**18:
        raise ValueError('expected integer Unix nanoseconds in plausible 2001-2033 range')
    shown = datetime.fromisoformat(displayed_naive)
    if shown.tzinfo is not None:
        raise ValueError('displayed documentation clock must be timezone-naive')
    utc_dt = EPOCH + timedelta(microseconds=ts_ns // 1000)
    taipei_dt = utc_dt.astimezone(TAIPEI)
    if shown == taipei_dt.replace(tzinfo=None):
        result = 'CONSISTENT_WITH_TRUE_UTC_EPOCH'
    elif shown == utc_dt.replace(tzinfo=None):
        result = 'EIGHT_HOUR_AMBIGUITY_OR_DOCUMENTATION_MISMATCH'
    else:
        result = 'UNRECONCILED_CLOCK'
    return {
        'status': result,
        'utc_clock': utc_dt.isoformat(),
        'taipei_clock': taipei_dt.isoformat(),
        'displayed_naive_clock': shown.isoformat(),
        'strategy_gate': 'BLOCKED',
        'timestamp_semantics': 'UNVERIFIED_NEEDS_LIVE_FEED_AND_TICKS',
    }
