import unittest
from tw_independent_minute_probe import official_close, inspect_fugle

class TestSourceAudit(unittest.TestCase):
    def test_official_close(self):
        p = {'stat':'OK','data':[['115/03/31','1','1','1760','1760','1760','1760','0','1']]}
        self.assertEqual(official_close(p, '2026-03-31'), 1760)

    def test_minute_bar(self):
        p = {'symbol':'2330','timeframe':'1','data':[{'date':'2026-03-31T13:30:00+08:00','open':1760,'high':1760,'low':1760,'close':1760,'volume':1}]}
        self.assertEqual(inspect_fugle(p, '2330', '2026-03-31')['close_at_1330'], 1760)
        with self.assertRaises(ValueError):
            inspect_fugle({**p, 'data':p['data']*2}, '2330', '2026-03-31')

if __name__ == '__main__':
    unittest.main()
