import datetime
from common.date_utils import get_current_day
import boto3
from boto3.dynamodb.conditions import Key
from common.utils import NotificationCategory
import json


class CorrespondenceManager:

    def __init__(self, dynamodb, control_table_name):
        self.schedule_notification_table = dynamodb.Table(control_table_name)

    def save_notification_sent(self, agency, report_type, category: NotificationCategory, summary, context_date_str, email_list, override_send_date=None):
        """
        Note: This is a bit of a hack.  
            - For error_notifications, we are using the context_date_str to store the date sent.
            - For shift_notifications, we are using the context_date_str to store the shift start.
        """
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        date_sent = get_current_day() if override_send_date is None else override_send_date
        key_date = context_date_str if category == NotificationCategory.SHIFT_NOTIFICATION else date_sent


        notification_key = self.make_notification_key(agency, category.value, report_type, key_date)
        # print('Date for key: {} date for sent_date: {} KEY: {}'.format(key_date, date_sent, notification_key))
        item = {'agency_category_start': notification_key, 
            'date_sent': date_sent, 'timestamp': timestamp, 'recipients': email_list}
        if summary is not None: 
            item['summary'] = json.dumps(summary)
        self.schedule_notification_table.put_item(Item=item)
        return notification_key, date_sent

    def is_items_in_retval(self, retval):
        # If there are no items, then we have not sent a notification for this shift
        if 'Items' not in retval:
            return False

        return len(retval.get('Items')) > 0


    def check_if_sent(self, category: NotificationCategory, notifications, summary, email_list):
        """
        The rule is:
            If category = SHIFT_NOTIFCATION, then send once per day, unless the summary has changed.
            If category = ERROR_NOTIFICATION, then send once per day
        """
        if len(notifications) == 0:
            return False

        if category == NotificationCategory.SHIFT_NOTIFICATION:
            # sort the items and get latest one
            latest_notification = sorted(notifications, key=lambda x: x['timestamp'])[-1]

            latest_notification['recipients'].sort()
            email_list.sort()

            # print('Checking last_notification.recipients: {} against email list: {} Result: {}'.format(latest_notification['recipients'], email_list, (latest_notification['recipients'] == email_list)))
            if latest_notification['recipients'] == email_list:
                if self.compare_summaries(latest_notification['summary'], summary):
                    return True
        else: 
            # Error notifications have date as part of the key, so if a notification exists for today's date, it was sent!
            return True
        
        return False

    def was_notification_sent(self, agency, category: NotificationCategory, report_type, summary, shift_start, email_list):
        """
        Determine if a notification was sent for this shift.

        :param agency: Agency name
        :param category: NotificationCategory (enum value)
        :param report_type: ReportType [duty]
        :param summary: Summary of the report (example: {'Sejal Patel': 3, 'Alice Hadley': 4, 'George Nowakowski': 12, 'Sydroy Morgan': 12})
        :param shift_start: Shift start time (YearMonthDayHour example: '2022050318' )
        :param email_list: List of email addresses
        :return: True if the notification was sent, False otherwise


        Error html will have shift_start empty and the current day should be used to see if one was sent for today.

        For shifts, a notification will be sent for every day if the recepient list changed.  
        For errors, a notification will be sent once per day (to Martinsvillers).
        """

        # For notification key, use the shift_start if it is a shift notification, otherwise use the current day for error notifications
        key_date = shift_start if category == NotificationCategory.SHIFT_NOTIFICATION else get_current_day()
        notification_key = self.make_notification_key(agency, category.value, report_type, key_date)

        retval = self.schedule_notification_table.query(KeyConditionExpression=Key('agency_category_start').eq(notification_key))
        if not self.is_items_in_retval(retval):
            # print('The key was not found: {}'.format(notification_key))
            was_sent = False
        else:
            notifications = retval.get('Items')
            was_sent = self.check_if_sent(category, notifications, summary, email_list)

        # print('Key: {} was sent: {}'.format(notification_key, was_sent))
        return was_sent


    def compare_summaries(self, summary1, summary2):
        if type(summary1 ) == str:
            summary1 = json.loads(summary1)
        if type(summary2) == str:
            summary2 = json.loads(summary2)

        summary1 = json.dumps(summary1, sort_keys=True)
        summary2 = json.dumps(summary2, sort_keys=True)
        return summary1 == summary2

    def make_notification_key(self, agency, category: str, report_type, date_in_key):
        return '{}_{}_{}_{}'.format(agency, category, report_type, date_in_key)



