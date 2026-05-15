#!/usr/bin/env python3
"""
Picky Products — Pinterest Scheduler via Make webhook
Posts all 9 pins for a product by sending schedule data to Make,
which calls Pinterest API v5 with publish_at scheduling.

Usage:
    python3 schedule_via_make.py <product-slug>

Example:
    python3 schedule_via_make.py silentnight-cool-touch-pillow

What it does:
    1. Reads pins/<product-slug>/schedule_meta.json
    2. Constructs GitHub Pages image URLs for each pin
    3. POSTs all 9 records to Make webhook
    4. Updates each Notion Distribution DB record → Status: Scheduled
    5. Moves pins/<product-slug>/ → pins/scheduled/<product-slug>/

Prerequisites:
    - Images pushed to docs/pins/<product-slug>/ in GitHub repo
    - schedule_meta.json written by Cowork during 'process [product]'
    - NOTION_TOKEN in .env
    - Make scenario active and listening on webhook URL
"""

import sys
import os
import json
import shutil

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests --break-system-packages")
    sys.exit(1)

# ── Config ─────────────────────────────────────────────────────────────────────
WORKSPACE       = os.path.dirname(os.path.abspath(__file__))
ENV_PATH        = os.path.join(WORKSPACE, ".env")
MAKE_WEBHOOK    = "https://hook.eu2.make.com/1ug4xsjoxp8jycg7dungek86smnuuorn"
GITHUB_PAGES    = "https://mjorquera.github.io/picky-products"
PINTEREST_BOARD = "1063764443174541558"
NOTION_API      = "https://api.notion.com/v1"


# ── .env helpers ───────────────────────────────────────────────────────────────
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




# ── Notion ─────────────────────────────────────────────────────────────────────
def update_notion_status(notion_token: str, page_id: str, status: str = "Scheduled"):
    resp = requests.patch(
        f"{NOTION_API}/pages/{page_id}",
        headers={
            "Authorization":  f"Bearer {notion_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type":   "application/json",
        },
        json={"properties": {"Status": {"select": {"name": status}}}},
    )
    if resp.status_code not in (200, 201):
        print(f"    ⚠ Notion update failed ({resp.status_code}): {resp.text[:120]}")
    return resp


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("Usage: python3 schedule_via_make.py <product-slug>")
        print("Example: python3 schedule_via_make.py silentnight-cool-touch-pillow")
        sys.exit(1)

    slug = sys.argv[1]
    base = os.path.join(WORKSPACE, "pins", slug)

    if not os.path.isdir(base):
        print(f"ERROR: Folder not found: pins/{slug}/")
        sys.exit(1)

    print(f"\n{'━'*62}")
    print(f"  Picky Products — Make Scheduler")
    print(f"  Product: {slug}")
    print(f"{'━'*62}\n")

    # ── Load config ────────────────────────────────────────────────────────────
    env          = read_env()
    notion_token = env.get("NOTION_TOKEN")

    if not notion_token:
        print("ERROR: NOTION_TOKEN not in .env")
        sys.exit(1)

    # ── Load schedule_meta.json ────────────────────────────────────────────────
    meta_path = os.path.join(base, "schedule_meta.json")
    if not os.path.exists(meta_path):
        print(f"ERROR: schedule_meta.json not found at pins/{slug}/")
        sys.exit(1)

    with open(meta_path) as f:
        meta = json.load(f)

    records = meta.get("records", [])
    if len(records) != 9:
        print(f"ERROR: Expected 9 records, found {len(records)}")
        sys.exit(1)

    # ── Validate PNGs + build image URLs ──────────────────────────────────────
    missing = []
    for rec in records:
        fname = rec["pin_file"]
        if not os.path.exists(os.path.join(base, fname)):
            missing.append(fname)

    if missing:
        print(f"ERROR: {len(missing)} PNG(s) missing:")
        for f in missing:
            print(f"  - pins/{slug}/{f}")
        sys.exit(1)

    # Enrich records with image URLs and board ID
    payload_records = []
    for rec in records:
        payload_records.append({
            "notion_page_id": rec["notion_page_id"],
            "title":          rec["title"],
            "description":    rec["description"],
            "affiliate_link": rec["affiliate_link"],
            "publish_at":     rec["publish_at"],
            "image_url":      f"{GITHUB_PAGES}/pins/{slug}/{rec['pin_file']}",
        })

    payload = {
        "product_slug": slug,
        "board_id":     PINTEREST_BOARD,
        "records":      payload_records,
    }

    # ── POST to Make webhook ───────────────────────────────────────────────────
    print("Sending to Make webhook...")
    resp = requests.post(MAKE_WEBHOOK, json=payload, timeout=30)

    if resp.status_code not in (200, 201, 202, 204):
        print(f"ERROR: Make webhook returned {resp.status_code}: {resp.text[:200]}")
        sys.exit(1)

    print(f"  ✓ Accepted by Make (HTTP {resp.status_code})\n")

    # ── Update Notion status ───────────────────────────────────────────────────
    print("Updating Notion status → Scheduled...")
    print(f"\n{'─'*62}")
    print(f"  {'#':<4} {'TITLE':<45} STATUS")
    print(f"{'─'*62}")

    for i, rec in enumerate(records, 1):
        notion_id = rec["notion_page_id"]
        title     = rec["title"][:42] + "..." if len(rec["title"]) > 42 else rec["title"]
        r         = update_notion_status(notion_token, notion_id)
        status    = "✓" if r.status_code in (200, 201) else "✗"
        print(f"  {i:<4} {title:<45} {status}")

    print(f"{'─'*62}\n")

    # ── Move folder ────────────────────────────────────────────────────────────
    scheduled_dir = os.path.join(WORKSPACE, "pins", "scheduled")
    os.makedirs(scheduled_dir, exist_ok=True)
    dest = os.path.join(scheduled_dir, slug)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.move(base, dest)

    print(f"✓ Moved → pins/scheduled/{slug}/")
    print(f"\nAll done. Make is now scheduling 9 pins.")
    print(f"Check Pinterest: https://uk.pinterest.com/scheduled/\n")


if __name__ == "__main__":
    main()
