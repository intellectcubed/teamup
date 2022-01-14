import dateutil
import datetime

OUTPUT_FMT_YMDHM = '%m/%d/%Y %H:%M'
OUTPUT_FMT_YMD = '%B %d, %Y'
API_DATE_FORMAT_YMD = '%Y-%m-%d'
HOUR_KEY_FMT = '%Y%m%d%H'



def date_simple_format(dt):
    return dateutil.parser.isoparse(dt).strftime(OUTPUT_FMT_YMDHM)

def key_to_date(key):
    return datetime.datetime.strptime(key, HOUR_KEY_FMT)

def date_to_key(dt):
    return dt.strftime(HOUR_KEY_FMT)

def add_hour_to_key(key):
    dt = key_to_date(key)
    delta = datetime.timedelta(hours=1)
    return dt + delta

def parse_date_add_hours(date_str, hours, format):
    dt = datetime.datetime.strptime(date_str, format)
    delta = datetime.timedelta(hours=hours)
    return dt + delta

def get_hours(start_date, end_date):
    diff = end_date - start_date
    return diff.days * 24 + diff.seconds //3600

def get_days_diff(start_date, end_date):
    if start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=end_date.tzinfo)
    if end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=start_date.tzinfo)

    diff = end_date - start_date
    return diff.days


def get_hours_parse(start_dt, end_dt):
    start_date = dateutil.parser.isoparse(start_dt)
    end_date = dateutil.parser.isoparse(end_dt)
    return get_hours(start_date, end_date)


