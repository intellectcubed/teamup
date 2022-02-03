"""
TODO: Add logging as below: 
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
"""


import requests
import json
import dateutil.parser
import datetime
import sys
import os
import time
from common.correspondence_manager import CorrespondenceManager
from common.email_utils import send_html_email, send_email
import argparse
import common.date_utils as date_utils
import common.utils as utils
import common.html_formatter as html_formatter
import re
import traceback
import boto3

administrator_email = ['gmn314@yahoo.com']

api_key = os.environ['TEAMUP_API_KEY']

url = 'https://api.teamup.com'
collaborative_calendar_key = os.environ['COLLABORATIVE_CALENDAR_KEY_RO']

coverage_required_calendar = os.environ['COVERAGE_REQUIRED_CALENDAR']
coverage_offered_calendar = os.environ['COVERAGE_OFFERED_CALENDAR']
tango_required_calendar = os.environ['TANGO_REQUIRED_CALENDAR']
tango_offered_calendar = os.environ['TANGO_OFFERED_CALENDAR']


s3 = boto3.client('s3')
s3_bucket = 'shift-reports-{}-535096317903' #substitute agency
s3_bucket_name = None

errors_for_run = []

dynamodb = boto3.resource('dynamodb')

correspondence_manager = CorrespondenceManager(dynamodb)

member_table = dynamodb.Table('squad_members')

email_is_live = False


## ------------------
## EMail configuration
email_address_file = 'emails.json' # file containing email addresses
email_address_map = {} # Cache for email addresses -- 
# unstaffed shifts are sent to the below addess
shift_error_recipients = os.getenv('SHIFT_ERROR_RECIPIENTS', 'gmn314@yahoo.com').split(',') # Defaults to gmn314@yahoo.com
error_missing_email_address = ['gmn314@yahoo.com'] # If we cannot look up an email address for a member name, notify the recipients in this list

email_address_manager = None

# The below boolean determines if the script will prompt the user to confirm certain actions.
HEADLESS = False

COVERAGE_LEVEL_DESCR_MAP = {
    'crew_chief': 'Crew Chief',
    'emt': 'EMT over 18',
    'emt_under_18_': 'EMT under 18',
    'driver': 'Driver',
    'assistant': 'Assistant'
} 

BRIEF_COVERAGE_DESCR_MAP = {
    'crew_chief': 'CC',
    'emt': 'EMT > 18',
    'emt_under_18_': 'EMT < 18',
    'driver': 'Driver',
    'assistant': 'Assistant'
} 


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
        num_hours = date_utils.get_hours_parse(coverage['start_dt'], coverage['end_dt']) # for how many hours is this coverage offered?
        start_date = dateutil.parser.isoparse(coverage['start_dt'])
        for hour in range(num_hours):
            dt = datetime.timedelta(hours=hour)
            coverage_hour = start_date + dt
            date_hour_key = date_utils.date_to_key(coverage_hour)
            coverage_offered[date_hour_key] = coverage_offered.get(date_hour_key, [])
            coverage_offered[date_hour_key].append(coverage)

    return coverage_offered

def check_events(required_subcalendar_id, offered_subcalendar_id, start_dt, end_dt):
    """
    Check if the coverage offered is sufficient for the required coverage.
    """
    requireds = get_coverage_required(required_subcalendar_id, start_dt, end_dt)

    # Note: When getting the coverage offered, we will start from the previous day (1 day before start_dt) to get all of the events
    # that started the day before, and ended today, and one day after, to get all that started today but end tomorrow.
    start_before = date_utils.parse_date_add_hours(start_dt, -1*24, date_utils.API_DATE_FORMAT_YMD).strftime(date_utils.API_DATE_FORMAT_YMD)
    end_after = date_utils.parse_date_add_hours(end_dt, 2*24, date_utils.API_DATE_FORMAT_YMD).strftime(date_utils.API_DATE_FORMAT_YMD)

    coverages = get_coverage_offered(offered_subcalendar_id, start_before, end_after)

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
    hours = date_utils.get_hours_parse(required_coverage['start_dt'], required_coverage['end_dt'])
    for hour in range(hours):
        dt = datetime.timedelta(hours=hour)
        coverage_hour = start_date + dt
        date_hour_key = date_utils.date_to_key(coverage_hour)
        coverage_events_for_hour = coverage_events.get(date_hour_key, [])
        missing, warnings = is_hour_staffed(required_subcalendar_id, coverage_events_for_hour)

        if len(missing) > 0:
            crew_missing[date_hour_key] = missing

        if len(warnings) > 0:
            shift_warnings[date_hour_key] = warnings

    missing_ranges = consolidate_hours(crew_missing)
    return (missing_ranges, shift_warnings)

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
            elif date_utils.add_hour_to_key(sub_list[-1]) == date_utils.key_to_date(date):
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
                start_date = date_utils.key_to_date(date_set[0])
                end_date = date_utils.add_hour_to_key(date_set[-1])
                hours = date_utils.get_hours(start_date, end_date)
                missing_ranges.append({'start_dt': start_date.strftime(date_utils.OUTPUT_FMT_YMDHM), 'end_dt': end_date.strftime(date_utils.OUTPUT_FMT_YMDHM), 'hours': hours, 'error': key})

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
        try:
            roles[event['custom']['coverage_level'][0]] = roles.get(event['custom']['coverage_level'][0], 0) + 1
        except KeyError:
            print('Data Exception: Missing coverage level for event {}'.format(event))
            raise

    # is there a CC?
    if 'crew_chief' in roles:
        if roles['crew_chief'] > 1:
            warnings.append('Warning: more than one CC')
    else:
        missing.append('Crew Chief')
    
    if not ('driver' in roles or 'emt' in roles or ('crew_chief' in roles and roles['crew_chief'] > 1)):
        missing.append('Driver or EMT over 18')

    return (missing, warnings)

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


