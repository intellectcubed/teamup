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
"""

import csv
import argparse
import os
import common.teamup_utils as teamup_utils
import sys


url = 'https://api.teamup.com'

api_key = os.environ['TEAMUP_API_KEY']
target_calendar_key = os.environ['COLLABORATIVE_CALENDAR_ADMIN_KEY']
coverage_required_calendar = os.environ['COVERAGE_REQUIRED_CALENDAR']
coverage_offered_calendar = os.environ['COVERAGE_OFFERED_CALENDAR']
tango_required_calendar = os.environ['TANGO_REQUIRED_CALENDAR']
tango_offered_calendar = os.environ['TANGO_OFFERED_CALENDAR']

"""
### Example how to invoke (Coverage required): 
python3 create_events.py --calendar coverage_required --source_file /Users/gnowakow/Projects/EMS/TeamUp/shifts/feb_2022_coverage_required.csv

Expected input for coverage_required calendar: [start_dt, end_dt, title]
Example: 2022-02-01T18:00:00-05:00,2022-02-02T06:00:00-05:00,MRS Duty: Covering 34 (Green Knoll) and 35 (Finderne)


### Example how to invoke (Coverage offered):
python3 create_events.py --calendar coverage_offered --source_file /Users/gnowakow/Projects/EMS/TeamUp/shifts/feb_2022_coverage_offered.csv

Expected input for coverage_offered: [start_dt, end_dt, role, who]
Example: 2022-02-14T18:00:00-05:00,2022-02-15T00:00:00-05:00,crew_chief,Jim Ross


### To delete records created: 

python3 create_events.py --calendar coverage_required --source_file /Users/gnowakow/Projects/EMS/TeamUp/shifts/feb_2022_coverage_required_event_ids.csv --delete_all


"""


def add_events(source_file, sub_calendar_key):
    print('Going to create events in calendar: {} Sub calendar: {} using API key: {}'.format(target_calendar_key, sub_calendar_key, api_key))
    num_events = 0
    event_id_file = source_file.replace('.csv', '_event_ids.csv')
    with open(event_id_file, 'w') as events_file:
        with open(source_file, 'r') as f:
            rdr = csv.reader(f)
            for row in rdr:
                event = row_to_event(sub_calendar_key, row)
                print(event)

                new_event = teamup_utils.create_event(event, target_calendar_key, api_key)
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

def translate_calendar_key(calendar_key):
    if calendar_key == 'coverage_required':
        return coverage_required_calendar
    elif calendar_key == 'coverage_offered':
        return coverage_offered_calendar
    elif calendar_key == 'tango_required':
        return tango_required_calendar
    elif calendar_key == 'tango_offered':
        return tango_offered_calendar
    else:
        raise Exception('Invalid calendar key: {}'.format(calendar_key))


def delete_all_events(id_file, sub_calendar_key):
    with open(id_file, 'r') as f:
        for event_id in f:
            print('Deleting event: {}'.format(event_id))
            teamup_utils.delete_event(event_id, sub_calendar_key, api_key)

def get_command_arguments():
    # Instantiate the parser
    parser = argparse.ArgumentParser(description='Optional app description')        

    # Required positional argument

    parser.add_argument('--calendar_key', 
        choices=['coverage_required', 'coverage_offered', 'tango_required', 'tango_offered'])

    parser.add_argument('--source_file' , help='The name of the file to read from')

    parser.add_argument('--delete_all', action='store_true', help='Delete all events in the calendar')

    # Parse the arguments
    args = parser.parse_args()

    print('===============================================')
    print('Will read the file: {}'.format(args.source_file))
    print('And create events in: {}'.format(args.calendar_key))
    print('===============================================')    

    if input("are you sure? (y/n)") != "y":
        exit()

    return args 


if __name__ == '__main__':
    args = get_command_arguments()
    if args.delete_all:
        delete_all_events(args.source_file, translate_calendar_key(args.calendar_key))
    else:
        num_events = add_events(args.source_file, translate_calendar_key(args.calendar_key))
        print('Created {} events.  Saved event_ids in a file'.format(num_events))
        
    # add_events(args.source_file, args.calendar_key)
