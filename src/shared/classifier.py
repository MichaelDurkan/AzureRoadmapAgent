"""Classifies Azure Update items into roadmap categories."""
from typing import Dict, List

# ── keyword sets ────────────────────────────────────────────────────────────────
_GA_CAT_KEYWORDS = {"generally available", "now-available"}
_PUBLIC_PREVIEW_CAT_KEYWORDS = {"public preview"}
_PRIVATE_PREVIEW_CAT_KEYWORDS = {"private preview"}
_RETIREMENT_CAT_KEYWORDS = {"retirement", "retirements"}
_RETIREMENT_TITLE_KEYWORDS = {
    "retire",
    "end of support",
    "end-of-support",
    "end of life",
    "end-of-life",
    "decommission",
    "being discontinued",
}
_SKU_TITLE_KEYWORDS = {
    "sku",
    "pricing change",
    "price change",
    "tier change",
    "billing change",
    "cost change",
    "price update",
}

# Ordered list of (category_name, test_function) — first match wins.
# "other" is the implicit fallback.
CATEGORY_LABELS = {
    "ga": "Generally Available",
    "public_preview": "Public Preview",
    "private_preview": "Private Preview",
    "retirements": "Retirements & End of Support",
    "sku_changes": "SKU & Pricing Changes",
    "other": "Other Updates",
}


def _cats_lower(item: Dict) -> str:
    return " ".join(item.get("categories", [])).lower()


def _title_lower(item: Dict) -> str:
    return item.get("title", "").lower()


def classify_item(item: Dict) -> str:
    """Return the category key for a single update item."""
    cats = _cats_lower(item)
    title = _title_lower(item)

    if any(k in cats for k in _GA_CAT_KEYWORDS) or "(ga)" in title or "now ga" in title:
        return "ga"
    if any(k in cats for k in _PUBLIC_PREVIEW_CAT_KEYWORDS):
        return "public_preview"
    if any(k in cats for k in _PRIVATE_PREVIEW_CAT_KEYWORDS):
        return "private_preview"
    if any(k in cats for k in _RETIREMENT_CAT_KEYWORDS) or any(
        k in title for k in _RETIREMENT_TITLE_KEYWORDS
    ):
        return "retirements"
    if any(k in title for k in _SKU_TITLE_KEYWORDS) or "pricing" in cats:
        return "sku_changes"
    return "other"


def classify_updates(items: List[Dict]) -> Dict[str, List[Dict]]:
    """Group a list of update items by category.

    Returns a dict with keys: ga, public_preview, private_preview,
    retirements, sku_changes, other.
    """
    result: Dict[str, List[Dict]] = {k: [] for k in CATEGORY_LABELS}
    for item in items:
        result[classify_item(item)].append(item)
    return result
