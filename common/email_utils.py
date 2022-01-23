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


def send_email(to_emails, cc_list, subject, body):

    to_emails = ['gmn314@yahoo.com']

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

    print('{} email with subject: {} sent to: {}'.format(datetime.datetime.now(), subject, to_emails))

# # Define email addresses to use
# addr_to   = 'xxxx@localdomain.com'
# addr_from = "xxxxx@gmail.com"

# # Define SMTP email server details
# smtp_server = 'smtp.gmail.com'
# smtp_user   = gmail_account
# smtp_pass   = gmail_password

# # Construct email
# msg = MIMEMultipart('alternative')
# msg['To'] = *emphasized text*addr_to
# msg['From'] = addr_from
# msg['Subject'] = 'Test Email From RPi'

# # Create the body of the message (a plain-text and an HTML version).
# text = "This is a test message.\nText and html."

# (your html code)

# # Record the MIME types of both parts - text/plain and text/html.
# part1 = MIMEText(text, 'plain')
# part2 = MIMEText(html, 'html')

# # Attach parts into message container.
# # According to RFC 2046, the last part of a multipart message, in this case
# # the HTML message, is best and preferred.
# msg.attach(part1)
# msg.attach(part2)

# # Send the message via an SMTP server
# s = smtplib.SMTP(smtp_server,587)
# s.ehlo()
# s.starttls()
# s.login(smtp_user,smtp_pass)
# s.sendmail(addr_from, addr_to, msg.as_string())
# s.quit()