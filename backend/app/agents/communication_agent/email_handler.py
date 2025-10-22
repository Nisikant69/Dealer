import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os

# Import the settings instance from our new config file
from ...core.config import settings

def send_email_with_attachment(recipient_email: str, subject: str, body: str, attachment_path: str):
    """
    Connects to an SMTP server and sends an email with an attachment.
    """
    if not recipient_email:
        raise ValueError("Recipient email cannot be empty.")

    try:
        # --- Email Message Setup ---
        msg = MIMEMultipart()
        msg['From'] = f"{settings.SMTP_SENDER_NAME} <{settings.SMTP_USER}>"
        msg['To'] = recipient_email
        msg['Subject'] = subject

        # Attach the email body
        msg.attach(MIMEText(body, 'plain'))

        # --- Attachment Setup ---
        if attachment_path and os.path.exists(attachment_path):
            filename = os.path.basename(attachment_path)
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}',
            )
            msg.attach(part)
        else:
            print(f"Warning: Attachment path not found: {attachment_path}")


        # --- SMTP Connection and Sending ---
        # Using a 'with' statement ensures the connection is automatically closed
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
            print(f"Email sent successfully to {recipient_email}")

    except Exception as e:
        print(f"Failed to send email to {recipient_email}. Error: {e}")
        # In a real application, you'd want more robust error handling/logging here
        raise
