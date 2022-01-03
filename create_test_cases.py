import requests
import json
import csv

api_key = '63a9180007a78ac4ea5738101159eb2ec8819f616ae91ed1d9e377dfd9300855'

url = 'https://api.teamup.com'
collaborative_calendar_key = 'ksfpzqh66j83hdoo85'
power_sub_calendar = 10364744
shift_sub_calendar = 10364691
tango_sub_calendar = 10364692

coverage_calendar_key = 'kstgggzjrpasj6eyiq'
coverage_required_calendar = 10358690
coverage_offered_calendar = 10363404
tango_required_calendar = 10358691
tango_offered_calendar = 10363770


def create_event(event):
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'Teamup-Token': api_key}

    ret = requests.post('/'.join([url, coverage_calendar_key, 'events']), data=json.dumps(event), headers=headers)
    if ret.status_code != 200:
        print('Error: {}'.format(ret.text))
        return
    else:
        print('Created event: {}'.format(ret.text))

def create_coverage_required(filename):
    with open(filename, 'r') as f:
        rdr = csv.reader(f)
        # This skips the header
        next(rdr)
        for row in rdr:
            print(row)

            event = {
                'subcalendar_id': coverage_required_calendar,
                'start_dt': row[0],
                'end_dt': row[1],
                'title': row[2]
            }
            create_event(event)

def create_test_cases(filename):
    with open(filename, 'r') as f:
        rdr = csv.reader(f)
        # This skips the header
        next(rdr)
        for row in rdr:
            print(row)

            event = {
                'subcalendar_id': coverage_offered_calendar,
                'start_dt': row[0],
                'end_dt': row[1],
                'who': row[2],
                'title': row[4],
                'custom': {
                    'coverage_level': row[3]
                }
            }
            create_event(event)


def get_events(start_dt, end_dt):
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'Teamup-Token': api_key}
    ret = requests.get('/'.join([url, coverage_calendar_key, 'events']) + '?startDate={}&endDate={}'.format(start_dt, end_dt), headers=headers)
    return json.loads(ret.text)

def delete_event(event_id):
    # print('Deleting event: ' + str(event_id))
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'Teamup-Token': api_key}
    ret = requests.delete('/'.join([url, coverage_calendar_key, 'events', str(event_id)]), headers=headers)
    print('deleted event: ' + str(event_id))

def delete_all(start_dt, end_dt):
    events = get_events(start_dt, end_dt)
    for event in events['events']:
        delete_event(event['id'])

if __name__ == '__main__':
    delete_all('2021-12-01', '2021-12-31')
    create_coverage_required('./test_cases/coverage_required_cases.csv')
    create_test_cases('./test_cases/coverage_offered_cases.csv')
