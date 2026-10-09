import json, unittest
from tw_tpex_individual_anchor_gate import parse_monthly, number
DAY="2026-10-07"; SID="6488"
ROW=["115/10/07","1,000","100,000","429","432","428","430","+1","30"]
def raw(rows,**kw): return json.dumps({"aaData":rows,**kw}).encode()
class Tests(unittest.TestCase):
    def test_good(self): self.assertEqual(parse_monthly(raw([ROW]),DAY,SID)["close"],number("430"))
    def test_date(self):
        with self.assertRaises(ValueError):parse_monthly(raw([ROW]),"2026-10-08",SID)
    def test_duplicate(self):
        with self.assertRaises(ValueError):parse_monthly(raw([ROW,ROW]),DAY,SID)
    def test_stock(self):
        with self.assertRaises(ValueError):parse_monthly(raw([ROW],stkNo="8299"),DAY,SID)
    def test_schema(self):
        with self.assertRaises(ValueError):parse_monthly(raw([ROW[:5]]),DAY,SID)
    def test_bad_price(self):
        x=ROW.copy();x[6]="500"
        with self.assertRaises(ValueError):parse_monthly(raw([x]),DAY,SID)
    def test_html(self):
        x=ROW.copy();x[6]="<span>430</span>"
        self.assertEqual(parse_monthly(raw([x]),DAY,SID)["close"],number("430"))
    def test_nonfinite(self):
        with self.assertRaises(ValueError):number("NaN")
if __name__=="__main__":unittest.main()
