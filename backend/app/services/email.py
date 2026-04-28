import io
import json
import logging
import smtplib
import zipfile
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, html_body: str) -> bool:
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        logger.warning("SMTP not configured, skipping email to %s", to_email)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        if settings.SMTP_USE_TLS:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)

        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD.get_secret_value())
        server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())
        server.quit()
        logger.info("Email sent to %s", to_email)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        return False


def send_password_reset_email(to_email: str, username: str, reset_token: str) -> bool:
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    subject = "Password Reset Request"
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Password Reset</h2>
        <p>Hello {username},</p>
        <p>We received a request to reset your password. Click the button below to set a new password:</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}"
               style="background-color: #4F46E5; color: white; padding: 12px 24px;
                      text-decoration: none; border-radius: 6px; display: inline-block;">
                Reset Password
            </a>
        </p>
        <p>This link will expire in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.</p>
        <p>If you didn't request a password reset, you can safely ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px;">
            If the button doesn't work, copy and paste this URL into your browser:<br>
            <a href="{reset_url}">{reset_url}</a>
        </p>
    </body>
    </html>
    """
    return send_email(to_email, subject, html_body)


def send_account_deletion_email(to_email: str, username: str, deletion_token: str) -> bool:
    deletion_url = f"{settings.FRONTEND_URL}/confirm-deletion?token={deletion_token}"
    subject = "Account Deletion Confirmation"
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #DC2626;">Account Deletion Request</h2>
        <p>Hello {username},</p>
        <p>We received a request to <strong>permanently delete</strong> your account and all associated data.
           This action is <strong>irreversible</strong>.</p>
        <p>The following data will be permanently removed:</p>
        <ul>
            <li>Your user profile</li>
            <li>All consumed products records</li>
            <li>All recipe consumption history</li>
            <li>All meal plan records</li>
            <li>All nutrition data</li>
            <li>All household memberships</li>
        </ul>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{deletion_url}"
               style="background-color: #DC2626; color: white; padding: 12px 24px;
                      text-decoration: none; border-radius: 6px; display: inline-block;">
                Confirm Account Deletion
            </a>
        </p>
        <p>This link will expire in 24 hours.</p>
        <p>If you didn't request this, you can safely ignore this email. Your account will remain active.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px;">
            If the button doesn't work, copy and paste this URL into your browser:<br>
            <a href="{deletion_url}">{deletion_url}</a>
        </p>
    </body>
    </html>
    """
    return send_email(to_email, subject, html_body)


def send_data_export_email(to_email: str, username: str, data: dict, export_type: str) -> bool:
    """Send data export email with JSON attachment.

    export_type: 'account' or 'household'
    """
    if export_type == "household":
        subject = "Your Household Data Export"
        description = "household"
    else:
        subject = "Your Account Data Export"
        description = "account"

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Data Export</h2>
        <p>Hello {username},</p>
        <p>You requested an export of your {description} data. The data is attached to this email
           as a ZIP archive containing one JSON file per table.</p>
        <p>Please save this file in a safe place.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px;">
            This email was sent because a data export was requested for your account.
        </p>
    </body>
    </html>
    """

    if not settings.SMTP_HOST or not settings.SMTP_USER:
        logger.warning("SMTP not configured, skipping data export email to %s", to_email)
        return False

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for table_name, rows in data.items():
            table_json = json.dumps(rows, ensure_ascii=False, indent=2)
            zf.writestr(f"{table_name}.json", table_json)

    attachment = MIMEBase("application", "zip")
    attachment.set_payload(zip_buffer.getvalue())
    encoders.encode_base64(attachment)
    attachment.add_header(
        "Content-Disposition", "attachment", filename=f"{description}_data_export.zip"
    )
    msg.attach(attachment)

    try:
        if settings.SMTP_USE_TLS:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)

        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD.get_secret_value())
        server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())
        server.quit()
        logger.info("Data export email sent to %s", to_email)
        return True
    except Exception:
        logger.exception("Failed to send data export email to %s", to_email)
        return False
