#!/usr/bin/env python3
"""Fail-closed historical TWSE/TPEx membership reconciliation (DATA QA ONLY).

Do not infer membership from today's symbol list or from four-digit codes.
Events are effective on their first trading day; prior market is exclusive then.
This validator only checks supplied *bounded, verified* intervals. A missing
observation is NOT evidence of suspension/delisting; a matched row is NOT proof
of common-share security type or actual tradeability.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

MARKETS = frozenset({"TWSE", "TPEX"})
TYPES = frozenset({"COMMON", "ETF", "ETN", "PREFERRED", "OTHER"})


@dataclass(frozen=True)
class Membership:
    stock_id: str
    market: str
    start: date  # inclusive, verified market membership effective date
    end: date  # exclusive; never infer membership outside this bound
    security_type: str
    source_url: str
    evidence_published: date

    def __post_init__(self):
        if not re.fullmatch(r"[1-9][0-9]{3}", self.stock_id):
            raise ValueError("invalid 4-digit code; 4 digits alone do not prove common stock")
        if self.market not in MARKETS or self.security_type not in TYPES:
            raise ValueError("unknown exchange/security type")
        if not (self.start < self.end):
            raise ValueError("membership interval must be nonempty [start,end)")
        if not self.source_url.startswith("https://"):
            raise ValueError("verified source URL required")
        if self.evidence_published > self.end:
            raise ValueError("evidence published after entire interval; investigate")


def validate_intervals(memberships: list[Membership]) -> None:
    by_code: dict[str, list[Membership]] = {}
    for m in memberships:
        by_code.setdefault(m.stock_id, []).append(m)
    for code, periods in by_code.items():
        periods.sort(key=lambda m: (m.start, m.end))
        for a, b in zip(periods, periods[1:]):
            if b.start < a.end:
                raise ValueError(f"overlapping market memberships for {code}: {a.market}/{b.market}")


def membership_on(stock_id: str, day: date, periods: list[Membership]) -> Membership:
    matches = [m for m in periods if m.stock_id == stock_id and m.start <= day < m.end]
    if len(matches) != 1:
        raise ValueError(f"{stock_id} {day}: no unique verified market membership")
    return matches[0]


def check_observations(rows: list[dict], periods: list[Membership], *, strict_coverage: bool = True) -> dict:
    """Reconcile historical daily observations to dated membership evidence.

    strict_coverage=True blocks any row without verified market and security type.
    An observed market match never means a non-observed day was a suspension.
    """
    validate_intervals(periods)
    seen = set()
    matched = 0
    missing = []
    non_common = 0
    for row in rows:
        day = date.fromisoformat(str(row["date"]))
        code = str(row["stock_id"])
        exchange = str(row["exchange"]).upper()
        key = (day, exchange, code)
        if key in seen:
            raise ValueError(f"duplicate market-date-security {key}")
        seen.add(key)
        if exchange not in MARKETS:
            raise ValueError(f"invalid exchange {exchange}")
        try:
            m = membership_on(code, day, periods)
        except ValueError:
            missing.append(key)
            continue
        if exchange != m.market:
            raise ValueError(f"{code} {day}: observed {exchange}, verified {m.market}")
        if m.security_type != "COMMON":
            non_common += 1
        matched += 1
    if strict_coverage and missing:
        raise ValueError(f"{len(missing)} observations lack PIT evidence; first={missing[0]}")
    return {"matched": matched, "unverified": len(missing),
            "excluded_non_common": non_common,
            "certification": "DATA_ONLY_NOT_TRADABILITY_OR_EDGE"}


def load_observations_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not {"date", "exchange", "stock_id"}.issubset(reader.fieldnames or []):
            raise ValueError("daily CSV requires date, exchange, stock_id")
        return list(reader)
