"""Synthetic fail-closed tests for independent tick-to-one-minute-bar label audit.

These tests NEVER authenticate an upstream, establish tick completeness, or
validate actual fills.  Passing them must not unblock strategy backtests.
"""
import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from tw_tick_bar_semantics_gate import audit_tick_bar_semantics


def fixture(mode="START"):
    bars, ticks = [], []
    for day_i, day in enumerate(("2026-09-01", "2026-09-02")):
        base = datetime.fromisoformat(day + "T09:10:00+08:00")
        for i in range(15):
            label = base + timedelta(minutes=i)
            if mode == "START":
                trade_time = label + timedelta(seconds=10)
            elif mode == "END":
                trade_time = label - timedelta(seconds=30)
            elif mode == "END_BOUNDARY":
                # A trade exactly at L-1m belongs to the END candle L.
                trade_time = label - timedelta(minutes=1)
            else:  # Exact boundary at L matches START L, not END L.
                trade_time = label
            px = Decimal(100 + day_i * 5) + Decimal(i) / 10
            bars.append(dict(date=label.isoformat(), open=str(px),
                             high=str(px), low=str(px), close=str(px),
                             volume_lots="1"))
            ticks.append(dict(timestamp=trade_time.isoformat(),
                              price=str(px), shares=1000,
                              trade_id=f"trade-{i}", sequence=i,
                              condition="REGULAR_BOARD_LOT"))
    return bars, ticks


def run(bars, ticks, **kwargs):
    return audit_tick_bar_semantics(
        bars, ticks, bar_upstream="independent_vendor_A",
        tick_upstream="independent_vendor_B",
        complete_tick_coverage=True, **kwargs)


class TickBarSemanticsContractTests(unittest.TestCase):
    def test_unique_start_label_on_two_days(self):
        b, t = fixture("START")
        out = run(b, t)
        self.assertEqual(out["label_semantics_supported"], "START")
        self.assertEqual(out["matched_bars"], 30)
        self.assertEqual(out["matched_days"], 2)
        self.assertEqual(out["strategy_gate"], "BLOCKED")
        self.assertTrue(out["not_a_broker_fill"])

    def test_unique_end_label_on_two_days(self):
        b, t = fixture("END")
        out = run(b, t)
        self.assertEqual(out["label_semantics_supported"], "END")
        self.assertEqual(out["scores"]["END"]["matched"], 30)

    def test_exact_boundary_belongs_to_start_label(self):
        b, t = fixture("BOUNDARY")
        out = run(b, t)
        self.assertEqual(out["label_semantics_supported"], "START")
        self.assertEqual(out["scores"]["START"]["matched"], 30)
        self.assertLess(out["scores"]["END"]["matched"], 30)

    def test_exact_boundary_belongs_to_next_end_label(self):
        b, t = fixture("END_BOUNDARY")
        out = run(b, t)
        self.assertEqual(out["label_semantics_supported"], "END")
        self.assertEqual(out["scores"]["END"]["matched"], 30)
        self.assertLess(out["scores"]["START"]["matched"], 30)

    def test_missing_trade_rejects(self):
        b, t = fixture("START")
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            run(b, t[:-1])

    def test_unverified_completeness_rejects(self):
        b, t = fixture()
        with self.assertRaisesRegex(ValueError, "coverage"):
            audit_tick_bar_semantics(b, t, bar_upstream="A",
                                     tick_upstream="B",
                                     complete_tick_coverage=False)

    def test_same_upstream_rejects(self):
        b, t = fixture()
        with self.assertRaisesRegex(ValueError, "independent"):
            audit_tick_bar_semantics(b, t, bar_upstream="A",
                                     tick_upstream="A",
                                     complete_tick_coverage=True)

    def test_duplicate_bar_rejects(self):
        b, t = fixture()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            run(b + [dict(b[0])], t)

    def test_auction_bar_rejects(self):
        b, t = fixture()
        b[0]["date"] = "2026-09-01T09:00:00+08:00"
        with self.assertRaisesRegex(ValueError, "auction"):
            run(b, t)

    def test_nonregular_trade_rejects(self):
        b, t = fixture()
        t[0]["condition"] = "ODD_LOT"
        with self.assertRaisesRegex(ValueError, "non-regular"):
            run(b, t)

    def test_non_board_lot_shares_rejects(self):
        b, t = fixture()
        t[0]["shares"] = 999
        with self.assertRaisesRegex(ValueError, "board-lot"):
            run(b, t)

    def test_single_day_rejects_even_if_thirty_bars(self):
        b, t = fixture()
        with self.assertRaisesRegex(ValueError, "insufficient"):
            run(b[:15], t[:15])


if __name__ == "__main__":
    unittest.main()
