"""Digest endpoints consumed by the Copilot Agent plugin."""
import logging
import os
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, EmailStr

from services.classifier import CATEGORY_LABELS, classify_updates
from services.email_sender import send_digest_email
from services.rss_fetcher import fetch_recent_updates

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Digest"])


# ── response models ──────────────────────────────────────────────────────────────

class UpdateItem(BaseModel):
    title: str
    link: str
    published_iso: str
    published_display: str
    summary: str
    categories: list[str]


class DigestResponse(BaseModel):
    period_days: int
    generated_at: str
    total_updates: int
    counts: dict[str, int]
    categories: dict[str, list[UpdateItem]]


class SendDigestRequest(BaseModel):
    recipient: Optional[EmailStr] = None
    days: int = 7


# ── endpoints ────────────────────────────────────────────────────────────────────

@router.get(
    "/digest",
    response_model=DigestResponse,
    summary="Get weekly Azure roadmap digest",
    description=(
        "Returns all Azure updates from the past *days* days grouped by category: "
        "Generally Available, Public Preview, Private Preview, Retirements, and SKU Changes."
    ),
    operation_id="getWeeklyDigest",
)
def get_digest(days: int = Query(default=7, ge=1, le=90, description="Lookback window in days")):
    items = fetch_recent_updates(days=days)
    classified = classify_updates(items)
    counts = {k: len(v) for k, v in classified.items() if k != "other"}
    total = sum(counts.values())
    return DigestResponse(
        period_days=days,
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_updates=total,
        counts=counts,
        categories={k: [UpdateItem(**i) for i in v] for k, v in classified.items()},
    )


@router.get(
    "/updates",
    summary="Get updates filtered by category",
    operation_id="getUpdatesByCategory",
)
def get_updates_by_category(
    category: Literal["ga", "public_preview", "private_preview", "retirements", "sku_changes", "all"] = Query(
        ..., description="Category to filter by, or 'all' for everything"
    ),
    days: int = Query(default=7, ge=1, le=90),
):
    items = fetch_recent_updates(days=days)
    if category == "all":
        return {
            "category": "all",
            "label": "All Updates",
            "count": len(items),
            "items": items,
        }
    classified = classify_updates(items)
    result = classified.get(category, [])
    return {
        "category": category,
        "label": CATEGORY_LABELS.get(category, category),
        "count": len(result),
        "items": result,
    }


@router.get(
    "/summary",
    summary="Get a plain-text summary for Copilot to narrate",
    operation_id="getDigestSummary",
)
def get_summary(days: int = Query(default=7, ge=1, le=90)):
    """Returns a concise Markdown-formatted summary suitable for Copilot to read aloud."""
    items = fetch_recent_updates(days=days)
    classified = classify_updates(items)

    lines = [
        f"## Azure Roadmap Digest — last {days} days\n",
        f"**Total updates:** {sum(len(v) for v in classified.values())}\n",
    ]
    section_order = ["ga", "public_preview", "private_preview", "retirements", "sku_changes"]
    icons = {"ga": "✅", "public_preview": "🔵", "private_preview": "🔒", "retirements": "⚠️", "sku_changes": "💲"}
    for key in section_order:
        entries = classified.get(key, [])
        label = CATEGORY_LABELS[key]
        lines.append(f"\n### {icons[key]} {label} ({len(entries)})\n")
        for item in entries[:20]:  # cap at 20 per section in summary
            lines.append(f"- [{item['title']}]({item['link']}) — {item['published_display']}")
        if len(entries) > 20:
            lines.append(f"- _…and {len(entries) - 20} more_")
    return {"summary": "\n".join(lines)}


@router.post(
    "/send-digest",
    summary="Trigger an immediate digest email",
    operation_id="sendDigestEmail",
)
def send_digest(body: SendDigestRequest, background_tasks: BackgroundTasks):
    """Queue a digest email. Uses RECIPIENT_EMAIL env var if no recipient is provided."""
    recipient = body.recipient or os.getenv("RECIPIENT_EMAIL")
    if not recipient:
        raise HTTPException(
            status_code=400,
            detail=(
                "No recipient email configured. "
                "Either set the RECIPIENT_EMAIL environment variable "
                "or pass 'recipient' in the request body."
            ),
        )
    background_tasks.add_task(_do_send, str(recipient), body.days)
    return {"status": "queued", "recipient": str(recipient), "days": body.days}


def _do_send(recipient: str, days: int) -> None:
    try:
        items = fetch_recent_updates(days=days)
        classified = classify_updates(items)
        send_digest_email(classified, recipient, days=days)
    except Exception as exc:
        logger.error("Failed to send digest email: %s", exc, exc_info=True)
