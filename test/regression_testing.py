"""
Regression test suite.

If regression tests are run and they fail because the old snapshot does not match the new snapshot,
it may be due to the fact that the test cases have changed, or might be because of a bug in the code.

If the cases do not match, you can use http://www.jsondiff.com/ to compare the results to the snapshot.  If you agree with the 
changes in the snapshot, you can delete the __snapshot__ folder and run again. -- This will save the snapshot for the next run.

TODO: 
    - Add code that removes dates and event_ids from the snapshot, that is not what should be compared between old vs new.
    - Change the check_coverage method to also return logs of which emails were sent.  Save this in another JSON file that should also
      be compared to the snapshot.
    - Write a shell script that will run the regression tests before uploading to AWS.  If regression fails, do not upload!
"""

import json
import check_coverage as CheckCoverage
import glob
import os


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
    latest_run = '{}/testing/__latest__'.format(current_dir)

    if os.path.isdir(latest_run):
        files = glob.glob('{}/*'.format(latest_run))
        for f in files:
            os.remove(f)        
    else:
        os.makedirs(latest_run)

    save_snapshot(shifts, '{}/shifts.json'.format(latest_run))
    save_snapshot(errors, '{}/errors.json'.format(latest_run))

    if os.path.isdir(snap_folder) == False:
        os.makedirs(snap_folder)
        save_snapshot(errors, '{}/errors.json'.format(snap_folder))
        save_snapshot(shifts, '{}/shifts.json'.format(snap_folder))
        print('Test results saved -- not validated')
        return True
    else:
        passed = True
        if load_snapshot_compare(shifts, '{}shifts.json'.format(snap_folder)) == False:
            print('** Shifts did not match snapshot **')
            passed = False
        if load_snapshot_compare(errors, '{}errors.json'.format(snap_folder)) == False:
            print('** Shifts did not match snapshot **')
            passed = False

        if passed == True:
            print('PASS - shifts snapshot matches')

        return passed


def run_check_events(start_date, end_date):  
    with open('./triggers/squadsentry_trigger.json') as f:
        event = json.load(f)

    if validate_results(*CheckCoverage.regression(event, start_date, end_date)) == False:
        print('Test cases failed!!!.  If you validate that test results are correct, delete the __snapshot__ folder and run again.')
        print('You may use: http://www.jsondiff.com/ to compare the results to the snapshot')
        return


# python -m test.regression_testing
if __name__ == '__main__':
    run_check_events('2021-12-01', '2021-12-31')
