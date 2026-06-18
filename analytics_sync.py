#!/usr/bin/env python3
"""
Picky Products — Pinterest Analytics Sync
Finds published pins in Notion Distribution DB that have a Pinterest Pin ID,
fetches impression and outbound-click data from Pinterest Analytics API v5,
and writes the metrics back to Notion.

Prerequisites:
    - Distribution DB must have fields: Pinterest Pin ID (text),
      Impressions (number), Outbound Clicks (number)
    - Make scenario must write Pin ID to Notion after creating each pin

Usage:
    python3 analytics_sync.py [--dry-run]

Run weekly via Cowork scheduled task.
"""

import sys
import os
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests --break-system-packages")
    sys.exit(1)

# ── Config ─────────────────────────────────────────────────────────────────────
WORKSPACE       = os.path.dirname(os.path.abspath(__file__))
ENV_PATH        = os.path.join(WORKSPACE, ".env")
NOTION_API      = "https://api.notion.com/v1"
PINTEREST_API   = "https://api.pinterest.com/v5"
DISTRIBUTION_DB = "c7718096-68b1-83ea-8ab2-01b6e3a2b2fe"
START_DATE      = "2026-01-01"  # beginning of project — effectively lifetime totals


# ── Helpers ────────────────────────────────────────────────────────────────────
def read_env() -> dict:
    env = {}
    if not os.path.exists(ENV_PATH):
        return env
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"')
    return env


def notion_query_pins_with_id(token: str) -> list:
    """Return all Distribution DB pages that are Published and have a Pin ID."""
    url     = f"{NOTION_API}/databases/{DISTRIBUTION_DB}/query"
    headers = {
        "Authorization":  f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type":   "application/json",
    }
    payload = {
        "filter": {
            "and": [
                {"property": "Status",           "select":    {"equals":       "Published"}},
                {"property": "Pinterest Pin ID", "rich_text": {"is_not_empty": True}},
            ]
        }
    }
    pages = []
    while True:
        resp = requests.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        pages.extend(data["results"])
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
    return pages


def extract_pin_id(page: dict) -> str:
    rich_text = page.get("properties", {}).get("Pinterest Pin ID", {}).get("rich_text", [])
    return rich_text[0].get("plain_text", "") if rich_text else ""


def extract_title(page: dict) -> str:
    title_list = page.get("properties", {}).get("Title", {}).get("title", [])
    return title_list[0].get("plain_text", "")[:55] if title_list else page["id"]


def fetch_pin_analytics(pin_id: str, access_token: str, end_date: str) -> dict | None:
    """
    Calls Pinterest Analytics API v5 for a single pin.
    Returns {"impressions": int, "clicks": int} or None on error.
    """
    resp = requests.get(
        f"{PINTEREST_API}/pins/{pin_id}/analytics",
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "start_date":   START_DATE,
            "end_date":     end_date,
            "metric_types": "IMPRESSION,OUTBOUND_CLICK",
        },
        timeout=15,
    )
    if resp.status_code == 401:
        print("    ✗ 401 Unauthorised — run refresh_pinterest_token.py and retry")
        return None
    if resp.status_code != 200:
        print(f"    ✗ Pinterest API {resp.status_code}: {resp.text[:120]}")
        return None

    data = resp.json()
    # Pinterest v5 returns summary_metrics as a sum over the requested date range
    summary = data.get("all", {}).get("summary_metrics", {})
    if summary:
        return {
            "impressions": int(summary.get("IMPRESSION", 0)),
            "clicks":      int(summary.get("OUTBOUND_CLICK", 0)),
        }

    # Fallback: sum daily_metrics
    impressions = clicks = 0
    for day in data.get("all", {}).get("daily_metrics", []):
        m = day.get("metrics", day)  # v5 wraps in "metrics"; older shape doesn't
        impressions += int(m.get("IMPRESSION", 0))
        clicks      += int(m.get("OUTBOUND_CLICK", 0))
    return {"impressions": impressions, "clicks": clicks}


def notion_update_metrics(token: str, page_id: str, impressions: int, clicks: int) -> bool:
    resp = requests.patch(
        f"{NOTION_API}/pages/{page_id}",
        headers={
            "Authorization":  f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type":   "application/json",
        },
        json={
            "properties": {
                "Impressions":    {"number": impressions},
                "Outbound Clicks": {"number": clicks},
            }
        },
    )
    return resp.status_code in (200, 201)


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    dry_run  = "--dry-run" in sys.argv
    now      = datetime.now(timezone.utc)
    end_date = now.strftime("%Y-%m-%d")

    print(f"\n{'━'*62}")
    print(f"  Picky Products — Analytics Sync")
    print(f"  {now.strftime('%a %Y-%m-%d %H:%M UTC')}{' [DRY RUN]' if dry_run else ''}")
    print(f"{'━'*62}\n")

    env = read_env()
    notion_token  = env.get("NOTION_TOKEN")
    access_token  = env.get("PINTEREST_ACCESS_TOKEN")

    if not notion_token:
        print("ERROR: NOTION_TOKEN not in .env")
        sys.exit(1)
    if not access_token:
        print("ERROR: PINTEREST_ACCESS_TOKEN not in .env")
        sys.exit(1)

    print("Querying Notion for published pins with Pin IDs...")
    try:
        pages = notion_query_pins_with_id(notion_token)
    except Exception as e:
        print(f"ERROR: Notion query failed — {e}")
        sys.exit(1)

    if not pages:
        print("No published pins with Pin IDs found.")
        print("Complete the Make scenario update so Pin IDs are captured at publish time.\n")
        return

    print(f"Found {len(pages)} pin(s). Fetching analytics ({START_DATE} → {end_date})...\n")

    updated = errors = 0

    for page in pages:
        page_id = page["id"]
        pin_id  = extract_pin_id(page)
        title   = extract_title(page)

        print(f"  {title}")
        print(f"  Pin ID: {pin_id}")

        if dry_run:
            print(f"  [dry run] would fetch analytics and update Notion\n")
            continue

        metrics = fetch_pin_analytics(pin_id, access_token, end_date)
        if metrics is None:
            errors += 1
            print()
            continue

        ok   = notion_update_metrics(notion_token, page_id, metrics["impressions"], metrics["clicks"])
        mark = "✓" if ok else "✗"
        print(f"  {mark} {metrics['impressions']:,} impressions / {metrics['clicks']:,} clicks\n")
        if ok:
            updated += 1
        else:
            errors += 1

    print(f"{'━'*62}")
    print(f"  Done — {updated} updated, {errors} errors.")
    print(f"{'━'*62}\n")


if __name__ == "__main__":
    main()
