import requests
import json
import dateutil.parser
import datetime
import sys
import os
import calendar
import time

api_key = os.environ['TEAMUP_API_KEY']

url = 'https://api.teamup.com'
collaborative_calendar_key = os.environ['COLLABORATIVE_CALENDAR_KEY']

coverage_required_calendar = os.environ['COVERAGE_REQUIRED_CALENDAR']
coverage_offered_calendar = os.environ['COVERAGE_OFFERED_CALENDAR']
tango_required_calendar = os.environ['TANGO_REQUIRED_CALENDAR']
tango_offered_calendar = os.environ['TANGO_OFFERED_CALENDAR']

OUTPUT_FMT_YMDHM = '%m/%d/%Y %H:%M'
OUTPUT_FMT_YMD = '%B %d, %Y'
API_DATE_FORMAT_YMD = '%Y-%m-%d'

COVERAGE_LEVEL_DESCR_MAP = {
    'crew_chief': 'Crew Chief',
    'emt': 'EMT over 18',
    'emt_under_18_': 'EMT under 18',
    'driver': 'Driver'
} 

BRIEF_COVERAGE_DESCR_MAP = {
    'crew_chief': 'CC',
    'emt': 'EMT > 18',
    'emt_under_18_': 'EMT < 18',
    'driver': 'Driver'
} 

HOUR_KEY_FMT = '%Y%m%d%H'


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
            date_hour_key = date_to_key(coverage_hour)
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

    return (requireds, coverages, shift_errors, shift_warnings)

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
        date_hour_key = date_to_key(coverage_hour)
        coverage_events_for_hour = coverage_events.get(date_hour_key, [])
        missing, warnings = is_hour_staffed(required_subcalendar_id, coverage_events_for_hour)

        if len(missing) > 0:
            crew_missing[date_hour_key] = missing

        if len(warnings) > 0:
            shift_warnings[date_hour_key] = warnings

    # for key, value in crew_missing.items():
    #     print('{} - {}'.format(key, value))

    missing_ranges = consolidate_hours(crew_missing)
    return (missing_ranges, shift_warnings)

def key_to_date(key):
    return datetime.datetime.strptime(key, HOUR_KEY_FMT)

def date_to_key(dt):
    return dt.strftime(HOUR_KEY_FMT)

def add_hour_to_key(key):
    dt = key_to_date(key)
    delta = datetime.timedelta(hours=1)
    return dt + delta

STAFFING_ERROR_SORT_ORDER = ['Crew Chief', 'Driver or EMT over 18']

def consolidate_hours(crew_missing):
    # First, we expand the errors into their own keys in the dict.
    missing_cats = dict()

    for key, value in crew_missing.items():
        for missing in value:
            missing_cats[missing] = missing_cats.get(missing, [])
            missing_cats[missing].append(key)

    for key, value in missing_cats.items():
        missing_dates = value
        date_sets = []
        sub_list =[]
        for date in missing_dates:
            if len(sub_list) == 0:
                sub_list.append(date)
            elif add_hour_to_key(sub_list[-1]) == key_to_date(date):
                sub_list.append(date)
            else:
                date_sets.append(sub_list[:])
                sub_list = []
        if len(sub_list) > 0:
            date_sets.append(sub_list[:])

        missing_cats[key] = date_sets

    missing_ranges = []
    for key in STAFFING_ERROR_SORT_ORDER:
        if key in missing_cats:
            date_sets = missing_cats[key]
            for date_set in date_sets:
                start_date = key_to_date(date_set[0])
                end_date = add_hour_to_key(date_set[-1])
                hours = get_hours(start_date, end_date)
                missing_ranges.append({'start_dt': start_date.strftime(OUTPUT_FMT_YMDHM), 'end_dt': end_date.strftime(OUTPUT_FMT_YMDHM), 'hours': hours, 'error': key})

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
    return '{} ({} shift) {}'.format(
        calendar.day_name[start_date.weekday()], 
        period_map.get(period),
        start_date.strftime(OUTPUT_FMT_YMD)
        )


def report_errors(shift_errors):
    if len(shift_errors) == 0:
        return
    print('The folowing shifts have errors:')
    for shift in shift_errors:
        print('Shift: ({}) {} - {}'.format(create_shift_name(shift['shift']), date_simple_format(shift['shift']['start_dt']), date_simple_format(shift['shift']['end_dt'])))
        for error in shift['errors']:
            print('  {} - {} ({} hours): {}'.format(error['start_dt'], error['end_dt'], error['hours'], error['error']))
        print("") 


def events_to_map(shifts):
    """
    Convert a list of shifts to a map of shifts
    """
    shift_map = {}
    for shift in shifts:
        start_date = shift['start_dt']
        if start_date in shift_map:
            shift_map[start_date].append(shift)
        else:
            shift_map[start_date] = [shift]
    return shift_map


