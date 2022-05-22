"""
source ~/Downloads/env/bin/activate


Create input file with the following columns: 

subcalendar_id,start_dt,end_dt,squad,title

Sample Row: 
10364691,2022-01-01T06:00:00-05:00,2022-01-02T06:00:00-05:00,finderne_35_,Shift

Valid values for squad:
green_knoll_34_
finderne_35_
bradley_gardens_39_
manville_42_
martinsville_43_
somerville_54_

Sample Command Line:
python create_events.py --calendar_key coverage_required --source_file shifts/feb_2022_coverage_required.csv
"""

import csv
from csv import DictReader
import calendar
from datetime import datetime
from datetime import timedelta
import argparse
import os
import dateutil

from anyio import create_event
import common.teamup_utils as teamup_utils
import common.date_utils as date_utils
import common.utils as utils
import sys
from common.config_data import CoverageLevels, EventCalendarsKeys, RunConfig, read_configuration, is_coverage_level, read_trigger, agency_map


url = 'https://api.teamup.com'
days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
run_config: RunConfig = None

test_event_ids_folder = 'test_cases/event_ids'

"""
-----------------------------------------------------------------------------------------------------------------------
## Setup Python environment
```
source ~/Downloads/env/bin/activate
source secrets.sh

```
-------------------------------------------------------------------------------------------------------------------------
# Coverage Required (from collab calendar)
## Download calendar (if creating collaborative events)
Go to Google Docs (Collaborative Spreadsheet) - click on the tab for the month and do a "Download as CSV" 

### To create events (Coverage required from Collaborative Spreadsheet): 
python3 create_events.py --calendar coverage_required --spreadsheet --year 2022 --month 6 --source_file '/Users/gnowakow/Downloads/Central Somerset EMS Collaborative Schedule 2022 - June.csv' --trigger_file ./triggers/martinsville_trigger.json

### To create events using a file (recurring or individual):
python3 create_events.py --calendar coverage_required --month 6 --year 2022 --auto_populate_shifts --source_file './shifts/day_of_week_required.csv' --trigger_file ./triggers/martinsville_trigger.json

#### File Format: 
(Monday = 0, Sunday = 6)

day_of_week,skip_days,absolute_date,start_time,end_time,title
0,13|20,,00:00,06:00,43 Covering 34/43
1,,,18:00,06:00,43 Covering 34/43
,,,2022-06-04,18:00,06:00,43 Covering 43

Note that the above says: 
Line 1: Create recurring on Mondays, every Monday except 13th and 20th
Line 2: Create recurring Tuesdays
Line 3: Create one event: 22-06-04 at 6:00-6:00

-------------------------------------------------------------------------------------------------------------------------
# Coverage Required (from your own .csv)
### To create events (Coverage required): 
python3 create_events.py --calendar coverage_required --source_file /Users/gnowakow/Projects/EMS/TeamUp/shifts/feb_2022_coverage_required.csv

Expected input for coverage_required calendar: [start_dt, end_dt, title]
Example: 2022-02-01T18:00:00,2022-02-02T06:00:00,MRS Duty: Covering 34 (Green Knoll) and 35 (Finderne)

-------------------------------------------------------------------------------------------------------------------------
# Coverage Offered (defaults using the "regulars" csv)
python3 create_events.py --calendar coverage_offered --default_coverage --month 6 --year 2022 --trigger_file ./triggers/martinsville_trigger.json --preview
-------------------------------------------------------------------------------------------------------------------------
# Coverage Offered (from your own .csv)
### To create events (Coverage offered):
python3 create_events.py --calendar coverage_offered --source_file /Users/gnowakow/Projects/EMS/TeamUp/shifts/feb_2022_coverage_offered.csv

Expected input for coverage_offered: [start_dt, end_dt, role, who]
Example: 2022-02-14T18:00:00,2022-02-15T00:00:00,crew_chief,Jim Ross

-------------------------------------------------------------------------------------------------------------------------
### To delete records created: 
python3 create_events.py --delete_all --calendar coverage_offered --source_file /Users/gnowakow/Downloads/CreatedCovers_0428.txt

### Query and delete events:
python3 create_events.py --calendar coverage_required --start_date 2022-02-01 --end_date 2022-02-30 --get_event_ids
python3 create_events.py --calendar coverage_required --source_file /Users/gnowakow/Projects/EMS/TeamUp/shifts/coverage_required_2022-03-01_2022-03-31.csv --delete_all

-------------------------------------------------------------------------------------------------------------------------
"""

