"""Fail-closed Taiwan stock minute/auction and indicative next-bar execution gate.

Pure data-contract audit; passing an anchor is NOT a verified fill or strategy edge.
The vendor's bar-start convention must be independently verified from ticks.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from math import isfinite

TPE_OFFSET = timedelta(hours=8)


def _number(value):
    if isinstance(value, bool):
        raise ValueError("boolean is not numeric")
    n = float(value)
    if not isfinite(n):
        raise ValueError("nonfinite numeric")
    return n


def validate_minute_auction(payload, symbol, target_day, official_close, exchange="TWSE"):
    """Validate vendor schema, continuous-session bars, and 13:30 auction anchor.

    This does not establish timestamp semantics or any executable trade.
    """
    day = date.fromisoformat(target_day)
    if payload.get("symbol") != symbol or str(payload.get("timeframe")) != "1":
        raise ValueError("wrong vendor symbol/timeframe")
    if payload.get("exchange") != exchange or exchange not in ("TWSE", "TPEx"):
        raise ValueError("missing or wrong exchange")
    if payload.get("type") not in (None, "EQUITY"):
        raise ValueError("non-equity security type")
    if payload.get("adjusted") is True:
        raise ValueError("minute data must be unadjusted")
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        raise ValueError("missing vendor minute bars")
    seen = set()
    bars = []
    for row in data:
        stamp = datetime.fromisoformat(row["date"].replace("Z", "+00:00"))
        if stamp.tzinfo is None or stamp.utcoffset() != TPE_OFFSET:
            raise ValueError("missing or wrong +08:00 timezone")
        if stamp.date() != day or stamp.second or stamp.microsecond:
            raise ValueError("wrong date or non-minute timestamp")
        if stamp in seen:
            raise ValueError("duplicate minute timestamp")
        seen.add(stamp)
        hhmm = stamp.hour * 60 + stamp.minute
        if not 540 <= hhmm <= 810:
            raise ValueError("minute outside normal trading session")
        if 805 <= hhmm < 810:
            raise ValueError("bar inside 13:25-13:30 closing call auction")
        op, hi, lo, cl, vol = (_number(row[k]) for k in
                                ("open", "high", "low", "close", "volume"))
        if not (0 < lo <= min(op, cl) <= max(op, cl) <= hi and vol >= 0):
            raise ValueError("impossible OHLCV")
        bars.append({"timestamp": stamp, "open": op, "high": hi,
                     "low": lo, "close": cl, "volume_lots": vol})
    bars.sort(key=lambda b: b["timestamp"])
    auction = [b for b in bars if b["timestamp"].hour == 13 and
               b["timestamp"].minute == 30]
    continuous = [b for b in bars if b not in auction]
    if len(auction) != 1 or auction[0]["volume_lots"] <= 0:
        raise ValueError("missing or zero-volume 13:30 auction print")
    if not continuous or not any(b["volume_lots"] > 0 for b in continuous):
        raise ValueError("no continuous-session trades")
    a = auction[0]
    if not (a["open"] == a["high"] == a["low"] == a["close"]):
        raise ValueError("13:30 must be a single-price auction point")
    if a["close"] != _number(official_close):
        raise ValueError("vendor 13:30 does not match official close")
    return {
        "status": "ANCHOR_MATCH_ONLY", "strategy_gate": "BLOCKED",
        "timestamp_semantics": "UNVERIFIED_NEEDS_INDEPENDENT_TICKS",
        "auction_close": a["close"], "auction_volume_lots": a["volume_lots"],
        "continuous_bars": len(continuous),
        "continuous_volume_lots": sum(b["volume_lots"] for b in continuous),
        "bars": bars,
    }


def indicative_next_bar(audit, signal_bar_time, *, bar_start_proven,
                        shares, available_cash, open_positions, max_positions,
                        upper_limit, buy_fee_rate=0.001425, slippage_rate=0.0005):
    """Return an *indicative-only* next-minute print, NEVER an assumed fill.

    Participation in the next bar is ex-post diagnostic, not a fill criterion.
    """
    if audit.get("status") != "ANCHOR_MATCH_ONLY":
        raise ValueError("minute/auction audit has not passed")
    if not bar_start_proven:
        raise ValueError("vendor bar-start semantics unverified against ticks")
    if not isinstance(shares, int) or shares <= 0 or shares % 1000:
        raise ValueError("board-lot shares must be positive multiples of 1000")
    if not 0 <= open_positions < max_positions:
        raise ValueError("portfolio position limit reached")
    if not isfinite(available_cash) or available_cash <= 0:
        raise ValueError("insufficient or invalid cash")
    if upper_limit is None or _number(upper_limit) <= 0:
        raise ValueError("exchange daily upper price limit unavailable")
    signal = datetime.fromisoformat(signal_bar_time)
    if signal.tzinfo is None or signal.utcoffset() != TPE_OFFSET:
        raise ValueError("signal timezone unknown")
    bars = audit["bars"]
    if signal not in {b["timestamp"] for b in bars}:
        raise ValueError("signal bar absent")
    if signal.hour * 60 + signal.minute >= 805:
        raise ValueError("signal not from continuous session")
    observed_at = signal + timedelta(minutes=1)
    # A bar opening exactly when the signal becomes observable has an open
    # print that may precede order computation, transmission and queueing.
    # Even for an indicative simulation, never treat that same-minute open
    # as an executable post-signal price. Require a strictly later bar.
    candidates = [b for b in bars if observed_at < b["timestamp"] and
                  b["timestamp"].hour * 60 + b["timestamp"].minute < 805 and
                  b["volume_lots"] > 0]
    if not candidates:
        raise ValueError("no subsequent tradable continuous-session print")
    b = candidates[0]
    if b["open"] >= _number(upper_limit):
        raise ValueError("at upper limit; buy execution unproven")
    if not (0 <= slippage_rate < 1 and 0 <= buy_fee_rate < 1):
        raise ValueError("invalid cost assumptions")
    indicative_price = b["open"] * (1 + slippage_rate)
    if indicative_price >= _number(upper_limit):
        raise ValueError("indicative buy reaches upper limit; execution unproven")
    cash_reserved = shares * indicative_price * (1 + buy_fee_rate)
    if cash_reserved > available_cash:
        raise ValueError("not enough cash to reserve buy and fees")
    return {
        "status": "INDICATIVE_ONLY_NOT_A_PROVEN_FILL",
        "signal_observed_at": observed_at.isoformat(),
        "next_available_bar": b["timestamp"].isoformat(),
        "indicative_buy_price": round(indicative_price, 6),
        "cash_reserved": round(cash_reserved, 2),
        "ex_post_participation_ratio": shares / (b["volume_lots"] * 1000),
        "ex_post_participation_is_not_fill_proof": True,
    }
