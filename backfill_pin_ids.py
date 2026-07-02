#!/usr/bin/env python3
"""
Picky Products — Backfill Pinterest Pin IDs
Fetches all pins from the angle-specific boards, matches them to Published
Notion Distribution DB records that have no Pin ID, and writes the IDs back.

Only covers the angle boards (Hot, Light, Anxious, Restless) — not the
catch-all board. Duplicate pins with the same title are flagged and skipped.

Usage:
    python3 backfill_pin_ids.py [--dry-run]
"""

import sys
import os

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

ANGLE_BOARDS = {
    "Hot":     "PINTEREST_BOARD_HOT",
    "Light":   "PINTEREST_BOARD_LIGHT",
    "Anxious": "PINTEREST_BOARD_ANXIOUS",
    "Restless":"PINTEREST_BOARD_RESTLESS",
}


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


def normalise(text: str) -> str:
    return " ".join(text.lower().split())


def fetch_board_pins(board_id: str, access_token: str) -> list:
    """Fetch all pins from a board, handling pagination."""
    pins = []
    bookmark = None
    while True:
        params = {"page_size": 100}
        if bookmark:
            params["bookmark"] = bookmark
        resp = requests.get(
            f"{PINTEREST_API}/boards/{board_id}/pins",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
            timeout=20,
        )
        if resp.status_code == 401:
            print("  ✗ 401 Unauthorised — run refresh_pinterest_token.py and retry")
            return []
        resp.raise_for_status()
        data = resp.json()
        pins.extend(data.get("items", []))
        bookmark = data.get("bookmark")
        if not bookmark:
            break
    return pins


def notion_query_published_no_pin_id(token: str) -> list:
    """Return all Published Distribution DB records with no Pinterest Pin ID."""
    url = f"{NOTION_API}/databases/{DISTRIBUTION_DB}/query"
    headers = {
        "Authorization":  f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type":   "application/json",
    }
    payload = {
        "filter": {
            "and": [
                {"property": "Status",           "select":    {"equals":    "Published"}},
                {"property": "Pinterest Pin ID", "rich_text": {"is_empty":  True}},
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


def notion_set_pin_id(token: str, page_id: str, pin_id: str) -> bool:
    resp = requests.patch(
        f"{NOTION_API}/pages/{page_id}",
        headers={
            "Authorization":  f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type":   "application/json",
        },
        json={"properties": {"Pinterest Pin ID": {"rich_text": [{"type": "text", "text": {"content": pin_id}}]}}},
    )
    return resp.status_code in (200, 201)


def extract_title(page: dict) -> str:
    title_list = page.get("properties", {}).get("Pin Title", {}).get("title", [])
    return title_list[0].get("plain_text", "") if title_list else ""


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    dry_run = "--dry-run" in sys.argv

    print(f"\n{'━'*62}")
    print(f"  Picky Products — Backfill Pinterest Pin IDs")
    print(f"{'[DRY RUN] ' if dry_run else ''}  Angle boards only")
    print(f"{'━'*62}\n")

    env = read_env()
    notion_token  = env.get("NOTION_TOKEN")
    access_token  = env.get("PINTEREST_ACCESS_TOKEN")

    if not notion_token:
        print("ERROR: NOTION_TOKEN not in .env"); sys.exit(1)
    if not access_token:
        print("ERROR: PINTEREST_ACCESS_TOKEN not in .env"); sys.exit(1)

    # ── Step 1: collect all pins from angle boards ─────────────────────────────
    print("Fetching pins from angle boards...")
    # title_key → list of (pin_id, board_name, description, created_at)
    pinterest_pins = {}
    duplicates = []

    for board_name, env_key in ANGLE_BOARDS.items():
        board_id = env.get(env_key)
        if not board_id:
            print(f"  ⚠  {board_name}: no board ID in .env ({env_key}) — skipping")
            continue
        pins = fetch_board_pins(board_id, access_token)
        print(f"  {board_name}: {len(pins)} pin(s)")
        for pin in pins:
            pin_id    = pin["id"]
            title     = (pin.get("title") or "").strip()
            desc      = (pin.get("description") or "").strip()
            created   = pin.get("created_at", "")
            key       = normalise(title)
            entry     = (pin_id, board_name, title, desc, created)
            if key in pinterest_pins:
                duplicates.append((board_name, pin_id, title))
                duplicates.append((pinterest_pins[key][1], pinterest_pins[key][0], pinterest_pins[key][2]))
            else:
                pinterest_pins[key] = entry

    print(f"\n  {len(pinterest_pins)} unique title(s) across angle boards")

    if duplicates:
        seen = set()
        print(f"\n⚠️  DUPLICATE PINS DETECTED (same title, same board):")
        for board, pid, title in duplicates:
            entry = f"{pid} — {title[:55]}"
            if entry not in seen:
                print(f"  [{board}] {entry}")
                seen.add(entry)
        print()

    # ── Step 2: query Notion for Published records without a Pin ID ────────────
    print("Querying Notion for Published records with no Pin ID...")
    try:
        notion_pages = notion_query_published_no_pin_id(notion_token)
    except Exception as e:
        print(f"ERROR: Notion query failed — {e}"); sys.exit(1)

    print(f"  {len(notion_pages)} record(s) found\n")

    if not notion_pages:
        print("Nothing to backfill — all Published records already have Pin IDs.\n")
        return

    # ── Step 3: match and update ───────────────────────────────────────────────
    matched = unmatched = errors = 0

    for page in notion_pages:
        page_id = page["id"]
        title   = extract_title(page)
        key     = normalise(title)

        if key not in pinterest_pins:
            print(f"  — no match: {title[:60]}")
            unmatched += 1
            continue

        pin_id, board_name, _, _, created = pinterest_pins[key]
        print(f"  ✓ [{board_name}] {title[:50]}")
        print(f"    Pin {pin_id}  created {created[:10]}")

        if dry_run:
            matched += 1
            continue

        ok = notion_set_pin_id(notion_token, page_id, pin_id)
        if ok:
            matched += 1
        else:
            print(f"    ✗ Notion update failed")
            errors += 1

    print(f"\n{'━'*62}")
    print(f"  Done — {matched} updated, {unmatched} unmatched, {errors} errors")
    if dry_run:
        print(f"  (dry run — no changes written)")
    print(f"{'━'*62}\n")

    if unmatched:
        print("Unmatched records are pins published to the catch-all board before")
        print("board routing was set up — no action needed for those.\n")


if __name__ == "__main__":
    main()
