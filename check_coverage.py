import requests
import json
import dateutil.parser
import datetime
import sys
import os
import calendar

api_key = os.environ['TEAMUP_API_KEY']

url = 'https://api.teamup.com'
collaborative_calendar_key = os.environ['COLLABORATIVE_CALENDAR_KEY']

coverage_required_calendar = os.environ['COVERAGE_REQUIRED_CALENDAR']
coverage_offered_calendar = os.environ['COVERAGE_OFFERED_CALENDAR']
tango_required_calendar = os.environ['TANGO_REQUIRED_CALENDAR']
tango_offered_calendar = os.environ['TANGO_OFFERED_CALENDAR']

OUTPUT_FMT_YMDHM = '%m/%d/%Y %H:%M'
API_DATE_FORMAT_YMD = '%Y-%m-%d'


def get_date_hour_key(dt):
    return dt.strftime('%Y%m%d%H')


def get_events(start_dt, end_dt, subcalendar_id):
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'Teamup-Token': api_key}
    ret = requests.get('/'.join([url, collaborative_calendar_key, 'events']) + '?startDate={}&endDate={}&subcalendarId[]={}'.format(start_dt, end_dt, subcalendar_id), headers=headers)
    return json.loads(ret.text)


def get_coverage_required(sub_calendar_id, start_dt, end_dt):
    return get_events(start_dt, end_dt, sub_calendar_id)


def get_coverage_offered(sub_calendar_id, start_dt, end_dt):
    """
    Get all coverage offered events.  For each event, expand the hours into their own keys in the dict.
    For example 
    Key: 2021120218
    Value: <Coverage Offer Message>
    """
    coverage_offered = {} # Key: date + hour, value: list of events
    coverages = get_events(start_dt, end_dt, sub_calendar_id)
    for coverage in coverages['events']:
        num_hours = get_hours_parse(coverage['start_dt'], coverage['end_dt']) # for how many hours is this coverage offered?
        start_date = dateutil.parser.isoparse(coverage['start_dt'])
        for hour in range(num_hours):
            dt = datetime.timedelta(hours=hour)
            coverage_hour = start_date + dt
            date_hour_key = get_date_hour_key(coverage_hour)
            coverage_offered[date_hour_key] = coverage_offered.get(date_hour_key, [])
            coverage_offered[date_hour_key].append(coverage)

    return coverage_offered

def check_events(required_subcalendar_id, offered_subcalendar_id, start_dt, end_dt):
    """
    Check if the coverage offered is sufficient for the required coverage.
    """
    requireds = get_coverage_required(required_subcalendar_id, start_dt, end_dt)

    # Note: When getting the coverage offered, we will start from the previous day (1 day before start_dt) to get all of the events
    # that started the day before, and ended today.
    start_dt = (datetime.datetime.strptime(start_dt, API_DATE_FORMAT_YMD) - datetime.timedelta(days=1)).strftime(API_DATE_FORMAT_YMD)
    coverages = get_coverage_offered(offered_subcalendar_id, start_dt, end_dt)

    shift_errors = []
    shift_warnings = []

    for required in requireds['events']:
        missing, warnings = check_staffing(required_subcalendar_id, required, coverages)
        # shift = '{} - {}'.format(required['start_dt'], required['end_dt'])
        if len(missing) > 0:
            shift_errors.append({'shift': required, 'errors': missing, 'warnings': warnings})
        if len(warnings) > 0:
            shift_warnings.append({'shift': required, 'errors': [], 'warnings': warnings})

    return (shift_errors, shift_warnings)

