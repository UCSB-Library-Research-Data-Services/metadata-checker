import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.environ.get("SMTP_HOST", "localhost")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "25"))
SMTP_FROM_ADDRESS = os.environ.get("SMTP_FROM_ADDRESS", "metadata-checker@localhost")
SMTP_TIMEOUT_SECONDS = float(os.environ.get("SMTP_TIMEOUT_SECONDS", "10"))


class MailerError(Exception):
    """Raised when the local mail relay rejects or can't be reached for a send."""


#Sends a MIME email (plain-text fallback + HTML) via the configured SMTP relay
def send_html_email(to_address, subject, html_body):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM_ADDRESS
    msg["To"] = to_address
    msg.set_content("Your metadata report is attached as HTML. Please view this email in an HTML-capable client.")
    msg.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS) as smtp:
            smtp.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        raise MailerError(f"Failed to send email via {SMTP_HOST}:{SMTP_PORT}: {exc}") from exc
