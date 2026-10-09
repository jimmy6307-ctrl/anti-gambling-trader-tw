import unittest
from datetime import date
from tw_pit_exchange_gate import Membership, membership_on, check_observations

URL = "https://www.twse.com.tw/zh/listed/suspend-listing.html"
def mk(code,market,start,end):
    return Membership(code,market,date.fromisoformat(start),date.fromisoformat(end),"COMMON",URL,date(2026,1,16))

class MembershipTests(unittest.TestCase):
    def setUp(self):
        self.intervals=[
            mk("6423","TWSE","2025-10-01","2026-01-22"),
            mk("6423","TPEX","2026-01-22","2026-04-02")]
    def test_transfer_boundary(self):
        self.assertEqual(membership_on("6423",date(2026,1,21),self.intervals).market,"TWSE")
        self.assertEqual(membership_on("6423",date(2026,1,22),self.intervals).market,"TPEX")
    def test_wrong_market_rejected(self):
        with self.assertRaises(ValueError):
            check_observations([dict(date="2026-03-31",stock_id="6423",exchange="TWSE")],self.intervals)
    def test_unknown_security_rejected(self):
        with self.assertRaises(ValueError):
            check_observations([dict(date="2026-03-31",stock_id="2330",exchange="TWSE")],self.intervals)
    def test_duplicate_rejected(self):
        row=dict(date="2025-10-01",stock_id="6423",exchange="TWSE")
        with self.assertRaises(ValueError):
            check_observations([row,row],self.intervals)
    def test_overlapping_rejected(self):
        with self.assertRaises(ValueError):
            check_observations([],self.intervals+[mk("6423","TPEX","2026-01-21","2026-01-23")])

if __name__ == "__main__":
    unittest.main()
