"""Offline tests for marketwide official TWSE data-quality parser."""
import unittest
from tw_marketwide_daily_gate import parse_mi, parse_stock_day

FIELDS = ["證券代號", "證券名稱", "成交股數", "成交筆數", "成交金額", "開盤價", "最高價", "最低價", "收盤價"]


class TestMarketwideOfficial(unittest.TestCase):
    def payload(self):
        return {"stat": "OK", "tables": [{"title": "115年03月31日每日收盤行情(全部)",
                "fields": list(FIELDS), "data": [
                ["2330", "台積電", "1,000", "5", "1,760,000", "1750", "1770", "1740", "1760"],
                ["2317", "鴻海", "200", "2", "40,000", "200", "205", "195", "200"],
                ["0050", "ETF", "10", "1", "100", "10", "10", "10", "10"],
                ["2881", "富邦金", "0", "0", "0", "--", "--", "--", "--"]]}]}

    def test_filter_and_prices(self):
        rows, skipped = parse_mi(self.payload(), "2026-03-31")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]["close"], 1760)
        self.assertEqual(skipped, {"non_equity_code_shape": 1, "no_trade": 1})

    def test_date_mismatch(self):
        with self.assertRaisesRegex(ValueError, "different trade date"):
            parse_mi(self.payload(), "2026-03-30")

    def test_schema_drift(self):
        p = self.payload()
        p["tables"][0]["fields"][8] = "無關欄位"
        with self.assertRaisesRegex(ValueError, "schema drift"):
            parse_mi(p, "2026-03-31")

    def test_duplicate_stock(self):
        p = self.payload()
        p["tables"][0]["data"].append(p["tables"][0]["data"][0])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            parse_mi(p, "2026-03-31")

    def test_anchor(self):
        p = {"stat": "OK", "data": [["115/03/31", "1", "2", "1750", "1770", "1740", "1760", "-", "1"]]}
        self.assertEqual(parse_stock_day(p, "2026-03-31")["close"], 1760)
        with self.assertRaisesRegex(ValueError, "missing"):
            parse_stock_day(p, "2026-03-30")


if __name__ == "__main__":
    unittest.main()
