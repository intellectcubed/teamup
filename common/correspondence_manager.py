import datetime
from nis import cat
from common.date_utils import get_current_day_key
import boto3
from boto3.dynamodb.conditions import Key
import json


class CorrespondenceManager:

    control_table_name = 'schedule_notifications'

    def __init__(self, dynamodb):
        self.schedule_notification_table = dynamodb.Table(self.control_table_name)

    def save_notification_sent(self, agency, category, summary, context_date_str, email_list, override_send_date=None):
        """
        Note: This is a bit of a hack.  
            - For error_notifications, we are using the context_date_str to store the date sent.
            - For shift_notifications, we are using the context_date_str to store the shift start.
        """
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        date_sent = get_current_day_key() if override_send_date is None else override_send_date
        key_date = context_date_str if category == 'shift_notification' else date_sent


        notification_key = self.make_notification_key(agency, category, key_date)
        # print('Date for key: {} date for sent_date: {} KEY: {}'.format(key_date, date_sent, notification_key))
        item = {'agency_category_start': notification_key, 
            'date_sent': date_sent, 'timestamp': timestamp, 'recipients': email_list}
        if summary is not None: 
            item['summary'] = json.dumps(summary)
        self.schedule_notification_table.put_item(Item=item)
        return notification_key, date_sent

    def was_notification_sent(self, agency, category, summary, shift_start, email_list):
        """
        Determine if a notification was sent for this shift.
        Error html will have shift_start empty and the current day should be used to see if one was sent for today.

        For shifts, a notification will be sent for every day if the recepient list changed.  
        For errors, a notification will be sent once per day (to Martinsvillers).

        Note: coverage = the below structure (always None for category = error_notifications)

        [
            {
                "start_dt": "2022020506",
                "end_dt": "2022020512",
                "who": "Alice Hadley <span class=\"duty_role\">(CC)</span>, Doris Zampella <span class=\"duty_role\">(Driver)</span>, Tianna Spitz <span class=\"duty_role\">(EMT < 18)</span>"
            },
            {
                "start_dt": "2022020512",
                "end_dt": "2022020518",
                "who": "David Vinarov <span class=\"duty_role\">(CC)</span>, Ethan Yoo <span class=\"duty_role\">(EMT > 18)</span>"
            }
        ]

        """
        # For notification key, use the shift_start if it is a shift notification, otherwise use the current day
        notification_key = self.make_notification_key(agency, category, shift_start)
        if category == 'error_notification':
            notification_key = self.make_notification_key(agency, category, get_current_day_key())

        retval = self.schedule_notification_table.query(KeyConditionExpression=Key('agency_category_start').eq(notification_key))
        # print(json.dumps(retval))
        if 'Items' not in retval:
            return False

        notifications = retval.get('Items')
        if len(notifications) == 0:
            return False

        if category == 'shift_notification':
            # sort the items and get latest one
            latest_notification = sorted(notifications, key=lambda x: x['timestamp'])[-1]

            latest_notification['recipients'].sort()
            email_list.sort()

            # print('Checking last_notification.recipients: {} against email list: {} Result: {}'.format(latest_notification['recipients'], email_list, (latest_notification['recipients'] == email_list)))
            if latest_notification['recipients'] == email_list:
                if self.compare_summaries(latest_notification['summary'], summary):
                    return True
        else: 
            # For errors, only send once per day, but each day after that, send again.
            # for notification in notifications:
            #     date_sent = datetime.datetime.strptime(notification['date_sent'], '%Y-%m-%d')
            #     if date_sent.date() == datetime.datetime.now().date():
            #         return True
            if len(notifications) > 0:  
                return True
        
        return False

    def compare_summaries(self, summary1, summary2):
        if type(summary1 ) == str:
            summary1 = json.loads(summary1)
        if type(summary2) == str:
            summary2 = json.loads(summary2)

        summary1 = json.dumps(summary1, sort_keys=True)
        summary2 = json.dumps(summary2, sort_keys=True)
        return summary1 == summary2

    def make_notification_key(self, agency, category, date_in_key):
        return '{}_{}_{}'.format(agency, category, date_in_key)



