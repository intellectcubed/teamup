import dateutil
import calendar
import common.date_utils as date_utils
import os
from enum import Enum
from datetime import datetime, timedelta


class NotificationCategory(Enum):
    SHIFT_NOTIFICATION = 'shiftnotification'
    ERROR_NOTIFICATION = 'errornotification'



def create_shift_name(shift):
    start_date = dateutil.parser.isoparse(shift['start_dt'])

    period = (start_date.hour % 24 + 4) // 4
    period_map = {1: 'Late Night',
                        2: 'Early Morning',
                        3: 'Morning',
                        4: 'Noon',
                        5: 'Evening',
                        6: 'Night'};
    return '{} ({} shift) {}'.format(
        calendar.day_name[start_date.weekday()], 
        period_map.get(period),
        start_date.strftime(date_utils.OUTPUT_FMT_YMD))


def clear_relative_path(path):
    current_dir = os.getcwd()

    target_path = path

    if not path.startswith(current_dir):
        if path.startswith('/'):
            target_path = os.path.join(current_dir, path[1:])
        else:
            target_path = os.path.join(current_dir, path)

    

    if os.path.isdir(target_path):
        os.rmdir(target_path)

    os.makedirs(target_path)


def create_start_end_dates(year, month, day, time_range):
    """
    (start, end) = create_start_end_dates(2022, 5, 2, '1200 - 0600')
    """
    fmt = "%Y-%m-%dT%H:%M:%S"    
    
    start_time = time_range.split('-')[0].strip()
    end_time = time_range.split('-')[1].strip()

    str_start = '{}-{:02d}-{:02d}T{:02d}:{:02d}:00'.format(year, month, day, int(start_time[:2]), int(start_time[2:]))
    start_date = datetime.strptime(str_start, fmt)

    end_month = month
    end_day = day

    if int(end_time) < int(start_time):
        modified_date = start_date + timedelta(days=1)
        end_month = modified_date.month
        end_day = modified_date.day

    str_end = '{}-{:02d}-{:02d}T{:02d}:{:02d}:00'.format(year, end_month, end_day, int(end_time[:2]), int(end_time[2:]))
    end_date = datetime.strptime(str_end, fmt)

    return (start_date, end_date)