def check_staffing(required_subcalendar_id, required_coverage, coverage_events):
    """
    Check if the coverage offered is sufficient for the required coverage.
    Return tuple: (list of required coverage, warnings)
    """
    crew_missing = dict()
    shift_warnings = dict()

    start_date = dateutil.parser.isoparse(required_coverage['start_dt'])
    hours = get_hours_parse(required_coverage['start_dt'], required_coverage['end_dt'])
    for hour in range(hours):
        dt = datetime.timedelta(hours=hour)
        coverage_hour = start_date + dt
        date_hour_key = get_date_hour_key(coverage_hour)
        coverage_events_for_hour = coverage_events.get(date_hour_key, [])
        missing, warnings = is_hour_staffed(required_subcalendar_id, coverage_events_for_hour)

        if len(missing) > 0:
            crew_missing[date_hour_key] = missing

        if len(warnings) > 0:
            shift_warnings[date_hour_key] = warnings

    missing_ranges = consolidate_hours(crew_missing)
    return (missing_ranges, shift_warnings)

def key_to_date(key):
    format1 = '%Y%m%d%H'
    return datetime.datetime.strptime(key, format1)

def add_hour_to_key(key):
    dt = key_to_date(key)
    delta = datetime.timedelta(hours=1)
    return dt + delta

def consolidate_hours(crew_missing):
    missing_ranges = []
    min_date = None
    max_date = None
    errors = None
    for key in sorted(crew_missing.keys()):
        if min_date is None or key < min_date:
            min_date = key
        if max_date is None or key > max_date:
            max_date = key
        
        if errors is None:
            errors = crew_missing[key]

        date_errors = crew_missing[key]
        if date_errors != errors:
            missing_ranges.append({'start_dt': key_to_date(min_date).strftime(OUTPUT_FMT_YMDHM), 'end_dt': add_hour_to_key(max_date).strftime(OUTPUT_FMT_YMDHM), 'errors': errors})
            errors = None
            min_date = None
            max_date = None

    if min_date is not None:
        missing_ranges.append({'start_dt': key_to_date(min_date).strftime(OUTPUT_FMT_YMDHM), 'end_dt': add_hour_to_key(max_date).strftime(OUTPUT_FMT_YMDHM), 'errors': errors})

    return missing_ranges            


def is_hour_staffed(subcalendar_id, coverage_events_for_hour):
    """
    Logic for determining if a shift is correctly staffed.  The required subcalendar id determines which logic to apply
    """

    if subcalendar_id == coverage_required_calendar:
        return check_shift_coverage(coverage_events_for_hour)
    elif subcalendar_id == tango_required_calendar:
        return check_tango_coverage(coverage_events_for_hour)


def check_tango_coverage(coverage_events_for_hour):
    """
    Check if the coverage offered is sufficient for the required coverage.
    Return tuple: (list of required coverage, warnings)
    """
    tango_missing = []
    tango_warnings = []

    num_tangos = 0
    for event in coverage_events_for_hour:
        if event['custom']['coverage_level'][0] == 'station_95_supervisor':
            num_tangos += 1

    if num_tangos < 1:
        tango_missing.append('Missing tango coverage')

    if num_tangos > 1:
        tango_warnings.append('Too many tangos')

    return (tango_missing, tango_warnings)

def check_shift_coverage(coverage_events_for_hour):
    warnings = []
    missing = []
    roles = {}

    if len(coverage_events_for_hour) > 5:
        warnings.append('Crew too large - 5 maximum')

    for event in coverage_events_for_hour:
        roles[event['custom']['coverage_level'][0]] = roles.get(event['custom']['coverage_level'][0], 0) + 1

    # is there a CC?
    if 'crew_chief' in roles:
        if roles['crew_chief'] > 1:
            warnings.append('Warning: more than one CC')
    else:
        missing.append('Crew Chief')
    
    if not ('driver' in roles or 'emt' in roles):
        missing.append('Driver or EMT over 18')

    return (missing, warnings)


def get_hours(start_date, end_date):
    diff = end_date - start_date
    return diff.days * 24 + diff.seconds //3600


def get_hours_parse(start_dt, end_dt):
    start_date = dateutil.parser.isoparse(start_dt)
    end_date = dateutil.parser.isoparse(end_dt)
    return get_hours(start_date, end_date)

