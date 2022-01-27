import datetime
from common.date_utils import get_current_day_key
import boto3
from boto3.dynamodb.conditions import Key


class CorrespondenceManager:

    control_table_name = 'schedule_notifications'

    def __init__(self, dynamodb):
        self.schedule_notification_table = dynamodb.Table(self.control_table_name)

    def save_notification_sent(self, agency, category, context_date_str, email_list, override_send_date=None):
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if override_send_date is not None:
            date_sent = override_send_date
        else:
            date_sent = get_current_day_key()

        notification_key = self.make_notification_key(agency, category, context_date_str)
        self.schedule_notification_table.put_item(Item={'agency_category_start': notification_key, 
            'date_sent': date_sent, 'timestamp': timestamp, 'recipients': email_list})
        return notification_key, date_sent

    def was_notification_sent(self, agency, category, shift_start, email_list):
        """
        Determine if a notification was sent for this shift.
        Error html will have shift_start empty and the current day should be used to see if one was sent for today.

        For shifts, a notification will be sent for every day if the recepient list changed.  
        For errors, a notification will be sent once per day (to Martinsvillers).

        """
        retval = self.schedule_notification_table.query(KeyConditionExpression=Key('agency_category_start').eq(self.make_notification_key(agency, category, shift_start)))
        if 'Items' not in retval:
            return True

        notifications = retval.get('Items')
        if len(notifications) == 0:
            return False

        if category == 'shift_notification':
            # sort the items and get latest one
            latest_notification = sorted(notifications, key=lambda x: x['timestamp'])[-1]

            latest_notification['recipients'].sort()
            email_list.sort()

            if latest_notification['recipients'] == email_list:
                return True
        else: 
            # For errors, only send once per day
            if len(notifications) > 0:
                return True
        
        return False

    def make_notification_key(self, agency, category, shift_start):
        return '{}_{}_{}'.format(agency, category, shift_start)



