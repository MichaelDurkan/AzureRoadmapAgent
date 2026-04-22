"""Sends the digest email via SMTP (works with Office 365, Gmail, SendGrid SMTP relay)."""
import logging
import os
import smtplib
import ssl
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List

from email_builder import build_html_email

logger = logging.getLogger(__name__)


def _get_required(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            "Check your Kubernetes Secret / ConfigMap."
        )
    return value


def send_digest_email(classified: Dict[str, List[Dict]], recipient: str, days: int = 7) -> None:
    """Build and send the weekly digest to *recipient* via SMTP.

    Required environment variables
    ───────────────────────────────
    SMTP_HOST       – e.g. smtp.office365.com  or  smtp.gmail.com
    SMTP_PORT       – default 587 (STARTTLS)
    SMTP_USER       – your SMTP login / sender address
    SMTP_PASSWORD   – app password or SMTP relay key
    SMTP_FROM       – optional display name + address, defaults to SMTP_USER
    """
    smtp_host = _get_required("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = _get_required("SMTP_USER")
    smtp_password = _get_required("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)

    now = datetime.now(timezone.utc)
    subject = (
        f"Azure Roadmap Weekly Digest — {now.strftime('%B %d, %Y')} "
        f"({sum(len(v) for v in classified.values())} updates)"
    )
    html_body = build_html_email(classified, days=days)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_from
    msg["To"] = recipient
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    logger.info("Connecting to SMTP %s:%s", smtp_host, smtp_port)
    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        server.ehlo()
        server.starttls(context=context)
        server.login(smtp_user, smtp_password)
        server.send_message(msg)

    logger.info("Digest email sent to %s", recipient)
