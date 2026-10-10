import unittest
from tw_shioaji_timestamp_gate import inspect_epoch_vs_displayed


class ShioajiTimestampGateTests(unittest.TestCase):
    def test_official_docs_tick_example_is_eight_hours_ambiguous(self):
        x = inspect_epoch_vs_displayed(1779094808306075000, '2026-05-18 09:00:08.306075')
        self.assertEqual(x['status'], 'EIGHT_HOUR_AMBIGUITY_OR_DOCUMENTATION_MISMATCH')
        self.assertEqual(x['taipei_clock'], '2026-05-18T17:00:08.306075+08:00')
        self.assertEqual(x['strategy_gate'], 'BLOCKED')

    def test_official_docs_kbar_example_is_also_ambiguous(self):
        x = inspect_epoch_vs_displayed(1779094860000000000, '2026-05-18 09:01:00')
        self.assertEqual(x['status'], 'EIGHT_HOUR_AMBIGUITY_OR_DOCUMENTATION_MISMATCH')

    def test_true_utc_epoch_for_taipei_nine_am_is_consistent(self):
        x = inspect_epoch_vs_displayed(1779066008306075000, '2026-05-18 09:00:08.306075')
        self.assertEqual(x['status'], 'CONSISTENT_WITH_TRUE_UTC_EPOCH')
        self.assertEqual(x['strategy_gate'], 'BLOCKED')

    def test_unreconciled_clock_blocks(self):
        x = inspect_epoch_vs_displayed(1779094808306075000, '2026-05-18 11:00:08.306075')
        self.assertEqual(x['status'], 'UNRECONCILED_CLOCK')

    def test_bad_timestamp_type_rejected(self):
        for value in (True, 1779094808, 1779094808306075000.0):
            with self.subTest(value=value), self.assertRaises(ValueError):
                inspect_epoch_vs_displayed(value, '2026-05-18 09:00:08.306075')

    def test_aware_displayed_clock_rejected(self):
        with self.assertRaises(ValueError):
            inspect_epoch_vs_displayed(1779094808306075000, '2026-05-18T09:00:08+08:00')


if __name__ == '__main__':
    unittest.main()
