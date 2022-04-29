import dateutil
import calendar
import common.date_utils as date_utils
import os
from enum import Enum


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
