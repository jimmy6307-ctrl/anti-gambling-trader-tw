import unittest
from tw_independent_minute_probe import official_close, inspect_fugle


def sample():
    return {
        "symbol": "2330", "type": "EQUITY", "exchange": "TWSE",
        "timeframe": "1", "data": [
            {"date": "2026-03-31T09:35:00+08:00", "open": 1759, "high": 1760,
             "low": 1759, "close": 1760, "volume": 3},
            {"date": "2026-03-31T13:30:00+08:00", "open": 1760, "high": 1760,
             "low": 1760, "close": 1760, "volume": 1},
        ],
    }


class TestSourceAudit(unittest.TestCase):
    def test_official_close(self):
        p = {"stat": "OK", "data": [["115/03/31", "1", "1", "1760", "1760", "1760", "1760", "0", "1"]]}
        self.assertEqual(official_close(p, "2026-03-31"), 1760)

    def test_minute_bar(self):
        p = sample()
        self.assertEqual(inspect_fugle(p, "2330", "2026-03-31")["close_at_1330"], 1760)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            inspect_fugle({**p, "data": p["data"] * 2}, "2330", "2026-03-31")

    def test_missing_exchange_rejected(self):
        p = sample()
        del p["exchange"]
        with self.assertRaisesRegex(ValueError, "exchange"):
            inspect_fugle(p, "2330", "2026-03-31")

    def test_zero_volume_auction_rejected(self):
        p = sample()
        p["data"][1]["volume"] = 0
        with self.assertRaisesRegex(ValueError, "13:30"):
            inspect_fugle(p, "2330", "2026-03-31")

    def test_non_point_auction_rejected(self):
        p = sample()
        p["data"][1]["high"] = 1761
        with self.assertRaisesRegex(ValueError, "single-price"):
            inspect_fugle(p, "2330", "2026-03-31")

    def test_no_continuous_trades_rejected(self):
        p = sample()
        p["data"][0]["volume"] = 0
        with self.assertRaisesRegex(ValueError, "continuous"):
            inspect_fugle(p, "2330", "2026-03-31")

    def test_wrong_timezone_rejected(self):
        p = sample()
        p["data"][0]["date"] = "2026-03-31T01:35:00Z"
        with self.assertRaisesRegex(ValueError, "08:00"):
            inspect_fugle(p, "2330", "2026-03-31")

    def test_auction_indicative_interval_rejected(self):
        p = sample()
        p["data"].insert(1, {"date": "2026-03-31T13:27:00+08:00",
                             "open": 1760, "high": 1760, "low": 1760,
                             "close": 1760, "volume": 1})
        with self.assertRaisesRegex(ValueError, "session"):
            inspect_fugle(p, "2330", "2026-03-31")


if __name__ == "__main__":
    unittest.main()
