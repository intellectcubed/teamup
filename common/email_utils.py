# Import smtplib to provide email functions
import smtplib
import os

# Import the email modules
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

gmail_account = os.environ['FROM_EMAIL']
gmail_password = os.environ['GMAIL_PWD']


def send_email(to_email, subject, body):
    # Create the container (outer) email message.
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = gmail_account
    msg['To'] = to_email

    # Assume that the message contains HTML
    msg.attach(MIMEText(body, 'html'))

    # Send the email via our own SMTP server.
    # s = smtplib.SMTP('smtp.gmail.com', 587)
    s = smtplib.SMTP('smtp.mail.yahoo.com', 587)
    s.starttls()
    print('creds: {} - {}'.format(gmail_account, gmail_password))
    s.login(gmail_account, gmail_password)
    s.send_message(msg)
    s.quit()

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