def expand_event(event):
    """
    Given an event, expand it into a list of events
    return key, [event]
    """
    # key = hour
    # value = event

    expanded_events = {}
    num_hours = get_hours_parse(event['start_dt'], event['end_dt']) # for how many hours is this coverage offered?
    start_date = dateutil.parser.isoparse(event['start_dt'])
    for hour in range(num_hours):
        dt = datetime.timedelta(hours=hour)
        coverage_hour = start_date + dt
        date_hour_key = date_to_key(coverage_hour)
        expanded_events[date_hour_key] = expanded_events.get(date_hour_key, [])
        expanded_events[date_hour_key].append(event)
    
    return expanded_events

DEBUG_OUTPUT = False

def report_shifts(coverage_required_calendar, coverage_offered_calendar, search_start, search_end, errors):
    debug_ts = int(time.time())

    shifts = get_events(search_start, search_end, coverage_required_calendar)
    coverages = get_events(search_start, search_end, coverage_offered_calendar)

    shift_map = events_to_map(shifts['events'])
    shift_keys = sorted(shift_map.keys())

    coverage_map = events_to_map(coverages['events'])
    coverage_keys = sorted(coverage_map.keys())

    # key = date, value = {shift, [coverage]}
    merged_shift_map = {}

    for shift_key in shift_keys:
        shifts_ = shift_map[shift_key]
        for shift in shifts_:
            # key = member_name, hours = {string, int}
            shift_summary_map = {}
            shift_date = shift['start_dt']
            covers_for_shift = {}
            for coverage_key in coverage_keys:
                coverages_ = coverage_map[coverage_key]
                for coverage in coverages_:
                    #TODO: If coverage offer started within the shift, but end is beyond end of shift, it will be ignored.  Should be counted!!
                    if coverage_key >= shift_key and coverage_key <= shift['end_dt']:
                        shift_summary_map[coverage['who']] = shift_summary_map.get(coverage['who'], 0) + get_hours_parse(coverage['start_dt'], coverage['end_dt'])
                        events_by_hour = expand_event(coverage)
                        for hour_key, events in events_by_hour.items():
                            covers_for_shift[hour_key] = covers_for_shift.get(hour_key, [])
                            covers_for_shift[hour_key].extend(events)
            merged_shift_map[shift_date] = {'shift': shift, 'coverage': covers_for_shift, 'shift-summary': shift_summary_map}

    # For every hour, sort the coverages: by coverage level, then by name
    for shift_date, shift_and_coverage in merged_shift_map.items():
        shift = shift_and_coverage['shift']
        coverage = shift_and_coverage['coverage']
        for hour_key, coverages in coverage.items():
            coverages.sort(key=lambda x: (x['custom']['coverage_level'][0], x['who']))
            coverage[hour_key] = coverages

    if DEBUG_OUTPUT:
        print('+++++')
        with open('/Users/gnowakow/Downloads/shift_map_{}.json'.format(debug_ts), 'w') as f:
            f.write(json.dumps(merged_shift_map, indent=4, sort_keys=True))
        print('+++++')

    """
    merged_shift_map is a map containing the following: 
    {
        shift_start_date (2022-01-08T11:00:00-05:00): {
            shift: {...shift attributes...},
            coverage: {
                hour_key (2022010812): [
                    {...coverage attributes...},
                    {...coverage attributes...},
                ]
            }
        }
    }
    
    """

    final_report_map = collapse_into_like_shifts(merged_shift_map)

    if DEBUG_OUTPUT:
        print('+++++')
        with open('/Users/gnowakow/Downloads/final_report_map_{}.json'.format(debug_ts), 'w') as f:
            f.write(json.dumps(final_report_map, indent=4, sort_keys=True))
        print('Printed final report map')
        print('+++++')

    return final_report_map

def simple_shift_formatting(final_report_map):
    for shift_date, shift_and_coverage in final_report_map.items():
        shift = shift_and_coverage['shift']
        coverage = shift_and_coverage['coverage']
        print('Shift: ({}) {} - {}'.format(create_shift_name(shift), date_simple_format(shift['start_dt']), date_simple_format(shift['end_dt'])))
        for hour_coverage in coverage:
            print('  {} - {} ({} hours): {}'.format(hour_coverage['start_dt'], hour_coverage['end_dt'], get_hours(key_to_date(hour_coverage['start_dt']), key_to_date(hour_coverage['end_dt'])), hour_coverage['who']))
        print("")

