"""Weekly digest scheduler — runs as a Kubernetes CronJob.

Fetches the Azure Updates RSS feed, classifies items, and sends
a formatted HTML email via SMTP.  All configuration is read from
environment variables injected by the Kubernetes Secret / ConfigMap.

Required env vars  (from k8s/secret):
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD
    RECIPIENT_EMAIL

Optional env vars  (from k8s/configmap):
    LOOKBACK_DAYS   (default: 7)
    LOG_LEVEL       (default: INFO)
"""
import logging
import os
import sys

# ── bootstrap logging before any imports that might log ─────────────────────
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("scheduler")

# Shared modules are copied to /app by the Dockerfile (no package prefix needed)
from classifier import classify_updates  # noqa: E402
from email_sender import send_digest_email  # noqa: E402
from rss_fetcher import fetch_recent_updates  # noqa: E402


def main() -> int:
    recipient = os.getenv("RECIPIENT_EMAIL")
    if not recipient:
        logger.error("RECIPIENT_EMAIL environment variable is not set — aborting.")
        return 1

    days = int(os.getenv("LOOKBACK_DAYS", "7"))
    logger.info("Starting weekly Azure Roadmap digest (last %d days → %s)", days, recipient)

    items = fetch_recent_updates(days=days)
    if not items:
        logger.warning("No items returned from the RSS feed — skipping email send.")
        return 0

    classified = classify_updates(items)
    total = sum(len(v) for v in classified.values())
    logger.info(
        "Classified %d items: GA=%d, PublicPreview=%d, PrivatePreview=%d, "
        "Retirements=%d, SKU=%d, Other=%d",
        total,
        len(classified["ga"]),
        len(classified["public_preview"]),
        len(classified["private_preview"]),
        len(classified["retirements"]),
        len(classified["sku_changes"]),
        len(classified["other"]),
    )

    send_digest_email(classified, recipient, days=days)
    logger.info("Digest sent successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
