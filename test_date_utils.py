import common.date_utils as date_utils
from datetime import datetime
from collections import namedtuple
Range = namedtuple('Range', ['start', 'end'])

def test_days_overlap():

    assert(date_utils.hours_overlap(Range(datetime(2021, 1, 1, 18, 0, 0), datetime(2021, 1, 2, 6, 0, 0)), 
        Range(datetime(2021, 1, 1, 6, 0, 0), datetime(2021, 1, 1, 18, 0, 0))) == 0)

    assert(date_utils.hours_overlap(Range(datetime(2021, 1, 1, 18, 0, 0), datetime(2021, 1, 2, 6, 0, 0)), 
        Range(datetime(2021, 1, 2, 6, 0, 0), datetime(2021, 1, 2, 10, 0, 0))) == 0)

    assert(date_utils.hours_overlap(Range(datetime(2021, 1, 1, 18, 0, 0), datetime(2021, 1, 2, 6, 0, 0)), 
        Range(datetime(2021, 1, 1, 12, 0, 0), datetime(2021, 1, 1, 20, 0, 0))) == 2)

    assert(date_utils.hours_overlap(Range(datetime(2021, 1, 1, 18, 0, 0), datetime(2021, 1, 2, 6, 0, 0)), 
        Range(datetime(2021, 1, 1, 18, 0, 0), datetime(2021, 1, 1, 20, 0, 0))) == 2)


    assert(date_utils.hours_overlap(Range(datetime(2021, 1, 1, 18, 0, 0), datetime(2021, 1, 2, 6, 0, 0)), 
        Range(datetime(2021, 1, 1, 19, 0, 0), datetime(2021, 1, 1, 20, 0, 0))) == 1)

    assert(date_utils.hours_overlap(Range(datetime(2021, 1, 1, 18, 0, 0), datetime(2021, 1, 2, 6, 0, 0)), 
        Range(datetime(2021, 1, 1, 19, 0, 0), datetime(2021, 1, 2, 5, 0, 0))) == 10)

    assert(date_utils.hours_overlap(Range(datetime(2021, 1, 1, 18, 0, 0), datetime(2021, 1, 2, 6, 0, 0)), 
        Range(datetime(2021, 1, 1, 19, 0, 0), datetime(2021, 1, 2, 6, 0, 0))) == 11)

    assert(date_utils.hours_overlap(Range(datetime(2021, 1, 1, 18, 0, 0), datetime(2021, 1, 2, 6, 0, 0)), 
        Range(datetime(2021, 1, 1, 19, 0, 0), datetime(2021, 1, 2, 8, 0, 0))) == 11)

    assert(date_utils.hours_overlap(Range(datetime(2022, 2, 5, 18, 0, 0), datetime(2022, 2, 6, 6, 0, 0)), 
        Range(datetime(2022, 2, 5, 12, 0, 0), datetime(2022, 2, 5, 18, 0, 0))) == 11)


if __name__ == '__main__':
    test_days_overlap()