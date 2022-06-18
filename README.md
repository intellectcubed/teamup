# teamup
Pull events from teamup calendar and ensure that shifts are covered


# Running
### Set up Python:
```
source ~/Downloads/env/bin/activate
source secrets.sh
```


## Environment variables:
stored in **prod.env** in the format: ```VARIABLE=VALUE```

## Command line arguments
|argument|Description|Default Value|
|-|-|-|
|start_date|Format YYYY-MM-DD (2022-01-01)|Current day|
|end_date|Format YYYY-MM-DD (2022-01-05)|5 days from today|
|send_email|[True, False] Should an email be sent?|False|
|headless|[True, False] Should the script be headless?|False|

---
## Testing check_coverage:
python-lambda-local -f lambda_handler check_coverage.py ./triggers/martinsville_trigger.json

### Or to test in the test environment:
python-lambda-local -f lambda_handler check_coverage.py ./triggers/squadsentry_trigger.json
--- 

## Sending email:
### Avoid multiple emails
In order to avoid multiple emails, the script will only send an email if a. there are any events to report, and b. the email has not been sent today.

### Email addresses
Email addresses are stored in the ```email.json``` file.  If an email is not found in the email address file, the script will look in the *notes* attribute in the shift
coverate object.  If it finds a string in the format: ```email: email@domain```, the script will use that address, and also add it to the emails.json file

* Shift infromation is sent to the member's email addresses that are in the shift.  
* Error (unstaffed shifts) are sent to ```martinsvillers@yahoo.com```
* If an email address is not found, and an email was not added to the ```notes:``` field, the email will be sent to just gnowakowski@gmail.com (the script owner)

