"""Fetches and normalises items from the Azure Updates RSS feed."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import feedparser

logger = logging.getLogger(__name__)

AZURE_UPDATES_FEED_URL = "https://azurecomcdn.azureedge.net/en-us/updates/feed/"


def fetch_recent_updates(days: int = 7) -> List[Dict]:
    """Return feed items published within the last *days* days.

    Each item is a plain dict with these keys:
        title, link, published_iso, published_display, summary, categories
    """
    logger.info("Fetching Azure Updates RSS feed (last %d days)", days)
    try:
        feed = feedparser.parse(AZURE_UPDATES_FEED_URL)
    except Exception as exc:
        logger.error("RSS fetch failed: %s", exc)
        return []

    if feed.get("bozo") and not feed.entries:
        logger.error("Feed parse error: %s", feed.get("bozo_exception"))
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    items: List[Dict] = []

    for entry in feed.entries:
        try:
            parsed_time = getattr(entry, "published_parsed", None)
            if not parsed_time:
                continue
            published = datetime(*parsed_time[:6], tzinfo=timezone.utc)
            if published < cutoff:
                continue

            categories = [
                t.term for t in getattr(entry, "tags", []) if hasattr(t, "term")
            ]

            items.append(
                {
                    "title": getattr(entry, "title", "Untitled"),
                    "link": getattr(entry, "link", "#"),
                    "published_iso": published.isoformat(),
                    "published_display": published.strftime("%d %b %Y"),
                    "summary": getattr(entry, "summary", ""),
                    "categories": categories,
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping entry due to parse error: %s", exc)

    logger.info("Found %d items in the last %d days", len(items), days)
    return items