def report_errors(shift_errors):
    if len(shift_errors) == 0:
        return
    print('The folowing shifts have errors:')
    for shift in shift_errors:
        print('Shift: ({}) {} - {}'.format(utils.create_shift_name(shift['shift']), date_utils.date_simple_format(shift['shift']['start_dt']), 
            date_utils.date_simple_format(shift['shift']['end_dt'])))
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

def filter_shifts_before_today(search_start, shifts):
    filtered_shifts = []

    for shift in shifts:
        if dateutil.parser.isoparse(shift['start_dt']) < date_utils.convert_date_to_ny(datetime.datetime.strptime(search_start, date_utils.API_DATE_FORMAT_YMD)):
            print('Skipping past shift: {}'.format(shift['start_dt']))
        else:
            filtered_shifts.append(shift)
    return filtered_shifts


def expand_event(event):
    """
    Given an event, expand it into a list of events
    return key, [event]
    """
    # key = hour
    # value = event

    expanded_events = {}
    num_hours = date_utils.get_hours_parse(event['start_dt'], event['end_dt']) # for how many hours is this coverage offered?
    start_date = dateutil.parser.isoparse(event['start_dt'])
    for hour in range(num_hours):
        dt = datetime.timedelta(hours=hour)
        coverage_hour = start_date + dt
        date_hour_key = date_utils.date_to_key(coverage_hour)
        expanded_events[date_hour_key] = expanded_events.get(date_hour_key, [])
        expanded_events[date_hour_key].append(event)
    
    return expanded_events

DEBUG_OUTPUT = False

