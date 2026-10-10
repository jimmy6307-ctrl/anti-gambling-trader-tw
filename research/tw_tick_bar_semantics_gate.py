"""Fail-closed audit of one-minute candle timestamp conventions against independent trades.

DATA QUALITY ONLY. Even a unique match cannot establish broker execution, full
market coverage, 13:30 auction correctness, or a profitable strategy.

Input contracts are deliberately normalized, not tied to a vendor API:
  bars: [{date: ISO8601 +08:00, open, high, low, close, volume_lots}, ...]
  ticks: [{timestamp: ISO8601 +08:00, price, shares, trade_id, sequence,
           condition: 'REGULAR_BOARD_LOT'}, ...]

Bars must be selected in advance; the tick feed must contain ALL trades for
both candidate intervals around each bar (and source completeness must be
independently established before setting complete_tick_coverage=True).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

TPE = timedelta(hours=8)
ONE_MINUTE = timedelta(minutes=1)


def _time(value):
    if not isinstance(value, str):
        raise ValueError('timestamp must be an ISO8601 string')
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('invalid timestamp') from exc
    if dt.tzinfo is None or dt.utcoffset() != TPE:
        raise ValueError('timestamp must explicitly use +08:00')
    return dt


def _decimal(value):
    if isinstance(value, bool):
        raise ValueError('boolean price/volume')
    try:
        x = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError('invalid numeric') from exc
    if not x.is_finite():
        raise ValueError('nonfinite numeric')
    return x


def _minute(t):
    return t.replace(second=0, microsecond=0)


def _ohlcv(trades):
    if not trades:
        return None
    prices = [x['price'] for x in trades]
    return (prices[0], max(prices), min(prices), prices[-1],
            sum((x['lots'] for x in trades), Decimal(0)))


def audit_tick_bar_semantics(bars, ticks, *, bar_upstream, tick_upstream,
                             complete_tick_coverage=False,
                             min_bars=30, min_days=2):
    """Identify start/end labels ONLY when a unique, exact multi-day match exists.

    `complete_tick_coverage` is an assertion supplied by an independently
    verified feed audit; this function cannot establish tick completeness.
    Exact tick and bar OHLCV equality is intentionally conservative.
    """
    if not bar_upstream or not tick_upstream or bar_upstream == tick_upstream:
        raise ValueError('independent upstream provenance is required')
    if complete_tick_coverage is not True:
        raise ValueError('tick coverage is not independently verified')
    if min_bars < 30 or min_days < 2:
        raise ValueError('minimum audit scope cannot be weakened')
    if not isinstance(bars, list) or not isinstance(ticks, list):
        raise ValueError('bars and ticks must be lists')

    normalized_bars = []
    bar_times = set()
    for row in bars:
        t = _time(row['date'])
        if t.second or t.microsecond or t in bar_times:
            raise ValueError('duplicate or non-minute bar timestamp')
        if not (9 * 60 <= t.hour * 60 + t.minute < 13 * 60 + 25):
            raise ValueError('auction/out-of-session bar in sample')
        bar_times.add(t)
        op, hi, lo, cl, vol = (_decimal(row[k]) for k in
                               ('open', 'high', 'low', 'close', 'volume_lots'))
        if not (0 < lo <= min(op, cl) <= max(op, cl) <= hi and vol > 0):
            raise ValueError('invalid bar OHLCV')
        normalized_bars.append((t, (op, hi, lo, cl, vol)))
    if len(normalized_bars) < min_bars or len({t.date() for t, _ in normalized_bars}) < min_days:
        raise ValueError('insufficient predeclared multi-day bar sample')

    normalized_ticks = []
    ids = set()
    sequences = set()
    for row in ticks:
        t = _time(row['timestamp'])
        if not (9 * 60 <= t.hour * 60 + t.minute < 13 * 60 + 25):
            raise ValueError('auction/out-of-session tick in sample')
        if row.get('condition') != 'REGULAR_BOARD_LOT':
            raise ValueError('non-regular or unclassified trade')
        trade_id = (t.date(), str(row['trade_id']))
        if trade_id in ids:
            raise ValueError('duplicate trade id')
        ids.add(trade_id)
        seq = row.get('sequence')
        if isinstance(seq, bool) or not isinstance(seq, int) or seq < 0:
            raise ValueError('missing or invalid tick sequence')
        seq_id = (t.date(), seq)
        if seq_id in sequences:
            raise ValueError('duplicate tick sequence')
        sequences.add(seq_id)
        px, shares = _decimal(row['price']), _decimal(row['shares'])
        if px <= 0 or shares <= 0 or shares % 1000:
            raise ValueError('invalid board-lot tick')
        normalized_ticks.append({'timestamp': t, 'price': px,
                                 'lots': shares / 1000, 'trade_id': str(row['trade_id']),
                                 'sequence': seq})
    normalized_ticks.sort(key=lambda x: (x['timestamp'], x['sequence']))

    start_bins, end_bins = defaultdict(list), defaultdict(list)
    for tick in normalized_ticks:
        t = tick['timestamp']
        start_bins[_minute(t)].append(tick)
        # End-labeled candle covers (label-1m, label]. A trade exactly
        # at the minute boundary belongs to the bar ending at that time.
        end_label = _minute(t) if t == _minute(t) else _minute(t) + ONE_MINUTE
        end_bins[end_label].append(tick)

    scores = {}
    for name, bins in (('START', start_bins), ('END', end_bins)):
        matches = [expected == _ohlcv(bins.get(t, [])) for t, expected in normalized_bars]
        scores[name] = {'matched': sum(matches), 'total': len(matches)}
    winners = [name for name, s in scores.items() if s['matched'] == s['total']]
    if len(winners) != 1:
        raise ValueError('timestamp semantics ambiguous or mismatched: ' + str(scores))
    return {
        'status': 'UNIQUE_TICK_BAR_LABEL_MATCH_ONLY',
        'label_semantics_supported': winners[0],
        'strategy_gate': 'BLOCKED',
        'independent_upstream_claims': [bar_upstream, tick_upstream],
        'complete_tick_coverage_asserted_not_proven_here': True,
        'matched_bars': len(normalized_bars),
        'matched_days': len({t.date() for t, _ in normalized_bars}),
        'scores': scores,
        'not_a_broker_fill': True,
    }
