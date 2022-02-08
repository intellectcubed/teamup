# import common.date_utils as date_utils
from common import date_utils
from datetime import datetime
from collections import namedtuple
import unittest
Range = namedtuple('Range', ['start', 'end'])

"""
From root directory TeamUp: python3 -m test.test_date_utils
"""

class TestDaysOverlap(unittest.TestCase):

    def test_no_overlap(self):
        self.longMessage = True
        self.assertEqual(date_utils.hours_overlap(Range(datetime(2021, 1, 1, 18, 0, 0), datetime(2021, 1, 2, 6, 0, 0)), 
        Range(datetime(2021, 1, 1, 6, 0, 0), datetime(2021, 1, 1, 18, 0, 0))), 0)

    def test_no_overlap_2(self):
        self.longMessage = True
        self.assertEqual(date_utils.hours_overlap(Range(datetime(2021, 1, 1, 18, 0, 0), datetime(2021, 1, 2, 6, 0, 0)), 
            Range(datetime(2021, 1, 2, 6, 0, 0), datetime(2021, 1, 2, 10, 0, 0))), 0)

    def test_no_overlap_3(self):
        self.longMessage = True
        self.assertEqual(date_utils.hours_overlap(Range(datetime(2021, 1, 1, 18, 0, 0), datetime(2021, 1, 2, 6, 0, 0)), 
            Range(datetime(2021, 1, 1, 12, 0, 0), datetime(2021, 1, 1, 20, 0, 0))), 2)

    def test_no_overlap_4(self):
        self.longMessage = True
        self.assertEqual(date_utils.hours_overlap(Range(datetime(2021, 1, 1, 18, 0, 0), datetime(2021, 1, 2, 6, 0, 0)), 
            Range(datetime(2021, 1, 1, 18, 0, 0), datetime(2021, 1, 1, 20, 0, 0))), 2)


    def test_no_overlap_5(self):
        self.longMessage = True
        self.assertEqual(date_utils.hours_overlap(Range(datetime(2021, 1, 1, 18, 0, 0), datetime(2021, 1, 2, 6, 0, 0)), 
            Range(datetime(2021, 1, 1, 19, 0, 0), datetime(2021, 1, 1, 20, 0, 0))), 1)

    def test_no_overlap_6(self):
        self.longMessage = True
        self.assertEqual(date_utils.hours_overlap(Range(datetime(2021, 1, 1, 18, 0, 0), datetime(2021, 1, 2, 6, 0, 0)), 
            Range(datetime(2021, 1, 1, 19, 0, 0), datetime(2021, 1, 2, 5, 0, 0))), 10)

    def test_no_overlap_7(self):
        self.longMessage = True
        self.assertEqual(date_utils.hours_overlap(Range(datetime(2021, 1, 1, 18, 0, 0), datetime(2021, 1, 2, 6, 0, 0)), 
            Range(datetime(2021, 1, 1, 19, 0, 0), datetime(2021, 1, 2, 6, 0, 0))), 11)

    def test_no_overlap_8(self):
        self.longMessage = True
        self.assertEqual(date_utils.hours_overlap(Range(datetime(2021, 1, 1, 18, 0, 0), datetime(2021, 1, 2, 6, 0, 0)), 
            Range(datetime(2021, 1, 1, 19, 0, 0), datetime(2021, 1, 2, 8, 0, 0))), 11)

    def test_no_overlap_9(self):
        self.longMessage = True
        self.assertEqual(date_utils.hours_overlap(Range(datetime(2022, 2, 5, 18, 0, 0), datetime(2022, 2, 6, 6, 0, 0)), 
            Range(datetime(2022, 2, 5, 12, 0, 0), datetime(2022, 2, 5, 18, 0, 0))), 0)


if __name__ == '__main__':
    unittest.main()
