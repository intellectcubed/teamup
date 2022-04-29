from dataclasses import dataclass

@dataclass
class EmailConfig:
    email_from: str
    email_account: str
    email_password: str
    smtp_server: str

