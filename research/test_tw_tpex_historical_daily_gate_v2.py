import unittest
from tw_tpex_historical_daily_gate_v2 import parse

D="2026-10-07"
CSV="""115年10月07日 上櫃股票每日收盤行情(不含定價)
代號,名稱,收盤,開盤,最高,最低,成交股數,成交金額(元),成交筆數
6488,環球晶,430,429,432,428,"1,234",543210,89
8299,群聯,600,598,602,597,500,299999,10
"""
HTML="""<h2>115/10/07 上櫃股票每日收盤行情</h2><table><tr><th>代號</th><th>名稱</th><th>收盤</th><th>開盤</th><th>最高</th><th>最低</th><th>成交股數</th><th>成交金額(元)</th><th>成交筆數</th></tr><tr><td>6488</td><td>環球晶</td><td>430</td><td>429</td><td>432</td><td>428</td><td>1234</td><td>543210</td><td>89</td></tr></table>"""
class GateTests(unittest.TestCase):
    def test_csv(self): self.assertEqual(len(parse(CSV.encode(),D)[0]),2)
    def test_html(self): self.assertEqual(len(parse(HTML.encode(),D)[0]),1)
    def test_bom(self): self.assertEqual(len(parse(CSV.encode("utf-8-sig"),D)[0]),2)
    def test_date(self):
        with self.assertRaises(ValueError):parse(CSV.encode(),"2026-10-08")
    def test_missing_date(self):
        with self.assertRaises(ValueError):parse(CSV.split("\n",1)[1].encode(),D)
    def test_schema(self):
        with self.assertRaises(ValueError):parse(CSV.replace("最高","未知").encode(),D)
    def test_duplicate(self):
        with self.assertRaises(ValueError):parse((CSV+CSV.splitlines()[-1]+"\n").encode(),D)
    def test_bad_ohlc(self):
        with self.assertRaises(ValueError):parse(CSV.replace("430,429,432,428","450,429,432,428").encode(),D)
    def test_no_trade(self):
        rows,skips=parse((CSV+"9999,無成交,-,-,-,-,-,-,-\n").encode(),D)
        self.assertEqual(len(rows),2);self.assertEqual(skips["no_trade"],1)
    def test_activity(self):
        with self.assertRaises(ValueError):parse(CSV.replace("543210,89","0,89").encode(),D)
if __name__=="__main__":unittest.main()
