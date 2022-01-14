import dateutil
import calendar
import common.date_utils as date_utils

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