def report_shifts(agency, coverage_required_calendar, coverage_offered_calendar, search_start, search_end, errors):

    shifts_with_errors = set()

    for shift in errors:
        shifts_with_errors.add(shift['shift']['id'])

    
    """
    Returning: 
        {
            "2022-01-08T11:00:00-05:00": {
                "coverage": [
                    {
                        "end_dt": "2022010823",
                        "start_dt": "2022010818",
                        "who": "Steph Landau (EMT > 18)"
                    },
                    {
                        "end_dt": "2022010901",
                        "start_dt": "2022010823",
                        "who": "George Nowakowski (CC), Steph Landau (EMT > 18)"
                    }
                ],
                "shift": {
                    "all_day": false,
                    "attachments": [],
                    "creation_dt": "2022-01-04T13:24:29-05:00",
                    "custom": {},
                    "delete_dt": null,
                    "end_dt": "2022-01-09T01:00:00-05:00",
                    "id": "1081908428",
                    "location": "",
                    "notes": null,
                    "readonly": true,
                    "remote_id": null,
                    "ristart_dt": null,
                    "rrule": "",
                    "rsstart_dt": null,
                    "series_id": null,
                    "start_dt": "2022-01-08T11:00:00-05:00",
                    "subcalendar_id": 10358690,
                    "subcalendar_ids": [
                        10358690
                    ],
                    "title": "MRS Duty: Covering 34 (Green Knoll)",
                    "tz": null,
                    "update_dt": null,
                    "version": "4c69a25fc459",
                    "who": ""
                },
                "shift-summary": {
                    "George Nowakowski": 2,
                    "Steph Landau": 7
                }
            }
            ]
        }
    """
    debug_ts = int(time.time())

    shifts = get_events(search_start, search_end, coverage_required_calendar)

    coverage_start = date_utils.parse_date_add_hours(search_start, -24, date_utils.API_DATE_FORMAT_YMD)
    coverage_end = date_utils.parse_date_add_hours(search_end, 24, date_utils.API_DATE_FORMAT_YMD)

    coverages = get_events(coverage_start, coverage_end, coverage_offered_calendar)

    shift_map = events_to_map(filter_shifts_before_today(search_start, shifts['events']))
    shift_keys = sorted(shift_map.keys())

    coverage_map = events_to_map(coverages['events'])
    coverage_keys = sorted(coverage_map.keys())

    # key = date, value = {shift, [coverage]}
    merged_shift_map = {}

    for shift_key in shift_keys:
        shifts_ = shift_map[shift_key]
        for shift in shifts_:
            if shift['id'] in shifts_with_errors:
                # print('Skipping shift with id: {}'.format(shift['id']))
                continue
            # key = member_name, hours = {string, int}
            shift_summary_map = {}
            shift_date = shift['start_dt']
            covers_for_shift = {}
            for coverage_key in coverage_keys:
                coverages_ = coverage_map[coverage_key]
                for coverage in coverages_:
                    check_for_email_address(agency, coverage)

                    #TODO: If coverage offer started within the shift, but end is beyond end of shift, it will be ignored.  Should be counted!!
                    if coverage_key >= shift_key and coverage_key < shift['end_dt']:
                        shift_summary_map[coverage['who']] = shift_summary_map.get(coverage['who'], 0) + date_utils.get_hours_parse(coverage['start_dt'], coverage['end_dt'])
                        events_by_hour = expand_event(coverage)
                        for hour_key, events in events_by_hour.items():
                            covers_for_shift[hour_key] = covers_for_shift.get(hour_key, [])
                            covers_for_shift[hour_key].extend(events)
            merged_shift_map[shift_date] = {'shift': shift, 'coverage': covers_for_shift, 'shift-summary': shift_summary_map}

    # For every hour, sort the coverages: by coverage level, then by name
    for shift_date, shift_and_coverage in merged_shift_map.items():
        shift = shift_and_coverage['shift']
        coverage = shift_and_coverage['coverage']
        try:
            for hour_key, coverages in coverage.items():
                coverages.sort(key=lambda x: (x['custom']['coverage_level'][0], x['who']))
                coverage[hour_key] = coverages
        except KeyError:
            errors_for_run.append({'shift': shift, 'error': 'No coverage level found for shift'})

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

def check_for_email_address(agency, coverage):
    """
    Confirm that email address exists in the email_address_map.  If it does not, check for the presence of a notes field.  If notes exists, and it contains a string like: 
    "email: email@domain" then add that email address to the email_address_map, and also save it in the file
    """

    member_name = coverage['who']
    if member_name in email_address_map:
        return True

    email_address = get_email_address_from_notes(coverage)
    if email_address:
        save_email_address(agency, member_name, email_address)
    else:
        email_address = get_email_from_db(agency, member_name)

    if email_address:
        email_address_map[member_name] = email_address

    return email_address

def simple_shift_formatting(final_report_map):
    for shift_date, shift_and_coverage in final_report_map.items():
        shift = shift_and_coverage['shift']
        coverage = shift_and_coverage['coverage']
        print('Shift: ({}) {} - {}'.format(utils.create_shift_name(shift), date_utils.date_simple_format(shift['start_dt']), date_utils.date_simple_format(shift['end_dt'])))
        for hour_coverage in coverage:
            print('  {} - {} ({} hours): {}'.format(hour_coverage['start_dt'], hour_coverage['end_dt'], date_utils.get_hours(date_utils.key_to_date(hour_coverage['start_dt']), 
                date_utils.key_to_date(hour_coverage['end_dt'])), hour_coverage['who']))
        print("")

def build_email_list(summary):
    email_addresses = []
    no_address_for_member = []

    for member_name, member_hours in summary.items():
        if member_name in email_address_map:
            email_addresses.append(email_address_map[member_name])
        else:
            no_address_for_member.append(member_name)

    return email_addresses, no_address_for_member

