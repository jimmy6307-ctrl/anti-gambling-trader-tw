#!/usr/bin/env python3
"""Dated, SOURCE-BOUNDED 5236 market-membership evidence; DATA QA ONLY.

Official TPEx notices:
* 2021-07-28: common shares began TPEx trading on 2021-07-29.
* 2026-07-14: common shares cease TPEx trading on 2026-07-16,
  and begin TWSE trading on the SAME day.

The later TWSE interval is conservatively bounded at 2026-10-08
(exclusive), using the independently audited 2026-10-07 TWSE MI_INDEX
snapshot. Dates outside these bounds remain UNKNOWN. A retrospective
membership reconstruction is NOT a signal available to traders in advance.
"""
from datetime import date
from tw_pit_exchange_gate import Membership, check_observations, membership_on

TPEX_INITIAL = "https://www.tpex.org.tw/storage/eb_data/11007/11000075301.html"
TPEX_TRANSFER = "https://www.tpex.org.tw/storage/eb_data/11507/11500666361.html"

def verified_5236_membership():
    return [
        Membership("5236", "TPEX", date(2021, 7, 29), date(2026, 7, 16),
                   "COMMON", TPEX_INITIAL, date(2021, 7, 28)),
        Membership("5236", "TWSE", date(2026, 7, 16), date(2026, 10, 8),
                   "COMMON", TPEX_TRANSFER, date(2026, 7, 14)),
    ]

def check_5236_samples():
    periods = verified_5236_membership()
    sample = [
        {"date": "2024-08-05", "exchange": "TPEX", "stock_id": "5236"},
        {"date": "2025-10-01", "exchange": "TPEX", "stock_id": "5236"},
        {"date": "2026-03-31", "exchange": "TPEX", "stock_id": "5236"},
        {"date": "2026-10-07", "exchange": "TWSE", "stock_id": "5236"},
    ]
    return check_observations(sample, periods)

if __name__ == "__main__":
    print(check_5236_samples())
