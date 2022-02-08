import sys
import datetime
import common.date_utils as date_utils
import time
import boto3
from common.correspondence_manager import CorrespondenceManager

"""
Tests function that sends email in check_coverage.py

## To run: From root of project (TeamUp):
python -m test.test_correspondence_manager
"""

agency = 'test_agency'
category_shift = 'shift_notification'
category_error = 'error_notification'
recepients = ['george@yahoo.com', 'neal@yahoo.com', 'lou@gmail.com']
recepients1 = ['thelma@yahoo.com', 'louise@yahoo.com']
recepients2 = ['birds@hmail', 'turtles@tmail.com']
recepients3 = ['c3po@gmail.com']


dynamodb = boto3.resource('dynamodb')

correspondence_manager = CorrespondenceManager(dynamodb)

member_table = dynamodb.Table('squad_members')
schedule_notification_table = dynamodb.Table('schedule_notifications')

shift_date_1_str = datetime.datetime.strftime(date_utils.key_to_date('2022010218') , date_utils.HOUR_KEY_FMT)
shift_date_2_str = datetime.datetime.strftime(date_utils.key_to_date('2022010318') , date_utils.HOUR_KEY_FMT)

summary1 = {"Ryan Ross": 6, "Jim Ross": 6, "Vishnu Chennapragada": 6, "Doris Zampella": 12, "George Nowakowski": 6, "Ian Smoke": 6}
summary2 = {"George Nowakowski": 12, "Sydroy Morgan": 12}

recip_summary = {'george': 8, 'neal': 8, 'lou': 12}
recip1_summary = {'Thelma': 4, 'louise': 6}
recip2_summary = {'birds': 4, 'turtles': 6}
recip3_summary = {'c3po': 4}

keys_created = []
def setup_scenarios():
    if skip_setup:
        return 

    # For scenario_2
    create_sent(agency, category_shift, recip1_summary, shift_date_1_str, recepients1, '2020-01-01')
    create_sent(agency, category_shift, recip2_summary, shift_date_1_str, recepients2, '2020-01-02')
    create_sent(agency, category_shift, recip3_summary, shift_date_1_str, recepients3, '2020-01-03')
    
    create_sent(agency, category_error, recip3_summary, shift_date_1_str, recepients3, '2020-01-03') # For shift 1, error notification sent on 2020-01-03
    create_sent(agency, category_error, recip3_summary, shift_date_2_str, recepients3, '2020-01-04') # For shift2, error notification sent today



    # Eventual consistency is a bitch!
    time.sleep(5)
    print('Scenarios setup')


def create_sent(agency, category, summary, date_str, recipients, override_date_sent=None):
    key, date_saved = correspondence_manager.save_notification_sent(agency, category, summary, date_str, recipients, override_send_date=override_date_sent)
    keys_created.append((key, date_saved))


def clean_up_scenarios():
    if skip_setup:
        return 
    for key, date_saved in keys_created:
        delete_notification_sent(key, date_saved)

    print('Scenarios cleaned up')

def delete_notification_sent(key, date_saved):
    schedule_notification_table.delete_item(Key={'agency_category_start': key, 'date_sent': date_saved})
    print('deleted')

def scenario_1():
    """
    NO notification record exists, should send email
    Test both types of notifications
    """
    # sys.argv = ["prog", '--headless', '--send_email']
    # correspondence_manager.get_command_arguments()

    shift_date_0_str = datetime.datetime.strftime(date_utils.key_to_date('2022010100') , date_utils.HOUR_KEY_FMT)
    assert correspondence_manager.was_notification_sent(agency, category_error, recip_summary, shift_date_0_str, list(recip_summary.keys())) == False, 'No error notification sent for shift_date_0_str, recepients'

    print('Scenario 1 Pass')

def scenario_2():
    """
    Record exists, should not send email (both categories)
    """
    # sys.argv = ["prog", "--headless", '--send_email']
    # args = correspondence_manager.get_command_arguments()

    assert correspondence_manager.was_notification_sent(agency, category_shift, recip_summary, shift_date_1_str, list(recip_summary.keys())) == False, 'shift for date1, recipients should already exist, do not send'
    assert correspondence_manager.was_notification_sent(agency, category_error, recip_summary, shift_date_1_str, list(recip_summary.keys())) == False, 'error for date1, recipients should already exist, do not send'

    print('Scenario 2 Pass')

def scenario_3():
    """
    - Three records exist for the same shift (three different days)
    - The latest record (when sorted by date_sent) uses the recipients3 list, therefore, it should not allow to send mail
    - If you use other recipients, it should allow to send mail
    """
    # sys.argv = ["prog", '--headless', '--send_email']
    # correspondence_manager.get_command_arguments()

    # recepients same as first record (ok to send)
    assert correspondence_manager.was_notification_sent(agency, category_shift, recip1_summary, shift_date_1_str, recepients1) == False

    # recepients same as second record (ok to send)
    assert correspondence_manager.was_notification_sent(agency, category_shift, recip2_summary, shift_date_1_str, recepients2) == False

    # recepients same as third record (not to send)
    assert correspondence_manager.was_notification_sent(agency, category_shift, recip3_summary, shift_date_1_str, recepients3) == True

    print('Scenario 3 Pass')

