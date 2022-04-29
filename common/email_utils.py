# Import smtplib to provide email functions
import smtplib
import datetime
from common.config_data import EmailConfig

# Import the email modules
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

class EmailUtil:

    def __init__(self, email_config: EmailConfig, is_test_mode=False):
        self.email_config = email_config
        self.is_test_mode = is_test_mode

    def send_html_email(self, to_emails, cc_list, subject, body):
        if self.is_test_mode:
            print('TestMode: Fake Sending email to: {}'.format(to_emails))
            return

        # print('Overriding to_emails {} with {}'.format(to_emails, "gmn314@yahoo.com"))
        # to_emails = ['gmn314@yahoo.com']

        # Create the container (outer) email message.
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = self.email_config.from_email_address
        msg['To'] = ', '.join(to_emails)
        if cc_list is not None and len(cc_list) > 0:
            msg['Cc'] = ', '.join(cc_list)

        # Assume that the message contains HTML
        msg.attach(MIMEText(body, 'html'))

        # Send the email via our own SMTP server.
        # s = smtplib.SMTP('smtp.gmail.com', 587)
        s = smtplib.SMTP(self.email_config.smtp_server, 587)
        s.starttls()
        s.login(self.email_config.email_account, self.email_config.email_password)
        s.send_message(msg)
        s.quit()

        print('{} email with subject: {} sent to: {} cc list: '.format(datetime.datetime.now(), subject, to_emails, cc_list))

    def send_email(self, to_emails, cc_list, subject, body):
        if self.is_test_mode:
            print('Test Mode: Fake Sending email to: {}'.format(to_emails))
            return

        # Create the container (outer) email message.
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.email_config.from_email_address
        msg['To'] = ', '.join(to_emails)
        if cc_list is not None and len(cc_list) > 0:
            msg['Cc'] = ', '.join(cc_list)


        # Send the email via our own SMTP server.
        s = smtplib.SMTP(self.email_config.smtp_server, 587)
        s.starttls()
        s.login(self.email_config.email_account, self.email_config.email_password)
        print('Sending from{} to{} msg{}'.format(self.email_config.from_email_address, to_emails, msg.as_string()))
        s.sendmail(self.email_config.from_email_address, to_emails, msg.as_string())
        s.quit()

        print('{} email with subject: {} sent to: {} cc list: '.format(datetime.datetime.now(), subject, to_emails, cc_list))
