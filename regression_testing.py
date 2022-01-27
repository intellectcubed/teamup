import json
import csv
from check_coverage import check_events, report_shifts
import common.teamup_utils as teamup_utils

import os

url = 'https://api.teamup.com'
api_key = os.environ['TEAMUP_API_KEY']

target_calendar_key = os.environ['COLLABORATIVE_CALENDAR_ADMIN_KEY']
coverage_required_calendar = os.environ['COVERAGE_REQUIRED_CALENDAR']
coverage_offered_calendar = os.environ['COVERAGE_OFFERED_CALENDAR']

agency = 'test_agency'

def create_test_cases(filename, subcalendar_id):
    events = []
    with open(filename, 'r') as f:
        rdr = csv.reader(f)
        # This skips the header
        next(rdr)
        for row in rdr:
            event = create_event(row, subcalendar_id)
            events.append(teamup_utils.create_event(event, target_calendar_key, api_key))

    return events


def create_event(row, subcalendar_id):

    if subcalendar_id == coverage_offered_calendar:
        return {
            'subcalendar_id': subcalendar_id,
            'start_dt': row[0],
            'end_dt': row[1],
            'who': row[2],
            'title': row[4],
            'custom': {
                'coverage_level': row[3]
            }
        }
    elif subcalendar_id == coverage_required_calendar:
        return {
            'subcalendar_id': coverage_required_calendar,
            'start_dt': row[0],
            'end_dt': row[1],
            'title': row[2]
        }

def save_snapshot(to_save, target_file_path):
    with open(target_file_path, 'w') as f:
        json.dump(to_save, f)


def load_snapshot_compare(to_compare, target_file_path):
    with open(target_file_path, 'r') as f:
        snapshot = json.load(f)

    if 'timestamp' in to_compare:
        to_compare.pop('timestamp')

    if 'timestamp' in snapshot:
        snapshot.pop('timestamp')

    return json.dumps(to_compare, sort_keys=True) == json.dumps(snapshot, sort_keys=True)


def validate_results(errors, shifts) -> bool:

    current_dir = os.getcwd()

    snap_folder = '{}/testing/__snapshot__/'.format(current_dir)

    if os.path.isdir(snap_folder) == False:
        os.makedirs(snap_folder)
        save_snapshot(errors, '{}errors.json'.format(snap_folder))
        save_snapshot(shifts, '{}shifts.json'.format(snap_folder))
        print('Test results saved -- not validated')
        return True
    else:
        if load_snapshot_compare(errors, '{}errors.json'.format(snap_folder)) == False:
            print('Errors snapshot does not match')
            return False
        else:
            print('PASS - Errors snapshot matches')

        if load_snapshot_compare(shifts, '{}shifts.json'.format(snap_folder)) == False:
            print('shifts snapshot does not match')
            return False
        else:
            print('PASS - shifts snapshot matches')

    return True


def refresh_test_cases(start_date, end_date):
    # TODO: Get the start and end dates from the test case files
    delete_all(start_date, end_date)
    test_ids = create_test_cases('./test_cases/coverage_required_cases.csv', coverage_required_calendar)
    test_ids.extend(create_test_cases('./test_cases/coverage_offered_cases.csv', coverage_offered_calendar));
    print('Test cases created {}'.format(test_ids))


def run_test_suite(start_date, end_date):
    requireds, coverages, errors, warnings = check_events(coverage_required_calendar, coverage_offered_calendar, start_date, end_date)
    shift_map = report_shifts(agency, coverage_required_calendar, coverage_offered_calendar, start_date, end_date, errors)

    if validate_results(errors, shift_map) == False:
        print('Test cases failed!!!.  If you validate that test results are correct, delete the __snapshot__ folder and run again.')
        print('You may use: http://www.jsondiff.com/ to compare the results to the snapshot')
        return

    # teamup_utils.delete_all_events(test_ids, target_calendar_key, api_key)


def delete_all(start_date, end_date):
    events = teamup_utils.get_events(start_date, end_date, target_calendar_key, api_key)
    teamup_utils.delete_all_events(events, target_calendar_key, api_key)
    print('Killed em all!!')


if __name__ == '__main__':
    run_test_suite('2021-12-01', '2021-12-31')