def translate_coverage(coverage_level):
    if coverage_level == 'CC':
        return 'Crew Chief'
    else:
        return coverage_level

def debug_show():
    coverage = get_coverage_offered(coverage_offered_calendar, '2021-12-01', '2021-12-31')
    for key, value in coverage.items() :
        offer = key
        for item in value:
            offer += '({})'.format(translate_coverage(item['custom']['coverage_level'][0]))
        print(offer)


def format_error_report(shift_errors):
    """
    Format the error report for Slack
    """
    error_report = ''
    for shift in shift_errors:
        error_report += 'Shift: {}\n'.format(shift['shift']['start_dt'])
        for error in shift['errors']:
            error_report += '  {}\n'.format(error)
        for warning in shift['warnings']:
            error_report += '  {}\n'.format(warning)
        error_report += '\n'
    return error_report

def date_simple_format(dt):
    return dateutil.parser.isoparse(dt).strftime(OUTPUT_FMT_YMDHM)


def create_shift_name(shift):
    start_date = dateutil.parser.isoparse(shift['start_dt'])

    period = (start_date.hour % 24 + 4) // 4
    period_map = {1: 'Late Night',
                        2: 'Early Morning',
                        3: 'Morning',
                        4: 'Noon',
                        5: 'Evening',
                        6: 'Night'};
    return '{} {}'.format(calendar.day_name[start_date.weekday()], period_map.get(period))


def debug_errors(shift_errors):
    if len(shift_errors) == 0:
        return
    print('The folowing shifts have errors:')
    for shift in shift_errors:
        print('Shift: ({}) {} - {}'.format(create_shift_name(shift['shift']), date_simple_format(shift['shift']['start_dt']), date_simple_format(shift['shift']['end_dt'])))
        for error in shift['errors']:
            err_start = error['start_dt']
            err_end = error['end_dt']

            start_date = datetime.datetime.strptime(err_start, OUTPUT_FMT_YMDHM)
            end_date = datetime.datetime.strptime(err_end, OUTPUT_FMT_YMDHM)

            for item in error['errors']:
                print('  {} - {} ({} hours): {}'.format(err_start, err_end, get_hours(start_date, end_date), item))
        print("") 

def debug_shift(start_dt, end_dt):
    requireds = get_coverage_required(coverage_required_calendar, start_dt, end_dt)
    coverages = get_coverage_offered(coverage_offered_calendar, start_dt, end_dt)

    shift_errors, warnings = check_events('2021-12-01', '2021-12-31')

    # for required in requireds['events']:
    print(coverages)

    for key, value in coverages.items():
        print('{}'.format(key))


    # coverage = get_coverage_offered(coverage_offered_calendar, start_dt, end_dt)
    # for key, value in coverage.items() :
    #     offer = key
    #     for item in value:
    #         offer += '({})'.format(item['custom']['coverage_level'][0])
    #     print(offer)


if __name__ == '__main__':
    search_start = datetime.datetime.now().strftime(API_DATE_FORMAT_YMD)
    search_end = (datetime.datetime.now() + datetime.timedelta(days=5)).strftime(API_DATE_FORMAT_YMD)
    print('Searching from {} to {}'.format(search_start, search_end))
    errors, warnings = check_events(coverage_required_calendar, coverage_offered_calendar, search_start, search_end)
    print('====================================')
    print('Duty Shifts Found: {} errors and {} warnings'.format(len(errors), len(warnings)))
    debug_errors(errors)

    errors, warnings = check_events(tango_required_calendar, tango_offered_calendar, search_start, search_end)
    print('====================================')
    print('Tango Shifts Found: {} errors and {} warnings'.format(len(errors), len(warnings)))
    debug_errors(errors)
    print('====================================')


    # debug_shift('2021-12-01', '2021-12-31')

    # print('Here is the api key: |{}|'.format(api_key))
    # coverages = get_events('2021-12-01', '2021-12-31', coverage_offered_calendar)
    # print(coverages)

