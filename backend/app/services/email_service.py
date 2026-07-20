import smtplib
from email.message import EmailMessage

from app.config import settings


class EmailNotConfiguredError(RuntimeError):
    pass


def is_email_configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_username and settings.smtp_password and settings.smtp_from_email)


def send_email(to_email: str, subject: str, body: str) -> None:
    if not is_email_configured():
        raise EmailNotConfiguredError(
            "Email sending isn't configured -- set smtp_host/smtp_username/smtp_password/"
            "smtp_from_email in .env."
        )

    message = EmailMessage()
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)
