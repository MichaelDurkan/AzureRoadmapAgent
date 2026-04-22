"""Builds the HTML digest email from classified Azure update items."""
from datetime import datetime, timezone
from typing import Dict, List

# ── section styling ──────────────────────────────────────────────────────────────
_SECTION_META = {
    "ga": {
        "icon": "✅",
        "label": "Generally Available",
        "color": "#107c10",
        "bg": "#f0f9f0",
        "row_alt": "#e8f5e8",
    },
    "public_preview": {
        "icon": "🔵",
        "label": "Public Preview",
        "color": "#0078d4",
        "bg": "#f0f7ff",
        "row_alt": "#e5f2ff",
    },
    "private_preview": {
        "icon": "🔒",
        "label": "Private Preview",
        "color": "#5c2d91",
        "bg": "#f8f4ff",
        "row_alt": "#ede8f7",
    },
    "retirements": {
        "icon": "⚠️",
        "label": "Retirements &amp; End of Support",
        "color": "#d13438",
        "bg": "#fff5f5",
        "row_alt": "#fde8e8",
    },
    "sku_changes": {
        "icon": "💲",
        "label": "SKU &amp; Pricing Changes",
        "color": "#ca5010",
        "bg": "#fff8f0",
        "row_alt": "#fdeede",
    },
}

_ORDERED_CATEGORIES = ["ga", "public_preview", "private_preview", "retirements", "sku_changes"]


def _render_section(key: str, items: List[Dict]) -> str:
    meta = _SECTION_META[key]
    count = len(items)
    if count == 0:
        return (
            f'<h2 style="color:{meta["color"]};border-left:4px solid {meta["color"]};'
            f'padding-left:12px;margin-top:32px;">'
            f'{meta["icon"]} {meta["label"]} (0)</h2>'
            f'<p style="color:#888;font-style:italic;margin-left:16px;">'
            f'No updates in this category this week.</p>'
        )

    rows = []
    for i, item in enumerate(items):
        bg = meta["row_alt"] if i % 2 == 0 else "#ffffff"
        rows.append(
            f'<tr style="background:{bg};">'
            f'<td style="padding:9px 14px;">'
            f'<a href="{item["link"]}" style="color:#0078d4;text-decoration:none;font-weight:500;">'
            f'{item["title"]}</a></td>'
            f'<td style="padding:9px 14px;white-space:nowrap;color:#666;font-size:12px;">'
            f'{item["published_display"]}</td>'
            f'</tr>'
        )

    return (
        f'<h2 style="color:{meta["color"]};border-left:4px solid {meta["color"]};'
        f'padding-left:12px;margin-top:32px;">'
        f'{meta["icon"]} {meta["label"]} ({count})</h2>'
        f'<table width="100%" cellpadding="0" cellspacing="0" '
        f'style="border-collapse:collapse;margin-top:8px;border:1px solid #e0e0e0;border-radius:4px;">'
        f'<thead><tr style="background:{meta["bg"]};">'
        f'<th style="padding:8px 14px;text-align:left;font-size:13px;color:#444;font-weight:600;">Feature / Service</th>'
        f'<th style="padding:8px 14px;text-align:left;font-size:13px;color:#444;font-weight:600;width:100px;">Date</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'</table>'
    )


def build_html_email(classified: Dict[str, List[Dict]], days: int = 7) -> str:
    """Return a complete HTML email string for the weekly digest."""
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%B %d, %Y")

    counts = {k: len(classified.get(k, [])) for k in _ORDERED_CATEGORIES}
    total = sum(counts.values())

    summary_chips = [
        f'<span style="margin-right:16px;color:{_SECTION_META[k]["color"]};">'
        f'{_SECTION_META[k]["icon"]} {_SECTION_META[k]["label"]}: <strong>{counts[k]}</strong></span>'
        for k in _ORDERED_CATEGORIES
    ]

    sections_html = "\n".join(
        _render_section(k, classified.get(k, [])) for k in _ORDERED_CATEGORIES
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Azure Roadmap Weekly Digest</title>
</head>
<body style="margin:0;padding:24px;background:#f3f3f3;font-family:'Segoe UI',Arial,sans-serif;">
  <div style="max-width:800px;margin:0 auto;background:#ffffff;border-radius:8px;
              overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,0.10);">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#0078d4 0%,#004578 100%);padding:36px 44px;">
      <h1 style="color:#ffffff;margin:0;font-size:26px;font-weight:600;letter-spacing:-0.3px;">
        ☁️ Azure Roadmap Weekly Digest
      </h1>
      <p style="color:#a8d4f5;margin:10px 0 0;font-size:14px;">
        Week ending {date_str} &nbsp;·&nbsp; Last {days} days &nbsp;·&nbsp;
        <strong style="color:#fff;">{total}</strong> total updates
      </p>
    </div>

    <!-- Summary bar -->
    <div style="background:#e8f4fd;border-bottom:1px solid #bdd7ee;padding:14px 44px;
                font-size:13px;line-height:2;">
      {"".join(summary_chips)}
    </div>

    <!-- Content -->
    <div style="padding:28px 44px 40px;">
      {sections_html}
    </div>

    <!-- Footer -->
    <div style="background:#f8f8f8;border-top:1px solid #e8e8e8;padding:18px 44px;
                text-align:center;font-size:12px;color:#999;">
      Generated by the Azure Roadmap Copilot Agent &nbsp;·&nbsp;
      <a href="https://azure.microsoft.com/en-us/updates/"
         style="color:#0078d4;">View all Azure Updates</a>
    </div>

  </div>
</body>
</html>"""
