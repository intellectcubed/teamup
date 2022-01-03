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

import requests
import json
import csv

api_key = '63a9180007a78ac4ea5738101159eb2ec8819f616ae91ed1d9e377dfd9300855'

url = 'https://api.teamup.com'
collaborative_calendar_key = 'ksfpzqh66j83hdoo85'
power_sub_calendar = 10364744
shift_sub_calendar = 10364691
tango_sub_calendar = 10364692

def add_events(source_file):
    with open(source_file, 'r') as f:
        rdr = csv.reader(f)
        # This skips the header
        next(rdr)
        for row in rdr:
            print(row)

            event = {
                'subcalendar_id': int(row[0]),
                'start_dt': row[1],
                'end_dt': row[2],
                'title': row[4],
                'custom': {
                    'squad2': row[3]
                }
            }
            create_event(event)

def create_event(event):
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'Teamup-Token': api_key}

    ret = requests.post('/'.join([url, collaborative_calendar_key, 'events']), data=json.dumps(event), headers=headers)
    print('created event')

def get_events(start_dt, end_dt):
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'Teamup-Token': api_key}
    ret = requests.get('/'.join([url, collaborative_calendar_key, 'events']) + '?startDate={}&endDate={}'.format(start_dt, end_dt), headers=headers)
    return json.loads(ret.text)
    print(ret.text)


def get_event1():
    return     {
      'subcalendar_id': shift_sub_calendar,
      'subcalendar_ids': [
        shift_sub_calendar
      ],
      'all_day': False,
      'notes': '<p>Covering 35 / 42 / 54</p>',
      'readonly': False,
      'start_dt': '2021-12-31T18:00:00-05:00',
      'end_dt': '2022-01-01T01:00:00-05:00',
      'squad2': 'bradley_gardens_39_',
      'custom': {
        'squad': 'bradley_gardens_39_'
      }
    }

def delete_event(event_id):
    # print('Deleting event: ' + str(event_id))
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'Teamup-Token': api_key}
    ret = requests.delete('/'.join([url, collaborative_calendar_key, 'events', str(event_id)]), headers=headers)
    print('deleted event: ' + str(event_id))

def delete_all_events(events):
    for event in events['events']:
        delete_event(event['id'])


if __name__ == '__main__':
    # add_events('/Users/gnowakow/Documents/tango.csv')
    add_events('/Users/gnowakow/Documents/collab_jan.csv')
    # delete_all_events(get_events('2022-01-01', '2022-02-01'))