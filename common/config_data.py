from dataclasses import dataclass
import os
import boto3
from boto3.dynamodb.conditions import Key
from enum import Enum
import json
import datetime

dynamodb = boto3.resource('dynamodb')
agency_configuration_table_name = os.environ.get("AGENCY_CONFIGURATION_TABLE_NAME", "agency_configuration")

agency_map = {
    'green knoll': '34',
    'finderne': '35',
    'manville': '42',
    'martinsville': '43',
    'somerville': '54',
    'bradley gardens': '39'
}

@dataclass
class RunTrigger:
    time: str
    agency: str
    report_type: str

@dataclass
class TeamupConfig:
    teamup_api_key: str
    required_calendar_key_admin: str # Administers the required calendar
    all_calendar_key_ro: str # Has read only access to all calendars
    offered_calendar_key_admin: str # Administers the offered calendar
    coverage_required_calendar: str
    coverage_offered_calendar: str
    level_mappings: dict

@dataclass 
class EmailConfig:
    from_email_address: str
    email_account: str
    email_password: str
    smtp_server: str

@dataclass
class EmailRecipients:
    admin_email: str
    shift_error_receipents: list

@dataclass
class AgencyConfig:
    notify_shift_within_days: int
    check_errors_within_days: int = 5

@dataclass
class Settings:
    notify_shift_within_days: int

@dataclass
class RunConfig:
    agency: str
    run_trigger: RunTrigger
    teamup_config: TeamupConfig
    agency_settings: AgencyConfig    
    email_account: EmailConfig
    email_recipients: EmailRecipients

"""
CoverageLevels provides the abstraction into specific levels of coverage (that are unique to each agency).
To get the value of the TeamUp enum, use the following: 

   run_config.agency_settings['coverage_levels'][CoverageLevels.CREW_CHIEF.value]
"""

class CoverageLevels(Enum):
    CREW_CHIEF = 'Crew Chief'
    EMT_OVER_18 = 'EMT (over 18)'
    EMT_UNDER_18 = 'EMT (under 18)'
    ASSISTANT = 'Assistant'
    DRIVER = 'Driver'
    DO_NOT_SELECT = 'Coverage Required DO NOT SELECT'

class EventCalendarsKeys(Enum):
    REQUIRED = 'coverage_required'
    OFFERED = 'coverage_offered'

# Check if coverage level is correct
def is_coverage_level(obj):
    try:
        CoverageLevels(obj)
    except ValueError:
        return False
    return True


def agency_config_from_json(config_j):
    return AgencyConfig(
            config_j['notify_shift_within_days']
    )

def email_config_from_json(config_j):
    return EmailConfig(
            config_j['from_email_address'],
            config_j['email_account'],
            config_j['email_password'],
            config_j['smtp_server'])

def teamup_config_from_json(config_j):
    return TeamupConfig(
            config_j['teamup_api_key'],
            config_j['required_calendar_key_admin'],
            config_j['all_calendar_key_ro'],
            config_j['offered_calendar_key_admin'],
            config_j['coverage_required_calendar'],
            config_j['coverage_offered_calendar'],
            config_j['level_mappings']);

def email_recipients_from_json(config_j):
    return EmailRecipients(
            config_j['admin_email'],
            config_j['shift_error_recipients']);

def run_config_from_json(run_trigger: RunTrigger, config_j):
    return RunConfig(
            config_j['agency'],
            run_trigger,
            teamup_config_from_json(config_j['team_up_calendar']),
            agency_config_from_json(config_j['agency_settings']),
            email_config_from_json(config_j['email_account']),
            email_recipients_from_json(config_j['recipients'])
    )   

def read_configuration(run_trigger: RunTrigger):
    retval = dynamodb.Table(agency_configuration_table_name).query(KeyConditionExpression=Key('agency').eq(run_trigger.agency))
    if len(retval['Items']) == 0:
        raise Exception('No configuration found for {}'.format(run_trigger.agency))
    
    config_json = retval['Items'][0]
    return run_config_from_json(run_trigger, config_json)

def read_trigger(filename) -> RunTrigger:
    trigger_json = None
    with open(filename) as f:
        trigger_json = json.load(f)

    return RunTrigger(datetime.datetime.now().isoformat(), trigger_json['agency'], trigger_json['report_type'])