def add_events(source_file, sub_calendar_key):
    print('Going to create events in calendar: {} Sub calendar: {} using API key: {}'.format(run_config.calendar_admin_key, sub_calendar_key, run_config.api_key))
    num_events = 0
    event_id_file = source_file.replace('.csv', '_event_ids.csv')
    with open(event_id_file, 'w') as events_file:
        with open(source_file, 'r') as f:
            rdr = csv.reader(f)
            for row in rdr:
                if len(row) == 0:
                    continue
                event = row_to_event(sub_calendar_key, row)
                print(event)

                new_event = teamup_utils.create_event(event, run_config.calendar_admin_key, run_config.api_key)
                if new_event is None:
                    print('Failed to create event: {}'.format(event))
                    sys.exit(1)

                # print('Created event: {}'.format(new_event))
                events_file.write(str(new_event['event']['id']) + '\n')
                num_events += 1
    return num_events

def row_to_event(sub_calendar_id, row):
    # print('calling row_to_event with: {}'.format(sub_calendar_id))
    if sub_calendar_id == translate_calendar_key('coverage_required'):
        return {
            'subcalendar_id': sub_calendar_id,
            'start_dt': row[0],
            'end_dt': row[1],
            'custom': {
                'coverage_level': 'do_not_select'
            },            
            'title': row[2]
        }
    elif sub_calendar_id == translate_calendar_key('coverage_offered'):
        return {
            'subcalendar_id': sub_calendar_id,
            'start_dt': row[0],
            'end_dt': row[1],
            'custom': {
                'coverage_level': row[2]
            },
            'who': row[3]
        }
    else:
        raise Exception('Invalid sub calendar id: {}'.format(sub_calendar_id))

def row_to_event2(sub_calendar, row):
    if 'coverage_level' in row:
        coverage_level = run_config.teamup_config.level_mappings[row['coverage_level']]
    else:
        coverage_level = run_config.teamup_config.level_mappings[CoverageLevels.DO_NOT_SELECT.value]

    msg = {
        'subcalendar_id': translate_calendar_key(sub_calendar),
        'start_dt': row['start_dt'],
        'end_dt': row['end_dt'],
        'custom': {
            'coverage_level': coverage_level
        }
    }

    if 'title' in row:
        msg['title'] = row['title']
    if 'who' in row:
        msg['who'] = row['who']
    return msg


def translate_calendar_key(calendar_key):
    if calendar_key == EventCalendarsKeys.REQUIRED.value:
        return run_config.teamup_config.coverage_required_calendar
    elif calendar_key == EventCalendarsKeys.OFFERED.value:
        return run_config.teamup_config.coverage_offered_calendar
    else:
        raise Exception('Invalid calendar key: {}'.format(calendar_key))

def subcalendar_from_event(event):
    if event['subcalendar_id'] == run_config.teamup_config.coverage_required_calendar:
        return EventCalendarsKeys.REQUIRED
    elif event['subcalendar_id'] == run_config.teamup_config.coverage_offered_calendar:
        return EventCalendarsKeys.OFFERED
    else:
        raise Exception('Invalid sub calendar id: {}'.format(event['subcalendar_id']))

def get_admin_key_for_calendar(calendar_key):
    if calendar_key == EventCalendarsKeys.REQUIRED:
        return run_config.teamup_config.required_calendar_key_admin
    elif calendar_key == EventCalendarsKeys.OFFERED:
        return run_config.teamup_config.offered_calendar_key_admin
    else:
        raise Exception('Invalid calendar key: {}'.format(calendar_key))

