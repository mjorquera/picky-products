#!/usr/bin/env python3
"""
Picky Products — Daily Pin Publisher
Finds pins due for publishing and sends them to Make.

Usage:
    python3 publish_due_pins.py [--dry-run]

What it does:
    1. Scans pins/*/schedule_meta.json for any records where publish_at <= now
    2. Checks Notion to skip any already Scheduled/Distributed
    3. Sends due pins to Make webhook → Pinterest publishes them
    4. Updates Notion status → Scheduled
    5. If all 9 pins for a product are done, moves folder → pins/scheduled/

Run daily via Cowork scheduled task.
"""

import sys
import os
import json
import glob
import shutil
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests --break-system-packages")
    sys.exit(1)

# ── Config ─────────────────────────────────────────────────────────────────────
WORKSPACE    = os.path.dirname(os.path.abspath(__file__))
ENV_PATH     = os.path.join(WORKSPACE, ".env")
MAKE_WEBHOOK = "https://hook.eu2.make.com/1ug4xsjoxp8jycg7dungek86smnuuorn"
GITHUB_PAGES = "https://mjorquera.github.io/picky-products"
BOARD_ID     = "1063764443174541558"
NOTION_API   = "https://api.notion.com/v1"


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


def notion_get_status(token: str, page_id: str) -> str:
    resp = requests.get(
        f"{NOTION_API}/pages/{page_id}",
        headers={"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28"},
    )
    if resp.status_code == 200:
        sel = resp.json().get("properties", {}).get("Status", {}).get("select") or {}
        return sel.get("name", "")
    return ""


def notion_set_status(token: str, page_id: str, status: str = "Scheduled") -> bool:
    resp = requests.patch(
        f"{NOTION_API}/pages/{page_id}",
        headers={
            "Authorization":  f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type":   "application/json",
        },
        json={"properties": {"Status": {"select": {"name": status}}}},
    )
    return resp.status_code in (200, 201)


def send_to_make(records: list) -> bool:
    resp = requests.post(
        MAKE_WEBHOOK,
        json={"board_id": BOARD_ID, "records": records},
        timeout=30,
    )
    return resp.status_code in (200, 201, 202, 204)


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    dry_run = "--dry-run" in sys.argv
    now     = datetime.now(timezone.utc)

    print(f"\n{'━'*62}")
    print(f"  Picky Products — Daily Pin Publisher")
    print(f"  {now.strftime('%a %Y-%m-%d %H:%M UTC')}{' [DRY RUN]' if dry_run else ''}")
    print(f"{'━'*62}\n")

    env = read_env()
    notion_token = env.get("NOTION_TOKEN")
    if not notion_token:
        print("ERROR: NOTION_TOKEN not in .env")
        sys.exit(1)

    # ── Scan active products ───────────────────────────────────────────────────
    meta_files = sorted(glob.glob(os.path.join(WORKSPACE, "pins", "*", "schedule_meta.json")))

    if not meta_files:
        print("No active products in pins/ — nothing to publish.\n")
        return

    due = []  # list of (slug, record_dict)

    for meta_path in meta_files:
        slug = os.path.basename(os.path.dirname(meta_path))
        with open(meta_path) as f:
            meta = json.load(f)

        for rec in meta.get("records", []):
            raw_date = rec.get("publish_at", "")
            if not raw_date:
                continue
            try:
                pub_dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            except Exception:
                continue

            if pub_dt > now:
                continue  # Not due yet

            # Check Notion — skip if already published
            status = notion_get_status(notion_token, rec["notion_page_id"])
            if status in ("Scheduled", "Distributed"):
                continue

            due.append((slug, rec))

    # ── Report ────────────────────────────────────────────────────────────────
    if not due:
        print("No pins due for publishing right now.\n")
        return

    print(f"Found {len(due)} pin(s) due:\n")
    for slug, rec in due:
        pub = rec.get("publish_at", "")[:10]
        print(f"  [{slug}]  {rec['title'][:50]}  ({pub})")
    print()

    if dry_run:
        print("Dry run — nothing sent.\n")
        return

    # ── Send to Make ──────────────────────────────────────────────────────────
    print("Sending to Make...")
    payload_records = [
        {
            "notion_page_id": rec["notion_page_id"],
            "title":          rec["title"],
            "description":    rec["description"],
            "affiliate_link": rec["affiliate_link"],
            "publish_at":     rec["publish_at"],
            "image_url":      f"{GITHUB_PAGES}/pins/{slug}/{rec['pin_file']}",
        }
        for slug, rec in due
    ]

    if not send_to_make(payload_records):
        print("  ✗ Make webhook failed\n")
        sys.exit(1)

    print(f"  ✓ {len(due)} pin(s) sent\n")

    # ── Update Notion ─────────────────────────────────────────────────────────
    print("Updating Notion...")
    for slug, rec in due:
        ok   = notion_set_status(notion_token, rec["notion_page_id"])
        mark = "✓" if ok else "✗"
        print(f"  {mark} {rec['title'][:55]}")

    # ── Move completed products ───────────────────────────────────────────────
    slugs = set(s for s, _ in due)
    for slug in slugs:
        meta_path = os.path.join(WORKSPACE, "pins", slug, "schedule_meta.json")
        if not os.path.exists(meta_path):
            continue
        with open(meta_path) as f:
            meta = json.load(f)

        all_done = all(
            notion_get_status(notion_token, r["notion_page_id"]) in ("Scheduled", "Distributed")
            for r in meta["records"]
        )
        if all_done:
            src = os.path.join(WORKSPACE, "pins", slug)
            dst = os.path.join(WORKSPACE, "pins", "scheduled", slug)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.move(src, dst)
            print(f"\n  ✓ All 9 published → moved to pins/scheduled/{slug}/")

    print(f"\nDone.\n")


if __name__ == "__main__":
    main()
