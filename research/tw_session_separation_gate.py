"""Fail-closed Taiwan stock tick session segregation for source QA, not fills.

TWSE's normal close may be delayed to 13:33; after-hours fixed-price and
odd-lot matching at 14:30 must never be folded into the normal-session close.
This classifier does not establish the vendor's timestamp or market-segment semantics.
"""
from datetime import datetime, timedelta
from math import isfinite

TPE_OFFSET = timedelta(hours=8)


def classify_tick(timestamp: str, *, delayed_close_verified: bool = False,
                  after_hours_segment: str | None = None) -> str:
    stamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if stamp.tzinfo is None or stamp.utcoffset() != TPE_OFFSET:
        raise ValueError("Taiwan-local +08:00 timezone required")
    if stamp.date().isoformat() < "2020-03-23":
        raise ValueError("session semantics outside supported historical era")
    minute = stamp.hour * 60 + stamp.minute
    if minute == 540 and stamp.second == 0 and stamp.microsecond == 0:
        return "OPENING_AUCTION_CANDIDATE"
    if 540 <= minute < 805:
        return "NORMAL_CONTINUOUS_CANDIDATE"
    if 805 <= minute < 810:
        raise ValueError("closing auction indicative interval is not a trade")
    if minute == 810 and stamp.second == 0 and stamp.microsecond == 0:
        if delayed_close_verified:
            raise ValueError("13:30 cannot be certified as close on a verified delayed-close day")
        return "NORMAL_CLOSE_AUCTION_CANDIDATE"
    if minute == 813 and stamp.second == 0 and stamp.microsecond == 0:
        if not delayed_close_verified:
            raise ValueError("13:33 delayed close needs independent symbol/day verification")
        return "DELAYED_CLOSE_AUCTION_CANDIDATE"
    if minute == 870 and stamp.second == 0 and stamp.microsecond == 0:
        if after_hours_segment not in ("AFTER_HOURS_FIXED_PRICE", "AFTER_HOURS_ODD_LOT"):
            raise ValueError("14:30 market segment must be explicitly verified")
        return after_hours_segment
    raise ValueError("timestamp outside verified normal/after-hours auction points")


def separate_ticks(rows, *, delayed_close_verified=False,
                   after_hours_segment=None):
    """Partition verified-session tick records; never sum cross-session volume.

    `after_hours_segment` applies to all 14:30 records. Mixed 14:30
    board-lot/odd-lot sources must be pre-separated by upstream vendor metadata.
    """
    if not rows:
        raise ValueError("no ticks")
    out = {}
    for row in rows:
        price = float(row["price"])
        vol = float(row["volume_lots"])
        if not (isfinite(price) and price > 0 and isfinite(vol) and vol > 0):
            raise ValueError("invalid tick price or positive traded volume")
        kind = classify_tick(row["timestamp"],
                             delayed_close_verified=delayed_close_verified,
                             after_hours_segment=after_hours_segment)
        out.setdefault(kind, []).append(row)
    if "NORMAL_CLOSE_AUCTION_CANDIDATE" in out and "DELAYED_CLOSE_AUCTION_CANDIDATE" in out:
        raise ValueError("conflicting normal and delayed closing auctions")
    return {"strategy_gate": "BLOCKED", "session_partitions": out,
            "timestamp_semantics": "UNVERIFIED", "execution_status": "NOT_A_FILL"}