def create_test_cases(coverage_required_file, coverage_offered_file):
    print('Setting up test calendar')

    scenarios_start_date = datetime.max
    scenarios_end_date = datetime.min

    coverage_required_events = []
    with open(coverage_required_file, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if len(row) > 0:
                event = row_to_event2(EventCalendarsKeys.REQUIRED, row)
                scenarios_start_date = min(scenarios_start_date, dateutil.parser.isoparse(event['start_dt']))
                scenarios_end_date = max(scenarios_end_date, dateutil.parser.isoparse(event['end_dt']))
                coverage_required_events.append(event)

    coverage_offered_events = []
    with open(coverage_offered_file, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if len(row) > 0:
                event = row_to_event2(EventCalendarsKeys.OFFERED, row)
                scenarios_start_date = min(scenarios_start_date, dateutil.parser.isoparse(event['start_dt']))
                scenarios_end_date = max(scenarios_end_date, dateutil.parser.isoparse(event['end_dt']))
                coverage_offered_events.append(event)

    print('Scenarios start date: {} endDate: {}'.format(scenarios_start_date, scenarios_end_date))
    existing_required_events = teamup_utils.get_events(scenarios_start_date, scenarios_end_date, run_config.teamup_config.all_calendar_key_ro, translate_calendar_key(EventCalendarsKeys.REQUIRED), run_config.teamup_config.teamup_api_key)
    existing_offered_events = teamup_utils.get_events(scenarios_start_date, scenarios_end_date, run_config.teamup_config.all_calendar_key_ro, translate_calendar_key(EventCalendarsKeys.OFFERED), run_config.teamup_config.teamup_api_key)

    print('========================================================================================================================')
    print('You are about to operate on the date range: {} - {}'.format(scenarios_start_date, scenarios_end_date))
    print('For the agency: {}'.format(run_config.agency))
    print('You will delete the following events:')
    print('\tRequired events: {}'.format(len(existing_required_events['events'])))
    print('\tOffered events: {}'.format(len(existing_offered_events['events'])))
    print('You will create: {} required events'.format(len(coverage_required_events)))
    print('You will create: {} offered events'.format(len(coverage_offered_events)))
    print('========================================================================================================================')
    print('are you sure? (y/n)')
    answer = input()
    if answer.lower()!= 'y':
        print('Aborting')
        sys.exit(1)

    print('== Deleting existing events ==')
    for event in existing_required_events['events']:
        teamup_utils.delete_event(event['id'], run_config.teamup_config.required_calendar_key_admin, run_config.teamup_config.teamup_api_key)
    for event in existing_offered_events['events']:
        teamup_utils.delete_event(event['id'], run_config.teamup_config.offered_calendar_key_admin, run_config.teamup_config.teamup_api_key)

    print('== Creating new events ==')
    for event in coverage_required_events:
        new_event = teamup_utils.create_event(event, run_config.teamup_config.required_calendar_key_admin, run_config.teamup_config.teamup_api_key)
        print('Created required event: {} with ID: {}'.format(new_event['event']['start_dt'], new_event['event']['id']))

    for event in coverage_offered_events:
        new_event = teamup_utils.create_event(event, run_config.teamup_config.offered_calendar_key_admin, run_config.teamup_config.teamup_api_key)
        print('Created offered event: {} with ID: {}'.format(new_event['event']['start_dt'], new_event['event']['id']))


def delete_all_events(id_file):
    with open(id_file, 'r') as f:
        for event_id in f:
            # print('Deleting event: {} subcal: {} api-key: {}'.format(event_id, sub_calendar_key, api_key))
            teamup_utils.delete_event(event_id.strip(), run_config.calendar_admin_key, run_config.api_key)


def query_save_events(calendar_key, start_date, end_date):
    """
    Query TeamUp for events in the given date range and save them to a file
    Saves to file named: <calendar_key>_<start_date>_<end_date>.txt
    Example: coverage_required_2022-02-01_2022-02-30.txt
    """
    if start_date > '2021-12-31':
        if input('Start date is greater than 2021-12-31, are you sure? (y/n) ') != 'y':
            exit()  

    current_directory = os. getcwd()
    filename = '{}/shifts/{}_{}_{}.csv'.format(current_directory, calendar_key, start_date, end_date)
    if os.path.isfile(filename) is True:
        print('File {} already exists'.format(filename))
        os.remove(filename)

    utils.clear_relative_path(test_event_ids_folder)
    events = teamup_utils.get_events(start_date, end_date, run_config.calendar_ro_key, translate_calendar_key(calendar_key), run_config.api_key)

    with open(filename, 'w') as f:
        for event in events['events']:
            print('id: {} start: {} end: {} who: {} title: {}'.format(event['id'], event['start_dt'], event['end_dt'], event['who'], event['title']))
            f.write(event['id'] + '\n')

    print('created file: {}'.format(filename))

def check_is_weekend(month, day_num, year):
    d = datetime(year, month, day_num)
    return d.weekday() > 4


def create_event(event, existing_events):
    for existing_event in existing_events['events']:
        if date_utils.chop_dst(existing_event['start_dt']) == event['start_dt'] and date_utils.chop_dst(existing_event['end_dt']) == event['end_dt']:
            print('Event already exists: {}'.format(existing_event['id']))
            return
    new_event = teamup_utils.create_event(event, get_admin_key_for_calendar(subcalendar_from_event(event)), run_config.teamup_config.teamup_api_key)
    if new_event is None:
        print('Failed to create event: {}'.format(event))
        sys.exit(1)
    print('Created event: {} with ID: {}'.format(new_event['event']['start_dt'], new_event['event']['id']))


def find_events_to_remove(existing_events, spreadsheet_events):
    events_to_delete = []
    for existing_event in existing_events['events']:
        found = False
        for spreadsheet_event in spreadsheet_events:
            if date_utils.chop_dst(existing_event['start_dt']) == spreadsheet_event['start_dt'] and date_utils.chop_dst(existing_event['end_dt']) == spreadsheet_event['end_dt']:
                found = True
                break
        if not found:
            events_to_delete.append(existing_event)
    return events_to_delete

def get_period(month, year):
    period_start_date = datetime(year, month, 1)
    period_end_date = datetime(year, month, calendar.monthrange(year, month)[1])
    return (period_start_date, period_end_date)

def process_spreadsheet(filename, calendar_key, month, year):
    period = get_period(month, year)
    existing_events = teamup_utils.get_events(period[0], period[1], run_config.calendar_ro_key, translate_calendar_key(calendar_key), run_config.api_key)

    days_staffed = [0] * 7
    total_hours = 0

    events_to_create = []

    with open(filename, 'r') as f:
        for i in range(4):
            next(f)
        reader = csv.reader(f)
        for row in reader:
            day = row[1]
            crew_1 = row[2]
            crew_2 = row[3]
            crew_1_parts = row[2].split(' ')
            crew_2_parts = row[3].split(' ')

            if crew_1_parts[0] == '43' or crew_2_parts[0] == '43':
                if crew_1_parts[0] == '43':
                    title = crew_1
                else:
                    title = crew_2

                morning_date = datetime(year, month, int(day), 6, 0, 0)
                morning_event_start_date = morning_date.isoformat()
                morning_event_end_date = datetime(year, month, int(day), 18, 0, 0).isoformat()

                next_day = morning_date + timedelta(days=1)
                evening_event_start_date = datetime(year, month, int(day), 18, 0, 0).isoformat()
                evening_end_date = datetime(next_day.year, next_day.month, next_day.day , 6, 0, 0).isoformat()

                days_staffed[morning_date.weekday()] += 1

                events_to_create.append(row_to_event(translate_calendar_key(calendar_key), [evening_event_start_date, evening_end_date, title]))
                total_hours += 12

                # If weekend, create two events: day and night shift
                if check_is_weekend(month, int(day), year):
                    events_to_create.append(row_to_event(translate_calendar_key(calendar_key), [morning_event_start_date, morning_event_end_date, title]))

                    # create_event(morning_event, existing_events)
                    total_hours += 12

    events_to_remove = find_events_to_remove(existing_events, events_to_create)

    for event in events_to_create:
        create_event(event, existing_events)

    if len(events_to_remove) > 0:
        print('Should remove the below events as they are not on the spreadsheet:')
        for event_to_remove in events_to_remove:
            print('Date: {} id: {}'.format(event_to_remove['start_dt'], event_to_remove['id']))
    
    print('===== Statistics =====')
    print('Days staffed:')
    for day in range(7):
        print('{}: {}'.format(days_of_week[day], days_staffed[day]))
        day += 1    
    print('Total hours: {}'.format(total_hours))

def process_spreadsheet_v2(filename, calendar_key, month, year):
    """
    This parses the csv from the latest version of the spreadsheet.
    Notable differences:
    1) Since some cells are split - we will replace columns with values from the previous row
    2) Need to pull only events for the indicated squad
    """

    def create_alias_row(header_row):
        new_header = []
        for hdr in header_row:
            if hdr in new_header:
                counter = 1
                alias_col = '{}.{}'.format(hdr, counter)
                while alias_col in new_header:
                    counter += 1
                    alias_col = '{}.{}'.format(hdr, counter)
                new_header.append(alias_col)
            else:
                new_header.append(hdr)
        
        return new_header

    def row_to_event(row, title):
        day = int(row['Day'])
        (start_date, end_date) = utils.create_start_end_dates(year, month, day, row['Hours'])
        return {
            'subcalendar_id': translate_calendar_key(calendar_key),
            'start_dt': datetime.isoformat(start_date),
            'end_dt': datetime.isoformat(end_date),
            'custom': {
                'coverage_level': 'do_not_select'
            },            
            'title': title
        }


    period = get_period(month, year)
    existing_events = teamup_utils.get_events(period[0], period[1], run_config.teamup_config.all_calendar_key_ro, translate_calendar_key(calendar_key), run_config.teamup_config.teamup_api_key)

    events_to_create = []
    skip_past = 1

    with open(filename, 'r') as f:
        for i in range(skip_past):
            next(f)
        reader = csv.reader(f)
        header_row = None
        prev_row = None
        for row in reader:
            if header_row is None:
                header_row = create_alias_row(row)
                print('Header row: {}'.format(header_row))
                continue

            # Create a new row with the values from the previous row
            row = dict(zip(header_row, row))

            # Spreadsheet has a summary at the bottom.  We know we are in the summary when we see the first row with a value of Squad for Day
            if row['Day'] == 'Squad':
                break

            # This might be a row with missing information because the row was split.  Fill in missing values from previous row
            if prev_row is not None and len(row['Day']) == 0:
                row['Day'] = prev_row['Day']
                row['Tango'] = prev_row['Tango']

            if row['Squad'].startswith(agency_map[run_config.agency]) or row['Squad.1'].startswith(agency_map[run_config.agency]):
                if row['Squad'].startswith(agency_map[run_config.agency]):
                    title = row['Squad']
                else:
                    title = row['Squad.1']
                title = title.replace('[', ' Covering [')

                events_to_create.append(row_to_event(row, title))

            prev_row = row

    events_to_remove = find_events_to_remove(existing_events, events_to_create)
    for event in events_to_create:
        create_event(event, existing_events)

    if len(events_to_remove) > 0:
        print('Should remove the below events as they are not on the spreadsheet:')
        for event_to_remove in events_to_remove:
            print('Date: {} id: {}'.format(event_to_remove['start_dt'], event_to_remove['id']))


def create_cover_event(member_name, start_dt, end_dt, coverage_level):
    return {
            'subcalendar_id': run_config.teamup_config.coverage_offered_calendar,
            'start_dt': start_dt.isoformat(),
            'end_dt': end_dt.isoformat(),
            'custom': {
                'coverage_level': run_config.teamup_config.level_mappings[coverage_level]
            },
            'who': member_name
        }

def get_coverage_span(required_start_date, required_end_date, offer_day_of_week, offer_start_time, offer_end_time):
    """
    For the given required_start_date - required_end_date, return the span of dates that fall within the required
    coverage time.
    """

    if offer_day_of_week == required_start_date.weekday():
        context_date = required_start_date
    elif offer_day_of_week == required_end_date.weekday():
        context_date = required_end_date
    else:
        return

    # Bring the offer start, end times within the context of the required start and end dates
    offer_span = date_utils.span_for_date(context_date, offer_start_time, offer_end_time)
    # print('offer DOW: {} offer_span: {} - {}'.format(offer_day_of_week, offer_span[0].isoformat(), offer_span[1].isoformat()))

    # If the offer span is completely outside the required span, return None
    if offer_span[0] < required_end_date and offer_span[1] > required_start_date:
        return max(offer_span[0], required_start_date), min(offer_span[1], required_end_date)


def is_duplicate_offer(member_name, coverage_hours, existing_offers):
    for existing_offer in existing_offers['events']:
        offer_start = coverage_hours[0].isoformat()
        offer_end = coverage_hours[1].isoformat()
        if existing_offer['who'] == member_name and existing_offer['start_dt'] == offer_start and existing_offer['end_dt'] == offer_end:
            return True
    return False

def find_coverage(required_event, existing_offers, regulars):
    """
    For the given required_event, find all of the "regulars" that should be scheduled to cover it
    Note: If the regular is already scheduled to cover the required_event, it will be skipped
    """
    covers_events = []
    required_start_date = dateutil.parser.isoparse(required_event['start_dt'])
    required_end_date = dateutil.parser.isoparse(required_event['end_dt'])

    for regular in regulars:
        offer_day_of_week = int(regular['day_of_week'])
        if offer_day_of_week == required_start_date.weekday() or offer_day_of_week == required_end_date.weekday():
            coverage_hours = get_coverage_span(required_start_date, required_end_date,  offer_day_of_week, regular['start_time'], regular['end_time'])
            if coverage_hours and not is_duplicate_offer(regular['member'], coverage_hours, existing_offers):
                covers_events.append(create_cover_event(regular['member'], coverage_hours[0], coverage_hours[1], regular['coverage_level']))
    return covers_events

def read_regulars():
    regulars = []
    with open("./shifts/regulars.csv", 'r') as file:
        csv_file = csv.DictReader(file)
        for row in csv_file:
            if is_coverage_level(row['coverage_level']) == False:
                print('Invalid Coverage Level in Regulars: {}'.format(row['coverage_level']))
            else:
                regulars.append(row)
    return regulars

def get_offers(regulars, month, year):
    period = get_period(month, year)
    required_coverage = teamup_utils.get_events(period[0], period[1], run_config.teamup_config.all_calendar_key_ro, run_config.teamup_config.coverage_required_calendar, run_config.teamup_config.teamup_api_key)
    existing_offers = teamup_utils.get_raw_events(period[0], period[1], run_config.teamup_config.all_calendar_key_ro, run_config.teamup_config.coverage_offered_calendar, run_config.teamup_config.teamup_api_key)

    coverage_events = []
    for required_event in required_coverage['events']:
        covers = find_coverage(required_event, existing_offers, regulars)
        if len(covers) > 0:
            coverage_events.extend(covers)

    return coverage_events

def auto_populate_coverage(month, year, is_preview=False):
    offer_events = get_offers(read_regulars(), month, year)

    if is_preview:
        print('Will create: {} events'.format(len(offer_events)))
        for offer_event in offer_events:
            print('{} Start: {} End: {} Who: {} ({})'.format(days_of_week[dateutil.parser.isoparse(offer_event['start_dt']).weekday()], offer_event['start_dt'], offer_event['end_dt'], offer_event['who'], offer_event['custom']['coverage_level']))
    else:
        for cover in offer_events:
            create_event(cover, {'events':[]})

def parse_skips(skips):
    if skips == None or len(skips.strip()) == 0:
        return []
    else:
        return [int(skip) for skip in skips.split('|')]


def auto_populate_shifts(month, year, source_file):
    required_events = []
    with open(source_file, 'r') as file:
        csv_file = csv.DictReader(file)
        for row in csv_file:            
            if 'day_of_week' in row and len(row['day_of_week']) > 0:
                # if '[' in row['day_of_week']: 
                weekdays = find_all_the_weekdays(month, year, row['day_of_week'], parse_skips(row['skip_days']))
                for weekday in weekdays:
                    date_span = date_utils.span_for_date(weekday, row['start_time'], row['end_time'])
                    required_events.append({'start_date':date_span[0], 'end_date': date_span[1], 'title': row['title']})
            elif 'absolute_date' in row and len(row['absolute_date']) > 0:
                date_span = date_utils.span_for_date(dateutil.parser.isoparse(row['absolute_date']), row['start_time'], row['end_time'])
                required_events.append({'start_date':date_span[0], 'end_date': date_span[1], 'title': row['title']})
            else:
                print('Invalid row: {}'.format(row))

    print('Will create: {} events'.format(len(required_events)))
    for required_event in required_events:
        print('Event: {}: \t{} - {} {}'.format(days_of_week[required_event['start_date'].weekday()], required_event['start_date'].isoformat(), required_event['end_date'].isoformat(), required_event['title']))


def find_all_the_weekdays(month, year, day_of_week, exclude_dates=[]):
    """
    For the given month and year, find all of the days of the given day_of_week
    day_of_week Monday = 0, Sunday = 6
    """
    print('Find all weekdays for {} {} day of week: {} excluding: {}'.format(month, year, day_of_week, exclude_dates))
    days_in_month = []
    for day in range(1, calendar.monthrange(year, month)[1] + 1):
        if len(exclude_dates) == 0 or day not in exclude_dates:
            date = dateutil.parser.isoparse('{}-{:02d}-{:02d}'.format(year, month, day))
            if date.weekday() == int(day_of_week):
                days_in_month.append(date)
    return days_in_month


def get_command_arguments():
    global run_config

    # Instantiate the parser
    parser = argparse.ArgumentParser(description='Optional app description')        

    # Required positional argument
    parser.add_argument('--trigger_file', type=str, required=True, help='trigger filename.  Default: ./triggers/squadsentry_trigger.json', default='./triggers/squadsentry_trigger.json')
    parser.add_argument('--calendar_key', choices=['coverage_required', 'coverage_offered'])

    # Operations
    parser.add_argument('--get_event_ids', action='store_true')
    parser.add_argument('--delete_all', action='store_true', help='Delete all events in the calendar')
    parser.add_argument('--spreadsheet', action='store_true', help='Process the events spreadsheet from Collaborative')
    parser.add_argument('--default_coverage', action='store_true', help='Default coverages using the regulars.csv')
    parser.add_argument('--auto_populate_shifts', action='store_true', help='Auto populate required shifts using repeating or single days')
    parser.add_argument('--sync_test_events', action='store_true', help='Sync test events')

    # Optional arguments
    parser.add_argument('--start_date')
    parser.add_argument('--end_date')
    parser.add_argument('--year', help='Year to process', type=int)
    parser.add_argument('--month', help='Month to process', type=int)
    parser.add_argument('--source_file' , help='The name of the file to read from')
    parser.add_argument('--required_events_file', help='The name of the file to read from')
    parser.add_argument('--offered_events_file', help='The name of the file to read from')
    parser.add_argument('--preview', action='store_true', help='Preview the events to be created')


    # Parse the arguments
    args = parser.parse_args()

    # Validate that what was passed in is valid
    if args.get_event_ids:
        if args.start_date is None or args.end_date is None:
            print('Must specify start and end dates when getting event ids')
            sys.exit(1)
        if args.calendar_key is None:
            print('Must specify calendar key when getting event ids')
            sys.exit(1)

    if args.delete_all:
        if args.source_file is None:
            print('Must specify source file containing event_ids')
            sys.exit(1)
    
    if args.spreadsheet:
        if args.source_file is None or args.year is None or args.month is None:
            print('Must specify source_file, year and month when processing spreadsheet')
            sys.exit(1)

    if args.default_coverage:
        if args.year is None or args.month is None:
            print('Must specify year and month when processing default coverage')
            sys.exit(1)

    if args.sync_test_events:
        if args.required_events_file is None or args.offered_events_file is None:
            print('Must specify required_events_file and offered_events_file when syncing test events')
            sys.exit(1)

    if args.auto_populate_shifts:
        if args.year is None or args.month is None or args.source_file is None:
            print('Must specify year and month and source file when auto populating shifts')
            sys.exit(1)

    run_config = read_configuration(read_trigger(args.trigger_file))


    print('===============================================')
    print('Running with the following configuration for agency: {}'.format(run_config.agency))
    if args.sync_test_events:
        print('Syncing test events')
    elif args.get_event_ids:
        print('Getting event ids from calendar: {}'.format(args.calendar_key))
        print('From start date: {} to end date: {}'.format(args.start_date, args.end_date))
    elif args.delete_all:
        print('Will delete all ids in the file: {}'.format(args.source_file))
    else:
        print('Will read the file: {}'.format(args.source_file))
        print('And create events in: {}'.format(args.calendar_key))
        if args.spreadsheet:
            print('From a spreadsheet')
    print('===============================================')    

    if args.preview:
        print('** Previewing events **')
    else:
        if input("are you sure? (y/n) ") != "y":
            exit()

    return args 


# python create_events.py --trigger_file './triggers/squadsentry_trigger.json'
# python create_events.py --trigger_file './triggers/squadsentry_trigger.json' --sync_test_events --required_events_file './testing/test_cases/coverage_required_cases.csv' --offered_events_file './testing/test_cases/coverage_offered_cases.csv'
if __name__ == '__main__':

    args = get_command_arguments()
    if args.sync_test_events:
        create_test_cases(args.required_events_file, args.offered_events_file)
    elif args.get_event_ids:
        query_save_events(args.calendar_key, args.start_date, args.end_date)
    elif args.delete_all:
        delete_all_events(args.source_file)
    elif args.spreadsheet:
        process_spreadsheet_v2(args.source_file, args.calendar_key, args.month, args.year)
    elif args.default_coverage:
        auto_populate_coverage(args.month, args.year, args.preview)
    elif args.auto_populate_shifts:
        auto_populate_shifts(args.month, args.year, args.source_file)
    else:
        num_events = add_events(args.source_file, translate_calendar_key(args.calendar_key))
        print('Created {} events.  Saved event_ids in a file'.format(num_events))