def scenario_3_2():
    """
    Same day, same recipient list, different shift start (for example 6am and 6pm on same day)
    Should send email in all cases
    """
    shift_date_morning_str = datetime.datetime.strftime(date_utils.key_to_date('2022010200') , date_utils.HOUR_KEY_FMT)


    # recepients same as third record (not to send)
    assert correspondence_manager.was_notification_sent(agency, category_shift, recip3_summary, shift_date_1_str, recepients3) == True

    # same recipients, same date, but different shift start (ok to send)
    assert correspondence_manager.was_notification_sent(agency, category_shift, recip2_summary, shift_date_morning_str, recepients2) == False

    print('Scenario 3_2 Pass')
    

def scenario_4():
    """
    For error notifications, should allow emails to be sent every day (but only once per day)
    """

    # sys.argv = ["prog", '--headless', '--send_email']
    # correspondence_manager.get_command_arguments()

    assert correspondence_manager.was_notification_sent(agency, category_error, recip_summary, shift_date_1_str, recepients) == False, 'errors should be sent once per day'
    assert correspondence_manager.was_notification_sent(agency, category_error, recip_summary, shift_date_2_str, recepients) == False, 'errors should be sent once per day'

    print('Scenario 4 Pass')

def scenario_5():
    """
    - save (shift) notification record
    - check if should send mail?  - assert False
    - Change recepients
    - check if should send mail?  - assert True
    """
    # sys.argv = ["prog", "--headless", '--send_email']
    # args = correspondence_manager.get_command_arguments()

    assert correspondence_manager.was_notification_sent(agency, category_shift, recip3_summary, shift_date_1_str, recepients3) == True

    new_recepients = recepients3[:]
    new_recepients.append('amy_webb@hoo.com')
    assert correspondence_manager.was_notification_sent(agency, category_shift, new_recepients, shift_date_1_str, recepients) == False

    print('Scenario 5 Pass')

def scenario_6():
    """
    Required Shifts: 
    1/7/22 :1800 - 0600
    1/8/22 :0600 - 1200

    Coverage: 
    George 1/7/22 :1800 - 1200

    > test: should send 1/7? - assert True
    > test: should send 1/8? - assert True

    Change Coverage: 
    George 1/7/22 :1800 - 1000
    Evan   1/8/22 :1000 - 1200

    > test: should send 1/7? - assert False
    > test: should send 1/8? - assert True

    """

    shift_date_7_str  = datetime.datetime.strftime(date_utils.key_to_date('2022010718') , date_utils.HOUR_KEY_FMT)
    shift_date_8_str  = datetime.datetime.strftime(date_utils.key_to_date('2022010806') , date_utils.HOUR_KEY_FMT)


    shift_7_crew = {'george': 12, 'lou': 6, 'sam': 6}
    shift_8_crew = {'george': 12, 'lou': 12, 'evan': 12}

    shift_7_recipients = list(shift_7_crew.keys())
    shift_8_recipients = list(shift_8_crew.keys())


    create_sent(agency, category_shift, shift_7_crew, shift_date_7_str, shift_7_recipients, '2020-01-06') 
    create_sent(agency, category_shift, shift_8_crew, shift_date_8_str, shift_8_recipients, '2020-01-06') 

    assert correspondence_manager.was_notification_sent(agency, category_shift, shift_7_crew, shift_date_7_str, shift_7_recipients) == True
    assert correspondence_manager.was_notification_sent(agency, category_shift, shift_8_crew, shift_date_8_str, shift_8_recipients) == True

    # TODO: Change shift hours
    mod_shift_7_crew = shift_7_crew.copy()
    mod_shift_7_crew['lou'] = 8
    mod_shift_7_crew['sam'] = 6

    assert correspondence_manager.was_notification_sent(agency, category_shift, mod_shift_7_crew, shift_date_7_str, shift_7_recipients) == False
    assert correspondence_manager.was_notification_sent(agency, category_shift, shift_8_crew, shift_date_8_str, shift_8_recipients) == True

    print('Scenario 6 Pass')


# =============================================================================
# Skip setup is an optimization.  If you set it to True, it will rely on the 
# events being in the db already.  False = create and drop each time the test is run
skip_setup = False
# =============================================================================




if __name__ == '__main__':
# >>> import test_check_send_email
# >>> test_check_send_email.setup_scenarios()

    # setup_scenarios()
    try:

        # print('{}'.format(correspondence_manager.was_notification_sent(agency, category_shift, shift_date_1_str, recepients1)))
        setup_scenarios()

        scenario_1()
        scenario_2()
        scenario_3()
        scenario_3_2()
        scenario_4()
        scenario_5()
        scenario_6()
    finally:
        clean_up_scenarios()

