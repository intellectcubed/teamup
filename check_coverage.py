import requests
import json
import dateutil.parser
import datetime
import sys
import os

api_key = os.environ['TEAMUP_API_KEY']

url = 'https://api.teamup.com'
collaborative_calendar_key = os.environ['COLLABORATIVE_CALENDAR_KEY']

coverage_required_calendar = os.environ['COVERAGE_REQUIRED_CALENDAR']
coverage_offered_calendar = os.environ['COVERAGE_OFFERED_CALENDAR']
tango_required_calendar = os.environ['TANGO_REQUIRED_CALENDAR']
tango_offered_calendar = os.environ['TANGO_OFFERED_CALENDAR']

output_fmt = '%m/%d/%Y %H:%M'


def get_date_hour_key(dt):
    return dt.strftime('%Y%m%d%H')

def get_events(start_dt, end_dt, subcalendar_id):
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'Teamup-Token': api_key}
    ret = requests.get('/'.join([url, collaborative_calendar_key, 'events']) + '?startDate={}&endDate={}&subcalendarId[]={}'.format(start_dt, end_dt, subcalendar_id), headers=headers)
    return json.loads(ret.text)

def get_coverage_required(start_dt, end_dt):
    return get_events(start_dt, end_dt, coverage_required_calendar)

def get_coverage_required2(start_dt, end_dt):
    required_dict = {}
    events = get_events(start_dt, end_dt, coverage_required_calendar)
    for event in events['events']:
        num_hours = get_hours(event['start_dt'], event['end_dt'])
        required_dict[event['id']] = [{'event_id':event['id'], 'start_time': event['start_dt']} for ele in range(num_hours)]


def get_coverage_offered(start_dt, end_dt):
    """
    Get all coverage offered events.  For each event, expand the hours into their own keys in the dict.
    For example 
    """
    coverage_offered = {} # Key: date + hour, value: list of events
    coverages = get_events(start_dt, end_dt, coverage_offered_calendar)
    for coverage in coverages['events']:
        num_hours = get_hours(coverage['start_dt'], coverage['end_dt']) # for how many hours is this coverage offered?
        start_date = dateutil.parser.isoparse(coverage['start_dt'])
        for hour in range(num_hours):
            dt = datetime.timedelta(hours=hour)
            coverage_hour = start_date + dt
            date_hour_key = get_date_hour_key(coverage_hour)
            coverage_offered[date_hour_key] = coverage_offered.get(date_hour_key, [])
            coverage_offered[date_hour_key].append(coverage)

    return coverage_offered

def check_events(start_dt, end_dt):
    requireds = get_coverage_required(start_dt, end_dt)
    coverages = get_coverage_offered(start_dt, end_dt)

    shift_errors = []
    shift_warnings = []

    for required in requireds['events']:
        missing, warnings = check_staffing(required, coverages)
        # shift = '{} - {}'.format(required['start_dt'], required['end_dt'])
        if len(missing) > 0:
            shift_errors.append({'shift': required, 'errors': missing, 'warnings': warnings})
        if len(warnings) > 0:
            shift_warnings.append({'shift': required, 'errors': [], 'warnings': warnings})

    return (shift_errors, shift_warnings)

def check_staffing(required_coverage, coverage_events):
    """
    Check if the coverage offered is sufficient for the required coverage.
    Return tuple: (list of required coverage, warnings)
    """
    crew_missing = dict()
    shift_warnings = dict()

    start_date = dateutil.parser.isoparse(required_coverage['start_dt'])
    hours = get_hours(required_coverage['start_dt'], required_coverage['end_dt'])
    for hour in range(hours):
        dt = datetime.timedelta(hours=hour)
        coverage_hour = start_date + dt
        date_hour_key = get_date_hour_key(coverage_hour)
        coverage_events_for_hour = coverage_events.get(date_hour_key, [])
        missing, warnings = is_hour_staffed(coverage_events_for_hour)

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
            missing_ranges.append({'start_dt': key_to_date(min_date).strftime(output_fmt), 'end_dt': add_hour_to_key(max_date).strftime(output_fmt), 'errors': errors})
            errors = None
            min_date = None
            max_date = None

    if min_date is not None:
        missing_ranges.append({'start_dt': key_to_date(min_date).strftime(output_fmt), 'end_dt': add_hour_to_key(max_date).strftime(output_fmt), 'errors': errors})

    return missing_ranges            

def is_hour_staffed(coverage_events_for_hour):
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
        missing.append('CC')
    
    if not ('driver' in roles or 'emt' in roles):
        missing.append('Driver or EMT over 18')

    return (missing, warnings)


def get_hours(start_dt, end_dt):
    start_date = dateutil.parser.isoparse(start_dt)
    end_date = dateutil.parser.isoparse(end_dt)
    diff = end_date - start_date
    return diff.days * 24 + diff.seconds //3600

def debug_show():
    coverage = get_coverage_offered('2021-12-01', '2021-12-31')
    for key, value in coverage.items() :
        offer = key
        for item in value:
            offer += '({})'.format(item['custom']['coverage_level'][0])
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

def debug_errors(shift_errors):
    print('The folowing shifts have errors:')
    for shift in shift_errors:
        print('{} to {} - {}'.format(dateutil.parser.isoparse(shift['shift']['start_dt']).strftime(output_fmt), dateutil.parser.isoparse(shift['shift']['end_dt']).strftime(output_fmt), shift['errors']))

if __name__ == '__main__':
    errors, warnings = check_events('2021-12-01', '2021-12-31')
    print('Found: {} errors and {} warnings'.format(len(errors), len(warnings)))
    debug_errors(errors)
    # print('Here is the api key: |{}|'.format(api_key))
    # coverages = get_events('2021-12-01', '2021-12-31', coverage_offered_calendar)
    # print(coverages)

