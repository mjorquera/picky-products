#!/usr/bin/env python3
"""
Picky Products — Pinterest Pin Scheduler
Schedules all 9 pins for a product via the Pinterest API v5.

Usage:
    python3 schedule_pins.py <product-slug>

Example:
    python3 schedule_pins.py silentnight-cool-touch-pillow

What it does:
    1. Reads pins/<product-slug>/schedule_meta.json  (written by Cowork)
    2. Reads pins/<product-slug>/hooks.json          (pin order + angle data)
    3. For each of the 9 pins:
       - Base64-encodes the PNG
       - POSTs to Pinterest API v5 with publish_at timestamp
       - Updates the Notion Distribution DB record → Status: Scheduled
    4. Moves pins/<product-slug>/ → pins/scheduled/<product-slug>/

Prerequisites:
    - Run pinterest_auth.py once to get Pinterest tokens
    - Add NOTION_TOKEN to .env (see CLAUDE.md)
    - Process product in Cowork ('process [product]') → creates schedule_meta.json
    - Generate pins ('generate pins for [product]') → creates PNG files

schedule_meta.json format (written by Cowork):
    {
      "product_slug": "silentnight-cool-touch-pillow",
      "records": [
        {
          "notion_page_id": "...",
          "pin_file":       "pin-1-hot-clean.png",
          "title":          "...",
          "description":    "...",
          "affiliate_link": "https://amazon.co.uk/...",
          "publish_at":     "2026-05-15T20:00:00Z"
        },
        ... (9 total, same order as hooks.json)
      ]
    }
"""

import sys
import os
import json
import base64
import shutil
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests --break-system-packages")
    sys.exit(1)

# ── Paths ──────────────────────────────────────────────────────────────────────
WORKSPACE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH  = os.path.join(WORKSPACE, ".env")

# ── API ────────────────────────────────────────────────────────────────────────
PINTEREST_API = "https://api.pinterest.com/v5"
NOTION_API    = "https://api.notion.com/v1"

# ── Priority time slots (UTC = GMT, UK audience) by weekday (0=Mon…6=Sun) ─────
# Used when publish_at has no time component (date-only string from Notion)
DEFAULT_TIMES = {
    6: "20:00",  # Sunday 8pm   ← highest priority
    0: "21:00",  # Monday 9pm
    1: "20:00",  # Tuesday 8pm
    3: "10:00",  # Thursday 10am
    5: "09:00",  # Saturday 9am
    2: "20:00",  # Wednesday (fallback)
    4: "20:00",  # Friday     (fallback)
}

# ── Angle slug map — must match generate_pins.py ───────────────────────────────
ANGLE_SLUG = {
    "Hot Sleeper":      "hot",
    "Light Sleeper":    "light",
    "Anxious Sleeper":  "anxious",
    "Restless Sleeper": "restless",
}


# ══════════════════════════════════════════════════════════════════════════════
# .env helpers
# ══════════════════════════════════════════════════════════════════════════════

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


def write_env_key(key: str, value: str):
    """Update a single key in .env in-place."""
    lines = []
    found = False
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                if line.strip().startswith(f"{key}="):
                    lines.append(f'{key}="{value}"\n')
                    found = True
                else:
                    lines.append(line)
    if not found:
        lines.append(f'{key}="{value}"\n')
    with open(ENV_PATH, "w") as f:
        f.writelines(lines)


# ══════════════════════════════════════════════════════════════════════════════
# Token management
# ══════════════════════════════════════════════════════════════════════════════

