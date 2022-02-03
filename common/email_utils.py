# Import smtplib to provide email functions
import smtplib
import os
import datetime


# Import the email modules
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from_email = os.environ['FROM_EMAIL_ADDRESS']
email_account = os.environ['EMAIL_ACCOUNT']
email_password = os.environ['EMAIL_PASSWORD']
smtp_server = os.environ['SMTP_SERVER']

def send_html_email(to_emails, cc_list, subject, body):

    # print('Overriding to_emails {} with {}'.format(to_emails, "gmn314@yahoo.com"))
    # to_emails = ['gmn314@yahoo.com']

    # Create the container (outer) email message.
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = ', '.join(to_emails)
    if cc_list is not None and len(cc_list) > 0:
        msg['Cc'] = ', '.join(cc_list)

    # Assume that the message contains HTML
    msg.attach(MIMEText(body, 'html'))

    # Send the email via our own SMTP server.
    # s = smtplib.SMTP('smtp.gmail.com', 587)
    s = smtplib.SMTP(smtp_server, 587)
    s.starttls()
    s.login(email_account, email_password)
    s.send_message(msg)
    s.quit()

    print('{} email with subject: {} sent to: {} cc list: '.format(datetime.datetime.now(), subject, to_emails, cc_list))

def send_email(to_emails, cc_list, subject, body):

    # Create the container (outer) email message.
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = ', '.join(to_emails)
    if cc_list is not None and len(cc_list) > 0:
        msg['Cc'] = ', '.join(cc_list)


    # Send the email via our own SMTP server.
    s = smtplib.SMTP(smtp_server, 587)
    s.starttls()
    s.login(email_account, email_password)
    print('Sending from{} to{} msg{}'.format(from_email, to_emails, msg.as_string()))
    s.sendmail(from_email, to_emails, msg.as_string())
    s.quit()

    print('{} email with subject: {} sent to: {} cc list: '.format(datetime.datetime.now(), subject, to_emails, cc_list))
