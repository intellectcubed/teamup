# teamup
Pull events from teamup calendar and ensure that shifts are covered


# Running
### Set up Python:
```
source ~/Downloads/env/bin/activate
source secrets.sh

  pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
```


## Export environment variables:
export TEAMUP_API_KEY_OTHER=<>
export TEAMUP_API_KEY=<>
export COLLABORATIVE_CALENDAR_KEY=<>
export COVERAGE_REQUIRED_CALENDAR=<>
export COVERAGE_OFFERED_CALENDAR=<>
export TANGO_REQUIRED_CALENDAR=<>
export TANGO_OFFERED_CALENDAR=<>


## Command line arguments
|argument|Description|Default Value|
|-|-|-|
|start_date|Format YYYY-MM-DD (2022-01-01)|Current day|
|end_date|Format YYYY-MM-DD (2022-01-05)|5 days from today|
|send_email|[True | False]|False


## Sample Command line
python check_coverage.py --start_date 2021-12-01 --end_date 2021-12-31 --send_email True