def collapse_into_like_shifts(merged_shift_map):
    """
    Given a map of shifts, collapse them into like shifts
    like shifts are consecutive shifts that have the same people working

    Returns:


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
                    collapsed_coverages.append({'start_dt': start_hour, 'end_dt': date_utils.date_to_key(date_utils.add_hour_to_key(previous_hour)), 'who': previous_member_names})
                previous_member_names = concat_offer_names(coverage_offers_for_hour)
                start_hour = hour_key
                previous_hour = hour_key

        if previous_member_names is not None:
            collapsed_coverages.append({'start_dt': start_hour, 'end_dt': date_utils.date_to_key(date_utils.add_hour_to_key(previous_hour)), 'who': previous_member_names})

        final_report_map[shift_date] = {'shift': shift, 'coverage': collapsed_coverages, 'shift-summary': shift_and_coverage['shift-summary']}

    return final_report_map


def are_keys_consecutive(previous_hour, hour):
    if previous_hour is None:
        return False

    prev_date = datetime.datetime.strptime(previous_hour, date_utils.HOUR_KEY_FMT)
    dt = datetime.timedelta(hours=1)
    hour_after_prev = prev_date + dt

    return datetime.datetime.strftime(hour_after_prev, date_utils.HOUR_KEY_FMT) == hour        

def concat_offer_names(coverages):
    names = []
    for coverage in coverages:
        names.append('{} <span class="duty_role">({})</span>'.format(coverage['who'], BRIEF_COVERAGE_DESCR_MAP.get(coverage['custom']['coverage_level'][0])))
    return ', '.join(names)

def are_names_equal(previous_names, coverages):
    if previous_names is None:
        return False

    names = concat_offer_names(coverages)
    return previous_names == names


def should_send_email(agency, email_recepients, category, context_date_str):
    if not email_is_live:
        return False

    notification_was_sent = correspondence_manager.was_notification_sent(agency, category, context_date_str, email_recepients)

    # If not HEADLESS, prompt will override whether it was already sent!
    if HEADLESS == False:
        if input("{} recipients already sent: {} Should the email be sent? (y/n) "
            .format(len(email_recepients), notification_was_sent)) == 'y':
            return True
        else:
            return False

    # if HEADLESS, send the email if not already sent
    return not notification_was_sent


def send_html_email(agency, email_recepients, context_date, category, subject, html_body):
    """
    if category = 'shift_notification', context_date is the start date of the shift
    if category = 'error_notification', context_date is the date of the error

    """
    cc_list = []
    if html_body is None or len(html_body) == 0:
        print('html_file is None or empty, nothing to do')
        return

    # Get the YEAR_MONTH_DAY_HOUR of the context date
    context_date_str = datetime.datetime.strftime(context_date, date_utils.HOUR_KEY_FMT)
    if should_send_email(agency, email_recepients, category, context_date_str):
        send_html_email(email_recepients, cc_list, subject, html_body)
        save_notification_sent(agency, category, context_date_str, email_recepients)


def save_notification_sent(agency, category, shift_start, email_list):
    return correspondence_manager.save_notification_sent(agency, category, shift_start, email_list)


def process_html_results(agency, html_map, final_report_map):
    """
    Iterate through the final_report_map.  For each shift:
        * Create an email mailing list
        * Create an html file
        * Send an email

        Note: If one or more recipients cannot be found for a shift, send an email to the script owner for manual intervention
    """
    for shift_date, shift_and_coverage in final_report_map.items():
        shift = shift_and_coverage['shift']
        shift_date_formatted = dateutil.parser.isoparse(shift['start_dt']).strftime('%A_%Y-%m-%d-hour-%H')
        coverage = shift_and_coverage['coverage']
        summary = shift_and_coverage['shift-summary']

        email_list, no_email_found = build_email_list(summary)
        if len(no_email_found) > 0:
            email_body = 'Problem while sending email for shift {}.  No email address found for the following members: {}'.format(shift_date, no_email_found)
            send_email(error_missing_email_address, [], 'TeamUp Script could not find email addresses for members listed', email_body)
            continue

        send_html_email(agency, email_list, date_utils.convert_date_to_ny(dateutil.parser.isoparse(shift['start_dt'])), 'shift_notification', 'Shift coming up soon', html_map[shift_date])

        # Also, write the html to a file
        write_resulting_html('shift_report_{}.html'.format(shift_date_formatted), html_map[shift_date])


def process_html_errors(agency, error_html):
    if error_html is not None:
        send_html_email(agency, shift_error_recipients, date_utils.get_now_tz(), 'error_notification', 'Unstaffed Shifts', error_html)

        write_resulting_html('error_list.html', error_html)

def write_resulting_html(file_name, html_body):
    s3.put_object(
        Bucket=s3_bucket_name,
        Key= '{}/{}'.format(date_utils.get_current_day_key(), file_name),
        Body=html_body
    )

def read_email_addresses():
    with open(email_address_file, 'r') as f:
        return json.load(f)

def get_email_from_db(agency, member_name):
    resp = member_table.get_item(
        Key={
            'agency':agency,
            'member_name': member_name
        }
    )
    if 'Item' in resp and 'email_address' in resp['Item']:
        return resp['Item']['email_address']


def get_email_address_from_notes(coverage):
    if 'notes' in coverage and \
        coverage['notes'] is not None and \
        'email' in coverage['notes']:

        lst = re.findall('\S+@\S+', coverage['notes'])
        if len(lst) == 0:
            return

        email_address = lst[0]
        if '</p>' in email_address:
            email_address = email_address[:-4]

        return email_address


def save_email_address(agency, member_name, email_address):
    member_table.put_item(
        Item={
            'agency': agency,
            'member_name': member_name,
            'email_address': email_address
        }
    )


def get_command_arguments():
    global HEADLESS
    global email_is_live

    # Instantiate the parser
    parser = argparse.ArgumentParser(description='Optional app description')        

    # Required positional argument
    parser.add_argument('--start_date', default=datetime.datetime.now().strftime(date_utils.API_DATE_FORMAT_YMD), 
        help='Start date of the report in YYYY-MM-DD format', required=False)

    parser.add_argument('--end_date', default=(datetime.datetime.now() + datetime.timedelta(days=5)).strftime(date_utils.API_DATE_FORMAT_YMD),
        help='End date of the report in YYYY-MM-DD format', required=False)

    parser.add_argument('--send_email', help='Boolean should the email be sent?', action='store_true', required=False)
    parser.add_argument('--headless', help='Boolean should the script prompt?', action='store_true', required=False)

    # Parse the arguments
    cmd_args = parser.parse_args()

    HEADLESS = cmd_args.headless
    email_is_live = cmd_args.send_email
    print('===============================================')
    print('Generating report for {} to {}'.format(cmd_args.start_date, cmd_args.end_date))
    print('Will send email? {}'.format(cmd_args.send_email))
    print('===============================================')    

    if HEADLESS == False and input("are you sure? (y/n) ") != "y":
        exit()

    return cmd_args

def init_from_cmd():
    global s3_bucket_name
    """
    Initialize the script when invoked from the command line
    """
    global email_address_map

    # email_address_map = read_email_addresses()
    s3_bucket_name = s3_bucket.format('martinsville')

    return get_command_arguments()

def process(agency, start_date, end_date):
    requireds, coverages, errors, warnings = check_events(coverage_required_calendar, coverage_offered_calendar, start_date, end_date)
    print('====================================')
    print('Duty Shifts Found: {} errors: {} warnings: {}'.format(len(requireds), len(errors), len(warnings)))
    report_errors(errors)

    html_errors = html_formatter.format_html_report_errors(errors, start_date, 99)
    process_html_errors(agency, html_errors)

    final_report_map = report_shifts(agency, coverage_required_calendar, coverage_offered_calendar, start_date, end_date, errors)
    html_map = html_formatter.format_html_shift_report(final_report_map)
    process_html_results(agency, html_map, final_report_map)

    requireds, coverages, errors, warnings = check_events(tango_required_calendar, tango_offered_calendar, start_date, end_date)
    print('====================================')
    print('Tango Shifts Found: {} errors: {} warnings: {}'.format(len(requireds), len(errors), len(warnings)))
    report_errors(errors)
    print('====================================')



def lambda_handler(event, context):
    global s3_bucket_name
    global HEADLESS
    global email_is_live

    HEADLESS = True
    email_is_live = True
    agency = event['agency']

    s3_bucket_name = s3_bucket.format(agency)

    start_date = datetime.datetime.now().strftime(date_utils.API_DATE_FORMAT_YMD)
    end_date = (datetime.datetime.now() + datetime.timedelta(days=5)).strftime(date_utils.API_DATE_FORMAT_YMD)

    try:
        process(agency, start_date, end_date)
    except Exception as e:
        invocation_params = 'agency: {} start_date: {} end_date: {}'.format(agency, start_date, end_date)
        exception_details = traceback.format_exc()
        email_body = 'Exception in lambda_handler: \n called with: {}\n\n{}'.format(invocation_params, exception_details)
        send_email(administrator_email, [], 'Exception in check_coverage lambda handler', email_body)
        exit()

if __name__ == '__main__':
    args = init_from_cmd()
    agency = 'martinsville'

    try:
        process(agency, args.start_date, args.end_date)
    except Exception as e:
        invocation_params = 'agency: {} start_date: {} end_date: {}'.format(agency, args.start_date, args.end_date)
        exception_details = traceback.format_exc()
        email_body = 'Exception in lambda_handler: \ncalled with: {}\n\n{}'.format(invocation_params, exception_details)
        send_email(administrator_email, [], 'Exception in check_coverage lambda handler', email_body)
        exit()
