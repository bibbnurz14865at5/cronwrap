"""Notification backends for cronwrap alerts (Slack and email)."""

import smtplib
import urllib.request
import urllib.error
import json
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger(__name__)


class NotificationError(Exception):
    """Raised when a notification cannot be delivered."""


def notify_slack(webhook_url: str, message: str, job_name: Optional[str] = None) -> None:
    """Send a message to a Slack channel via an Incoming Webhook URL."""
    title = f"*[cronwrap] Job `{job_name}` failed*" if job_name else "*[cronwrap] Job failed*"
    payload = {
        "text": f"{title}\n```{message}```"
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                raise NotificationError(
                    f"Slack webhook returned HTTP {resp.status}"
                )
    except urllib.error.URLError as exc:
        raise NotificationError(f"Failed to reach Slack webhook: {exc}") from exc


def notify_email(
    smtp_host: str,
    smtp_port: int,
    sender: str,
    recipients: list,
    message: str,
    job_name: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    use_tls: bool = True,
) -> None:
    """Send a failure notification via SMTP email."""
    subject = f"[cronwrap] Job `{job_name}` failed" if job_name else "[cronwrap] Job failed"

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(message, "plain"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            if use_tls:
                server.starttls()
            if username and password:
                server.login(username, password)
            server.sendmail(sender, recipients, msg.as_string())
    except smtplib.SMTPException as exc:
        raise NotificationError(f"Failed to send email: {exc}") from exc


def dispatch(
    config,
    message: str,
    job_name: Optional[str] = None,
) -> None:
    """Dispatch failure notifications according to the provided CronwrapConfig."""
    if config.slack_webhook_url:
        try:
            notify_slack(config.slack_webhook_url, message, job_name=job_name)
            logger.info("Slack notification sent for job '%s'", job_name)
        except NotificationError as exc:
            logger.error("Slack notification failed: %s", exc)

    if config.email_recipients and config.smtp_host:
        try:
            notify_email(
                smtp_host=config.smtp_host,
                smtp_port=config.smtp_port or 587,
                sender=config.email_sender or "cronwrap@localhost",
                recipients=config.email_recipients,
                message=message,
                job_name=job_name,
                username=config.smtp_username,
                password=config.smtp_password,
                use_tls=config.smtp_use_tls if config.smtp_use_tls is not None else True,
            )
            logger.info("Email notification sent for job '%s'", job_name)
        except NotificationError as exc:
            logger.error("Email notification failed: %s", exc)
