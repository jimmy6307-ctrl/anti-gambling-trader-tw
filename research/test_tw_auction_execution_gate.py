import copy
import unittest
from tw_auction_execution_gate import validate_minute_auction, indicative_next_bar


def sample():
    return {"symbol":"2330","type":"EQUITY","exchange":"TWSE","timeframe":"1",
            "data":[
                {"date":"2026-04-23T09:35:00+08:00","open":2080,"high":2082,"low":2079,"close":2081,"volume":80},
                {"date":"2026-04-23T09:36:00+08:00","open":2081,"high":2083,"low":2080,"close":2082,"volume":20},
                {"date":"2026-04-23T13:24:00+08:00","open":2090,"high":2090,"low":2085,"close":2090,"volume":104},
                {"date":"2026-04-23T13:30:00+08:00","open":2080,"high":2080,"low":2080,"close":2080,"volume":5330},
            ]}


class TestGate(unittest.TestCase):
    def gate(self,p=None):
        return validate_minute_auction(sample() if p is None else p,"2330","2026-04-23",2080)

    def test_anchor_only(self):
        g=self.gate();self.assertEqual(g["status"],"ANCHOR_MATCH_ONLY")
        self.assertEqual(g["strategy_gate"],"BLOCKED")
        self.assertEqual(g["auction_volume_lots"],5330)

    def test_wrong_exchange(self):
        p=sample();p["exchange"]="TPEx"
        with self.assertRaisesRegex(ValueError,"exchange"):self.gate(p)

    def test_wrong_security_type(self):
        p=sample();p["type"]="ETF"
        with self.assertRaisesRegex(ValueError,"non-equity"):self.gate(p)

    def test_missing_auction(self):
        p=sample();p["data"].pop()
        with self.assertRaisesRegex(ValueError,"auction print"):self.gate(p)

    def test_zero_volume_auction(self):
        p=sample();p["data"][-1]["volume"]=0
        with self.assertRaisesRegex(ValueError,"auction print"):self.gate(p)

    def test_close_mismatch(self):
        p=sample();p["data"][-1].update(open=2075,high=2075,low=2075,close=2075)
        with self.assertRaisesRegex(ValueError,"official close"):self.gate(p)

    def test_auction_nonpoint(self):
        p=sample();p["data"][-1]["high"]=2085
        with self.assertRaisesRegex(ValueError,"single-price"):self.gate(p)

    def test_duplicate_timestamp(self):
        p=sample();p["data"].append(copy.deepcopy(p["data"][0]))
        with self.assertRaisesRegex(ValueError,"duplicate"):self.gate(p)

    def test_no_timezone(self):
        p=sample();p["data"][0]["date"]="2026-04-23T09:35:00"
        with self.assertRaisesRegex(ValueError,"timezone"):self.gate(p)

    def test_no_1327_bar(self):
        p=sample();p["data"][2]["date"]="2026-04-23T13:27:00+08:00"
        with self.assertRaisesRegex(ValueError,"call auction"):self.gate(p)

    def test_bad_ohlc(self):
        p=sample();p["data"][0]["low"]=2084
        with self.assertRaisesRegex(ValueError,"OHLCV"):self.gate(p)

    def test_requires_proven_bar_semantics(self):
        with self.assertRaisesRegex(ValueError,"semantics"):
            indicative_next_bar(self.gate(),"2026-04-23T09:35:00+08:00",
                                bar_start_proven=False,shares=1000,available_cash=3000000,
                                open_positions=0,max_positions=2,upper_limit=2200)

    def test_next_bar_indicative_only(self):
        r=indicative_next_bar(self.gate(),"2026-04-23T09:35:00+08:00",
                             bar_start_proven=True,shares=1000,available_cash=3000000,
                             open_positions=0,max_positions=2,upper_limit=2200)
        self.assertEqual(r["next_available_bar"],"2026-04-23T09:36:00+08:00")
        self.assertEqual(r["status"],"INDICATIVE_ONLY_NOT_A_PROVEN_FILL")
        self.assertTrue(r["ex_post_participation_is_not_fill_proof"])

    def test_no_cash(self):
        with self.assertRaisesRegex(ValueError,"cash"):
            indicative_next_bar(self.gate(),"2026-04-23T09:35:00+08:00",
                                bar_start_proven=True,shares=1000,available_cash=1000,
                                open_positions=0,max_positions=2,upper_limit=2200)

    def test_no_room(self):
        with self.assertRaisesRegex(ValueError,"position limit"):
            indicative_next_bar(self.gate(),"2026-04-23T09:35:00+08:00",
                                bar_start_proven=True,shares=1000,available_cash=3000000,
                                open_positions=2,max_positions=2,upper_limit=2200)

    def test_upper_limit(self):
        with self.assertRaisesRegex(ValueError,"upper limit"):
            indicative_next_bar(self.gate(),"2026-04-23T09:35:00+08:00",
                                bar_start_proven=True,shares=1000,available_cash=3000000,
                                open_positions=0,max_positions=2,upper_limit=2081)

    def test_missing_price_limit(self):
        with self.assertRaisesRegex(ValueError,"upper price limit"):
            indicative_next_bar(self.gate(),"2026-04-23T09:35:00+08:00",
                                bar_start_proven=True,shares=1000,available_cash=3000000,
                                open_positions=0,max_positions=2,upper_limit=None)


if __name__=='__main__':unittest.main()
