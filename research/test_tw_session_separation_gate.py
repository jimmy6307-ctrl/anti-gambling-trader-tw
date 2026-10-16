import unittest
from tw_session_separation_gate import classify_tick, separate_ticks


class TestSessionSeparation(unittest.TestCase):
    def test_normal_auction(self):
        self.assertEqual(classify_tick('2026-10-08T13:30:00+08:00'), 'NORMAL_CLOSE_AUCTION_CANDIDATE')

    def test_opening(self):
        self.assertEqual(classify_tick('2026-10-08T09:00:00+08:00'), 'OPENING_AUCTION_CANDIDATE')

    def test_early_trade(self):
        self.assertEqual(classify_tick('2026-10-08T09:35:21+08:00'), 'NORMAL_CONTINUOUS_CANDIDATE')

    def test_auction_window(self):
        with self.assertRaisesRegex(ValueError, 'indicative'):
            classify_tick('2026-10-08T13:27:00+08:00')

    def test_delayed_close_unverified(self):
        with self.assertRaisesRegex(ValueError, 'verification'):
            classify_tick('2026-10-08T13:33:00+08:00')

    def test_delayed_close_verified(self):
        self.assertEqual(classify_tick('2026-10-08T13:33:00+08:00', delayed_close_verified=True),
                         'DELAYED_CLOSE_AUCTION_CANDIDATE')

    def test_no_1330_on_delayed_day(self):
        with self.assertRaisesRegex(ValueError, 'cannot be certified'):
            classify_tick('2026-10-08T13:30:00+08:00', delayed_close_verified=True)

    def test_afterhours_requires_segment(self):
        with self.assertRaisesRegex(ValueError, 'segment'):
            classify_tick('2026-10-08T14:30:00+08:00')

    def test_afterhours_boardlot(self):
        self.assertEqual(classify_tick('2026-10-08T14:30:00+08:00', after_hours_segment='AFTER_HOURS_FIXED_PRICE'),
                         'AFTER_HOURS_FIXED_PRICE')

    def test_afterhours_oddlot(self):
        self.assertEqual(classify_tick('2026-10-08T14:30:00+08:00', after_hours_segment='AFTER_HOURS_ODD_LOT'),
                         'AFTER_HOURS_ODD_LOT')

    def test_bad_timezone(self):
        with self.assertRaisesRegex(ValueError, 'timezone'):
            classify_tick('2026-10-08T14:30:00Z')

    def test_naive_timestamp(self):
        with self.assertRaisesRegex(ValueError, 'timezone'):
            classify_tick('2026-10-08T14:30:00')

    def test_bad_volume(self):
        with self.assertRaisesRegex(ValueError, 'volume'):
            separate_ticks([dict(timestamp='2026-10-08T13:30:00+08:00', price=100, volume_lots=0)])

    def test_partition_no_aggregation(self):
        rows=[dict(timestamp='2026-10-08T13:30:00+08:00',price=100,volume_lots=10),
              dict(timestamp='2026-10-08T14:30:00+08:00',price=100,volume_lots=3)]
        x=separate_ticks(rows,after_hours_segment='AFTER_HOURS_FIXED_PRICE')
        self.assertEqual(x['strategy_gate'],'BLOCKED')
        self.assertEqual(len(x['session_partitions']),2)
        self.assertEqual(x['execution_status'],'NOT_A_FILL')


if __name__ == '__main__':
    unittest.main()
