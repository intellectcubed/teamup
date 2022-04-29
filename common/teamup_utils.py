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


def get_events(start_dt, end_dt, calendar_key, subcalendar_id, api_key):
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'Teamup-Token': api_key}
    ret = requests.get('/'.join([url, calendar_key, 'events']) + '?startDate={}&endDate={}&subcalendarId[]={}&tz=America/New_York'.format(start_dt, end_dt, subcalendar_id), headers=headers)
    response = json.loads(ret.text)
    if 'error' in response:
        print('Code: {} Error: {}'.format(ret.status_code, ret.text))
        raise Exception('Error getting events')
    round_start_end_dates(response)
    return response

def get_raw_events(start_dt, end_dt, calendar_key, subcalendar_id, api_key):
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain', 'Teamup-Token': api_key}
    ret = requests.get('/'.join([url, calendar_key, 'events']) + '?startDate={}&endDate={}&subcalendarId[]={}&tz=America/New_York'.format(start_dt, end_dt, subcalendar_id), headers=headers)
    response = json.loads(ret.text)
    if 'error' in response:
        print('Code: {} Error: {}'.format(ret.status_code, ret.text))
        raise Exception('Error getting events')
    return response



def round_start_end_dates(response):
    """
    Given a list of events in the response object, round the hours to the nearest half hour
    """
    for event in response['events']:
        event['start_dt'] = round_date(event['start_dt'])
        event['end_dt'] = round_date(event['end_dt'])

def round_date(date):
    """
    Given a date in the format YYYY-MM-DDTHH:MM:SS.SSSZ, round the hours to the nearest half hour
    """
    date_split = date.split('T')
    # print('Rounding: {} to {}'.format(date, round_time(date_split[1])))
    date_split[1] = round_time(date_split[1])
    return 'T'.join(date_split)

def round_time(time):
    """
    Given a time in the format HH:MM:SS.SSSZ, round the hours to the nearest half hour
    """
    time_split = time.split(':')
    if int(time_split[1]) == 0:
        return time
    else:
        if int(time_split[1]) >= 30:
            time_split[0] = str(int(time_split[0]) + 1)
            time_split[1] = '00'
        else:
            time_split[1] = '30'
        return ':'.join(time_split)


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

