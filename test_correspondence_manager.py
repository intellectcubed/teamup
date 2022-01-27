import sys
import datetime
import common.date_utils as date_utils
import time
import boto3
from common.correspondence_manager import CorrespondenceManager

"""
Tests function that sends email in check_coverage.py
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


skip_setup = False

keys_created = []
def setup_scenarios():
    if skip_setup:
        return 

    # For scenario_2
    create_sent(agency, category_shift, shift_date_1_str, recepients1, '2020-01-01')
    create_sent(agency, category_shift, shift_date_1_str, recepients2, '2020-01-02')
    create_sent(agency, category_shift, shift_date_1_str, recepients3, '2020-01-03')
    
    time.sleep(5)


def create_sent(agency, category, date_str, recipients, override_date_sent=None):
    key = correspondence_manager.make_notification_key(agency, category, date_str)
    key, date_saved = correspondence_manager.save_notification_sent(agency, category, date_str, recipients, override_send_date=override_date_sent)
    keys_created.append((key, date_saved))


def clean_up_scenarios():
    if skip_setup:
        return 
    for key, date_saved in keys_created:
        delete_notification_sent(key, date_saved)

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

    was_sent = correspondence_manager.was_notification_sent(agency, category_shift, shift_date_0_str, recepients)
    assert was_sent == False

    was_sent = correspondence_manager.was_notification_sent(agency, category_error, shift_date_0_str, recepients)
    assert was_sent == False

    print('Scenario 1 Pass')

def scenario_2():
    """
    Record exists, should not send email (both categories)
    """
    # sys.argv = ["prog", "--headless", '--send_email']
    # args = correspondence_manager.get_command_arguments()

    assert correspondence_manager.was_notification_sent(agency, category_shift, shift_date_1_str, recepients) == False
    assert correspondence_manager.was_notification_sent(agency, category_error, shift_date_1_str, recepients) == False

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
    assert correspondence_manager.was_notification_sent(agency, category_shift, shift_date_1_str, recepients1) == False

    # recepients same as second record (ok to send)
    assert correspondence_manager.was_notification_sent(agency, category_shift, shift_date_1_str, recepients2) == False

    # recepients same as third record (not to send)
    assert correspondence_manager.was_notification_sent(agency, category_shift, shift_date_1_str, recepients3) == True

    print('Scenario 3 Pass')

def scenario_3_2():
    """
    Same day, same recipient list, different shift start (for example 6am and 6pm on same day)
    Should send email in all cases
    """
    shift_date_morning_str = datetime.datetime.strftime(date_utils.key_to_date('2022010200') , date_utils.HOUR_KEY_FMT)


    # recepients same as third record (not to send)
    assert correspondence_manager.was_notification_sent(agency, category_shift, shift_date_1_str, recepients3) == True

    # same recipients, same date, but different shift start (ok to send)
    assert correspondence_manager.was_notification_sent(agency, category_shift, shift_date_morning_str, recepients2) == False

    print('Scenario 3_2 Pass')
    

def scenario_4():
    """
    For error notifications, should allow emails to be sent every day (but only once per day)
    """

    # sys.argv = ["prog", '--headless', '--send_email']
    # correspondence_manager.get_command_arguments()

    assert correspondence_manager.was_notification_sent(agency, category_shift, shift_date_1_str, recepients) == True

def scenario_5():
    """
    - save (shift) notification record
    - check if should send mail?  - assert False
    - Change recepients
    - check if should send mail?  - assert True
    """
    # sys.argv = ["prog", "--headless", '--send_email']
    # args = correspondence_manager.get_command_arguments()

    assert correspondence_manager.was_notification_sent(agency, category_shift, shift_date_1_str, recepients) == True

    new_recepients = ['amy_webb@hoo.com']
    assert correspondence_manager.was_notification_sent(agency, category_shift, shift_date_1_str, new_recepients) == False


if __name__ == '__main__':
# >>> import test_check_send_email
# >>> test_check_send_email.setup_scenarios()


    # setup_scenarios()
    scenario_1()
    scenario_2()
    scenario_3()
    scenario_3_2()
    # scenario_4()
    # scenario_5()
    # clean_up_scenarios()