def refresh_token(env: dict) -> str:
    """Exchange refresh token for a new access token. Returns the new token."""
    client_id     = env.get("PINTEREST_CLIENT_ID")
    client_secret = env.get("PINTEREST_CLIENT_SECRET")
    refresh       = env.get("PINTEREST_REFRESH_TOKEN")

    if not (client_id and client_secret and refresh):
        print("  Cannot refresh: missing CLIENT_ID, CLIENT_SECRET, or REFRESH_TOKEN.")
        return env.get("PINTEREST_ACCESS_TOKEN", "")

    resp = requests.post(
        f"{PINTEREST_API}/oauth/token",
        auth=(client_id, client_secret),
        data={"grant_type": "refresh_token", "refresh_token": refresh},
    )

    if resp.status_code != 200:
        print(f"  Token refresh failed ({resp.status_code}): {resp.text}")
        return env.get("PINTEREST_ACCESS_TOKEN", "")

    data = resp.json()
    new_access  = data.get("access_token")
    new_refresh = data.get("refresh_token")

    if new_access:
        write_env_key("PINTEREST_ACCESS_TOKEN", new_access)
        print("  ✓ Access token refreshed and saved")
    if new_refresh:
        write_env_key("PINTEREST_REFRESH_TOKEN", new_refresh)

    return new_access or env.get("PINTEREST_ACCESS_TOKEN", "")


def get_valid_token(env: dict) -> str:
    """Return a valid Pinterest access token, refreshing if expired."""
    token = env.get("PINTEREST_ACCESS_TOKEN")
    if not token:
        print("ERROR: No PINTEREST_ACCESS_TOKEN in .env. Run pinterest_auth.py first.")
        sys.exit(1)

    resp = requests.get(
        f"{PINTEREST_API}/user_account",
        headers={"Authorization": f"Bearer {token}"},
    )

    if resp.status_code == 200:
        username = resp.json().get("username", "?")
        print(f"  ✓ Authenticated as @{username}")
        return token
    elif resp.status_code == 401:
        print("  Access token expired — refreshing...")
        return refresh_token(env)
    else:
        print(f"  WARNING: Token check returned {resp.status_code} — proceeding anyway")
        return token


# ══════════════════════════════════════════════════════════════════════════════
# Date helpers
# ══════════════════════════════════════════════════════════════════════════════

