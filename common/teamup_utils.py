import requests
import json

url = 'https://api.teamup.com'


def create_event(event, calendar_key, api_key):
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'Teamup-Token': api_key}

    ret = requests.post('/'.join([url, calendar_key, 'events']), data=json.dumps(event), headers=headers)
    if ret.status_code != 200 and ret.status_code != 201:
        print('Code: {} Error: {}'.format(ret.status_code, ret.text))
        return
    else:
        return json.loads(ret.text)


def get_events(start_dt, end_dt, calendar_key, api_key):
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'Teamup-Token': api_key}
    ret = requests.get('/'.join([url, calendar_key, 'events']) + '?startDate={}&endDate={}'.format(start_dt, end_dt), headers=headers)
    # print(ret.text)
    return json.loads(ret.text)

def delete_event(event_id, calendar_key, api_key):
    # print('Deleting event: ' + str(event_id))
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'Teamup-Token': api_key}
    ret = requests.delete('/'.join([url, calendar_key, 'events', str(event_id)]), headers=headers)
    if ret.status_code != 200 and ret.status_code != 201:
        print('Code: {} Error: {}'.format(ret.status_code, ret.text))
    else:
        print('deleted event: ' + str(event_id))

def delete_all_events(events, calendar_key, api_key):
    for event in events['events']:
        delete_event(event['id'], calendar_key, api_key)

