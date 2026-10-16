import unittest
from tw_vendor_amount_volume_gate import classify_amount_volume


class VendorAmountVolumeGateTests(unittest.TestCase):
    def test_shioaji_official_example_consistent_with_lots_only(self):
        x = classify_amount_volume(low=2225, high=2235,
                                   volume=2565, amount=5708965000)
        self.assertEqual(x['classification'], 'LOTS_ONLY_DOCUMENTATION_CONSISTENT')
        self.assertTrue(x['plausible_if_lots'])
        self.assertFalse(x['plausible_if_shares'])
        self.assertEqual(x['strategy_gate'], 'BLOCKED')

    def test_share_unit_example(self):
        x = classify_amount_volume(low=99, high=101, volume=1000, amount=100000)
        self.assertEqual(x['classification'], 'SHARES_ONLY_DOCUMENTATION_CONSISTENT')

    def test_neither_unit_plausible(self):
        x = classify_amount_volume(low=99, high=101, volume=10, amount=50000)
        self.assertEqual(x['classification'], 'NEITHER_PLAUSIBLE_REJECT_UNITS_OR_FIELDS')
        self.assertEqual(x['data_gate'].split('_')[0], 'BLOCKED')

    def test_wide_range_can_leave_both_units_ambiguous(self):
        x = classify_amount_volume(low=1, high=1000, volume=10, amount=10000)
        self.assertEqual(x['classification'], 'BOTH_PLAUSIBLE_UNRESOLVED')
        self.assertEqual(x['strategy_gate'], 'BLOCKED')

    def test_nonstandard_lot_size_explicit(self):
        x = classify_amount_volume(low=99, high=101, volume=10,
                                   amount=50000, lot_size=50)
        self.assertEqual(x['classification'], 'LOTS_ONLY_DOCUMENTATION_CONSISTENT')

    def test_malformed_values_fail_closed(self):
        for field, value in [('low', 'NaN'), ('high', float('inf')),
                             ('volume', 0), ('amount', -10), ('volume', True)]:
            data = dict(low=99, high=101, volume=1000, amount=100000)
            data[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                classify_amount_volume(**data)

    def test_reversed_range_fails(self):
        with self.assertRaisesRegex(ValueError, 'low exceeds high'):
            classify_amount_volume(low=101, high=99, volume=1000, amount=100000)

    def test_invalid_lot_size_fails(self):
        for v in (True, 1, 1000.0):
            with self.subTest(v=v), self.assertRaises(ValueError):
                classify_amount_volume(low=99, high=101, volume=1000,
                                       amount=100000, lot_size=v)


if __name__ == '__main__':
    unittest.main()