def to_utc_iso(publish_at: str) -> str | None:
    """
    Normalise a date string to Pinterest's expected format: 2026-05-15T20:00:00Z

    Handles:
      - Full ISO datetime:  "2026-05-15T20:00:00Z" or "2026-05-15T20:00:00+00:00"
      - Date only:          "2026-05-15"  → applies priority time by weekday
    """
    if not publish_at:
        return None

    if "T" in publish_at:
        try:
            dt = datetime.fromisoformat(publish_at.replace("Z", "+00:00"))
            dt = dt.astimezone(timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception as e:
            print(f"  WARNING: Could not parse datetime '{publish_at}': {e}")

    # Date-only — apply the priority time slot for that weekday
    try:
        date    = datetime.strptime(publish_at[:10], "%Y-%m-%d")
        weekday = date.weekday()
        time_str = DEFAULT_TIMES.get(weekday, "20:00")
        h, m    = map(int, time_str.split(":"))
        dt      = date.replace(hour=h, minute=m, tzinfo=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception as e:
        print(f"  WARNING: Could not parse date '{publish_at}': {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Pinterest API
# ══════════════════════════════════════════════════════════════════════════════

def create_pin(
    token:       str,
    board_id:    str,
    title:       str,
    description: str,
    link:        str,
    publish_at:  str | None,
    image_path:  str,
) -> requests.Response:
    """POST a single pin to Pinterest API v5."""

    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "board_id": board_id,
        "title":    title[:100],       # Pinterest hard limit
        "description": description[:500],
        "link":     link,
        "media_source": {
            "source_type":  "image_base64",
            "content_type": "image/png",
            "data":         image_b64,
        },
    }

    if publish_at:
        payload["publish_at"] = publish_at

    return requests.post(
        f"{PINTEREST_API}/pins",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        },
        json=payload,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Notion API
# ══════════════════════════════════════════════════════════════════════════════

def update_notion_status(notion_token: str, page_id: str, status: str = "Scheduled"):
    """PATCH a Distribution DB record to set Status."""
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


# ══════════════════════════════════════════════════════════════════════════════
# Load local files
# ══════════════════════════════════════════════════════════════════════════════

def load_hooks(base_dir: str) -> list[dict]:
    """Load hooks.json — returns 9 entries with angle, hook, variant, filename."""
    path = os.path.join(base_dir, "hooks.json")
    if not os.path.exists(path):
        print(f"ERROR: hooks.json not found at {path}")
        sys.exit(1)

    with open(path) as f:
        data = json.load(f)

    if len(data) != 9:
        print(f"ERROR: hooks.json must have 9 entries, found {len(data)}")
        sys.exit(1)

    pins = []
    angle_counters: dict[str, int] = {}

    for i, entry in enumerate(data, start=1):
        angle = entry["angle"]
        hook  = entry.get("hook")
        slug  = ANGLE_SLUG.get(angle, angle.lower().replace(" ", "-"))

        count = angle_counters.get(slug, 0)
        angle_counters[slug] = count + 1

        if hook is None:
            suffix, variant = "clean", "A"
        elif count == 1:
            suffix, variant = "hook-a", "B"
        else:
            suffix, variant = "hook-b", "C"

        pins.append({
            "index":    i,
            "filename": f"pin-{i}-{slug}-{suffix}.png",
            "angle":    angle,
            "hook":     hook,
            "variant":  variant,
        })

    return pins


def load_schedule_meta(base_dir: str) -> dict:
    """Load schedule_meta.json — written by Cowork during 'process [product]'."""
    path = os.path.join(base_dir, "schedule_meta.json")
    if not os.path.exists(path):
        print(f"ERROR: schedule_meta.json not found at {path}")
        print()
        print("  This file is created by Cowork when you run 'process [product]'.")
        print("  It contains Notion IDs, titles, descriptions, affiliate links,")
        print("  and publish_at timestamps for all 9 pins.")
        print()
        print("  See CLAUDE.md → 'Pinterest scheduling' for the expected format.")
        sys.exit(1)

    with open(path) as f:
        meta = json.load(f)

    records = meta.get("records", [])
    if len(records) != 9:
        print(f"ERROR: schedule_meta.json must have 9 records, found {len(records)}")
        sys.exit(1)

    return meta


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 schedule_pins.py <product-slug>")
        print("Example: python3 schedule_pins.py silentnight-cool-touch-pillow")
        sys.exit(1)

    slug = sys.argv[1]
    base = os.path.join(WORKSPACE, "pins", slug)

    if not os.path.isdir(base):
        print(f"ERROR: Folder not found: {base}")
        print(f"       Expected: pins/{slug}/")
        sys.exit(1)

    print(f"\n{'━'*62}")
    print(f"  Picky Products — Pinterest Scheduler")
    print(f"  Product: {slug}")
    print(f"{'━'*62}\n")

    # ── Load config ────────────────────────────────────────────────────────────
    env          = read_env()
    board_id     = env.get("PINTEREST_BOARD_ID")
    notion_token = env.get("NOTION_TOKEN")

    if not board_id:
        print("ERROR: PINTEREST_BOARD_ID not in .env. Run pinterest_auth.py.")
        sys.exit(1)
    if not notion_token:
        print("ERROR: NOTION_TOKEN not in .env.")
        print("  Get one at: https://www.notion.so/my-integrations")
        print("  Then add: NOTION_TOKEN=\"ntn_xxxx...\" to .env")
        print("  Then share your Distribution DB with the integration in Notion.")
        sys.exit(1)

    # ── Auth ───────────────────────────────────────────────────────────────────
    print("Checking Pinterest auth...")
    token = get_valid_token(env)

    # ── Load files ─────────────────────────────────────────────────────────────
    print("\nLoading pin definitions...")
    hooks   = load_hooks(base)
    meta    = load_schedule_meta(base)
    records = meta["records"]

    # ── Validate PNG files exist ───────────────────────────────────────────────
    missing = []
    for pin, rec in zip(hooks, records):
        fname    = rec.get("pin_file") or pin["filename"]
        img_path = os.path.join(base, fname)
        if not os.path.exists(img_path):
            missing.append(fname)

    if missing:
        print(f"\nERROR: {len(missing)} PNG file(s) missing:")
        for f in missing:
            print(f"  - pins/{slug}/{f}")
        print("\nRun: python3 generate_pins.py " + slug)
        sys.exit(1)

    print(f"  ✓ All 9 PNGs present\n")

    # ── Schedule pins ──────────────────────────────────────────────────────────
    COL = f"{'#':<5} {'ANGLE':<20} {'VAR':<4} {'PUBLISH AT (UTC)':<24} STATUS"
    print(COL)
    print("─" * 70)

    results = []

    for pin, record in zip(hooks, records):
        idx          = pin["index"]
        angle        = pin["angle"]
        variant      = pin["variant"]
        fname        = record.get("pin_file") or pin["filename"]
        notion_id    = record.get("notion_page_id", "")
        title        = record.get("title", slug)
        description  = record.get("description", "")
        link         = record.get("affiliate_link", "")
        raw_date     = record.get("publish_at", "")
        img_path     = os.path.join(base, fname)

        publish_at   = to_utc_iso(raw_date)
        pt_display   = publish_at or "IMMEDIATE"

        try:
            resp = create_pin(token, board_id, title, description, link, publish_at, img_path)

            if resp.status_code in (200, 201):
                pin_id = resp.json().get("id", "?")
                print(f"  {idx:<4} {angle:<20} {variant:<4} {pt_display:<24} ✓ {pin_id}")

                # Update Notion status
                if notion_id:
                    update_notion_status(notion_token, notion_id)

                results.append({"pin": pin, "success": True, "pinterest_id": pin_id})

            elif resp.status_code == 429:
                msg = "RATE LIMITED — wait 60s and re-run"
                print(f"  {idx:<4} {angle:<20} {variant:<4} {pt_display:<24} ✗ {msg}")
                results.append({"pin": pin, "success": False, "reason": "rate limited"})

            else:
                try:
                    err_msg = resp.json().get("message", resp.text[:80])
                except Exception:
                    err_msg = resp.text[:80]
                print(f"  {idx:<4} {angle:<20} {variant:<4} {pt_display:<24} ✗ {resp.status_code}: {err_msg}")
                results.append({"pin": pin, "success": False, "reason": f"{resp.status_code}: {err_msg}"})

        except Exception as e:
            print(f"  {idx:<4} {angle:<20} {variant:<4} {pt_display:<24} ✗ ERROR: {e}")
            results.append({"pin": pin, "success": False, "reason": str(e)})

    # ── Summary ────────────────────────────────────────────────────────────────
    success_count = sum(1 for r in results if r["success"])
    print("─" * 70)
    print(f"\n{'✅' if success_count == 9 else '⚠'} {success_count}/9 pins scheduled\n")

    if success_count == 9:
        # Move folder to pins/scheduled/
        scheduled_dir = os.path.join(WORKSPACE, "pins", "scheduled")
        os.makedirs(scheduled_dir, exist_ok=True)
        dest = os.path.join(scheduled_dir, slug)
        if os.path.exists(dest):
            shutil.rmtree(dest)
        shutil.move(base, dest)
        print(f"✓ Moved → pins/scheduled/{slug}/")
        print(f"\nAll done. Check Pinterest: https://uk.pinterest.com/scheduled/")

    else:
        failed = [r for r in results if not r["success"]]
        print("Failed pins:")
        for r in failed:
            p = r["pin"]
            print(f"  pin-{p['index']:02d} ({p['angle']}, Variant {p['variant']}): {r['reason']}")
        print("\nFix the issues above and re-run. Already-scheduled pins won't be duplicated")
        print("(Pinterest will reject duplicate publish_at + content combinations).")
        sys.exit(1)


if __name__ == "__main__":
    main()
