from django.test import TestCase
from .utils import calculate_trip_segments

class HOSLogicTestCase(TestCase):
    def test_short_trip_no_breaks(self):
        """
        Test 1: Short Trip (~300 miles, ~5 hours driving)
        Should have: Pickup (1h), Drive (~5h), Dropoff (1h). No breaks.
        """
        # 300 miles / 60mph = 5 hours driving
        segments, hours_consumed = calculate_trip_segments(300, 10)
        
        types = [s['type'] for s in segments]
        self.assertEqual(types, ['on_duty', 'driving', 'on_duty'])
        self.assertAlmostEqual(hours_consumed, 1 + 5 + 1, delta=0.1)

    def test_medium_trip_break(self):
        """
        Test 2: Medium Trip (~660 miles, 11 hours driving -> needs break)
        Actually 600 miles = 10 hours.
        Rule: 30 min break required after 8 hours driving.
        Expect: Pickup(1), Drive(8), Break(0.5), Drive(2), Dropoff(1)
        """
        # 600 miles
        segments, hours_consumed = calculate_trip_segments(600, 20)
        
        types = [s['type'] for s in segments]
        # Check presence of break
        self.assertIn('off_duty', types) # We used off_duty for 30m break
        
        # Verify sequence
        # Index 0: Pickup
        # Index 1: Drive (8h)
        # Index 2: Break (0.5h)
        # Index 3: Drive (2h)
        # Index 4: Dropoff
        
        self.assertEqual(segments[1]['duration'], 8.0)
        self.assertEqual(segments[2]['type'], 'off_duty')
        self.assertEqual(segments[2]['duration'], 0.5)

    def test_long_trip_sleeper(self):
        """
        Test 3: Long Trip (1000 miles, ~16.6h driving)
        Needs: Pickup, Drive(8), Break, Drive(3 -> 11h limit), Sleeper, Drive(Rest), Dropoff
        Also Fuel Stop at 1000 miles?
        1000 miles exactly might trigger fuel stop at the very end or just before dropoff.
        """
        segments, hours_consumed = calculate_trip_segments(1000, 0)
        types = [s['type'] for s in segments]
        
        self.assertIn('sleeper', types)
        
        # Count 10h rests
        sleepers = [s for s in segments if s['type'] == 'sleeper']
        self.assertEqual(len(sleepers), 1)
        self.assertEqual(sleepers[0]['duration'], 10.0)

    def test_near_limit(self):
        """
        Test 4: Near 70-hour limit.
        Hours used = 68. Available = 2.
        Trip = 300 miles (5 hours).
        Should fail or truncate.
        """
        # Pickup (1h) + Drive (1h) = 2h.
        # Should stop after 1h driving (total 2h consumption).
        # Actually utils.py checks cycle at generic points.
        
        segments, hours_consumed = calculate_trip_segments(300, 68)
        
        # Should contain "REACHED 70-HOUR LIMIT" or similar
        last_seg = segments[-1]
        if last_seg['type'] == 'off_duty' and 'LIMIT' in last_seg['description']:
            # Passed truncation check
            pass
        else:
            # Check if total consumed <= 2.1 (allow float variance)
            self.assertLessEqual(hours_consumed, 2.1)
