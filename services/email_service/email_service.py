# services/email_service.py
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


def send_email_notification(subject, message, to_email=None):
    """
    Send email notification using Gmail SMTP

    Args:
        subject: Email subject
        message: Email body message
        to_email: Recipient email address (defaults to team email if None)
    """
    gmail_user = os.environ.get('GMAIL_USER')
    gmail_password = os.environ.get('GMAIL_PASSWORD')
    recipient = to_email or os.environ.get('TEAM_EMAIL')

    if not gmail_user or not gmail_password or not recipient:
        logger.error(
            "Email credentials not configured. Set GMAIL_USER, GMAIL_PASSWORD, and TEAM_EMAIL environment variables.")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = recipient
        msg['Subject'] = subject

        msg.attach(MIMEText(message, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.send_message(msg)
        server.quit()

        logger.info(f"Email notification sent to {recipient}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False


if __name__ == "__main__":
    # Example usage
    send_email_notification(
        subject="Test Email",
        message="This is a test email from the email service.",
        to_email="w.piyumal2319@gmail.com"
    )