# Might consider this in the future: https://ptable.readthedocs.io/en/latest/tutorial.html  (at least for debugging/printing interactively ascii tables)
def format_html_shift_report(final_report_map):
    for shift_date, shift_and_coverage in final_report_map.items():
        shift = shift_and_coverage['shift']
        coverage = shift_and_coverage['coverage']
        summary = shift_and_coverage['shift-summary']

        max_members = -1
        for coverage_span in coverage:
            max_members = max(max_members, len(coverage_span['who'].split(',')))

        shift_content = '<h2>{}</h2>'.format(create_shift_name(shift))
        shift_table = '<table>'
        shift_table += '<tr><th>Start</th><th>End</th><th>Hours</th>{}</tr>'.format(''.join(['<th>Member</th>' for x in range(max_members)]))
        for coverage_span in coverage:
            shift_row = '<tr><td>{}</td><td>{}</td><td class="cell_hour">{}</td>'.format(
                key_to_date(coverage_span['start_dt']).strftime(OUTPUT_FMT_YMDHM), 
                key_to_date(coverage_span['end_dt']).strftime(OUTPUT_FMT_YMDHM),
                get_hours(key_to_date(coverage_span['start_dt']), key_to_date(coverage_span['end_dt']))
                )
            shift_row += ''.join(['<td>{}</td>'.format(x) for x in coverage_span['who'].split(',')])
            # TODO: Fill in blank cells with empty strings here
            num_blank_cells = max_members - len(coverage_span['who'].split(','))
            shift_row += ''.join(['<td></td>' for x in range(num_blank_cells)])
            shift_row += '</tr>'
            shift_table += shift_row

        shift_table += '</table>'
        shift_content += shift_table

        shift_content += '<h3>Shift Summary</h3>'
        shift_content += build_shift_summary_table(summary)

        template = None
        with open('/Users/gnowakow/Projects/EMS/TeamUp/docs/schedule_template.txt'.format(shift_date), 'r') as f:
            template = f.read()

        html_file = template.replace('<!-- Content -->', shift_content)

        output_filename = '/Users/gnowakow/Downloads/sample_report_{}.html'.format(date_to_key(dateutil.parser.isoparse(shift['start_dt'])))
        with open(output_filename, 'w') as f:
            f.write(html_file)


def build_shift_summary_table(summary) -> str:
    summary_table = '<table>'
    summary_table += '<tr><th>Member</th><th>Total Hours</th></tr>'
    for summary_key, summary_value in summary.items():
        summary_table += '<tr><td>{}</td><td>{}</td></tr>'.format(summary_key, summary_value)
    summary_table += '</table>'
    return summary_table

def collapse_into_like_shifts(merged_shift_map):
    """
    Given a map of shifts, collapse them into like shifts
    like shifts are consecutive shifts that have the same people working
    """
    final_report_map = {}
    # Collapse into like shifts
    for shift_date, shift_and_coverage in merged_shift_map.items():
        shift = shift_and_coverage['shift']
        coverage_by_hour = shift_and_coverage['coverage']

        collapsed_coverages = []

        previous_member_names = None
        start_hour = None
        previous_hour = None
        for hour_key in sorted(coverage_by_hour.keys()):
            coverage_offers_for_hour = coverage_by_hour[hour_key] # coverage_offers is a list of coverages for this hour (sorted by coverage level, name)
            if are_keys_consecutive(previous_hour, hour_key) and are_names_equal(previous_member_names, coverage_offers_for_hour):
                previous_hour = hour_key
            else:
                if previous_member_names is not None:
                    collapsed_coverages.append({'start_dt': start_hour, 'end_dt': date_to_key(add_hour_to_key(previous_hour)), 'who': previous_member_names})
                previous_member_names = concat_offer_names(coverage_offers_for_hour)
                start_hour = hour_key
                previous_hour = hour_key

        if previous_member_names is not None:
            collapsed_coverages.append({'start_dt': start_hour, 'end_dt': date_to_key(add_hour_to_key(previous_hour)), 'who': previous_member_names})

        final_report_map[shift_date] = {'shift': shift, 'coverage': collapsed_coverages, 'shift-summary': shift_and_coverage['shift-summary']}
    return final_report_map


def are_keys_consecutive(previous_hour, hour):
    if previous_hour is None:
        return False

    prev_date = datetime.datetime.strptime(previous_hour, HOUR_KEY_FMT)
    dt = datetime.timedelta(hours=1)
    hour_after_prev = prev_date + dt

    return datetime.datetime.strftime(hour_after_prev, HOUR_KEY_FMT) == hour        

def concat_offer_names(coverages):
    names = []
    for coverage in coverages:
        names.append('{} ({})'.format(coverage['who'], BRIEF_COVERAGE_DESCR_MAP.get(coverage['custom']['coverage_level'][0])))
    return ', '.join(names)

def are_names_equal(previous_names, coverages):
    if previous_names is None:
        return False

    names = concat_offer_names(coverages)
    return previous_names == names


if __name__ == '__main__':
    search_start = datetime.datetime.now().strftime(API_DATE_FORMAT_YMD)
    search_end = (datetime.datetime.now() + datetime.timedelta(days=5)).strftime(API_DATE_FORMAT_YMD)
    print('Searching from {} to {}'.format(search_start, search_end))
    requireds, coverages, errors, warnings = check_events(coverage_required_calendar, coverage_offered_calendar, search_start, search_end)
    print('====================================')
    print('Duty Shifts Found: {} errors and {} warnings'.format(len(errors), len(warnings)))
    report_errors(errors)

    final_report_map = report_shifts(coverage_required_calendar, coverage_offered_calendar, search_start, search_end, errors)
    format_html_shift_report(final_report_map)
    # simple_shift_formatting(final_report_map)

    requireds, coverages, errors, warnings = check_events(tango_required_calendar, tango_offered_calendar, search_start, search_end)
    print('====================================')
    print('Tango Shifts Found: {} errors and {} warnings'.format(len(errors), len(warnings)))
    report_errors(errors)
    print('====================================')



