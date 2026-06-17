#!/usr/bin/env python3
"""
create_angle_boards.py

Creates three angle-specific Pinterest boards and saves their IDs to .env.

Boards created:
  Hot Sleeper — Sleep Accessories
  Light Sleeper — Sleep Accessories
  Anxious/Insomniac — Sleep Accessories

Restless Sleeper pins continue to use the existing catch-all board
(PINTEREST_BOARD_ID).

Usage:
    python3 create_angle_boards.py

After running:
  - .env will have PINTEREST_BOARD_HOT, PINTEREST_BOARD_LIGHT,
    PINTEREST_BOARD_ANXIOUS populated
  - Update the Make Pinterest module to use {{5.board_id}} instead of
    the hardcoded board ID (see instructions printed at the end)
"""

import json
import os
import sys

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests --break-system-packages")
    sys.exit(1)

WORKSPACE   = os.path.dirname(os.path.abspath(__file__))
ENV_PATH    = os.path.join(WORKSPACE, ".env")
BOARDS_URL  = "https://api.pinterest.com/v5/boards"

BOARDS_TO_CREATE = [
    {
        "env_key":    "PINTEREST_BOARD_HOT",
        "name":       "Hot Sleeper — Sleep Accessories",
        "description": "Cooling sleep accessories for hot sleepers in the UK. Breathable pillows, bamboo bedding, and temperature-regulating products.",
    },
    {
        "env_key":    "PINTEREST_BOARD_LIGHT",
        "name":       "Light Sleeper — Sleep Accessories",
        "description": "Sleep accessories for light sleepers in the UK. Sound machines, blackout masks, and comfort products for undisturbed nights.",
    },
    {
        "env_key":    "PINTEREST_BOARD_ANXIOUS",
        "name":       "Anxious Sleeper — Sleep Accessories",
        "description": "Calming sleep accessories for anxious and insomniac sleepers in the UK. Weighted blankets, natural bedding, and wind-down products.",
    },
]


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


def write_env_keys(updates: dict):
    """Append or update specific keys in .env without touching others."""
    lines = []
    existing_keys = set()
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    k = stripped.partition("=")[0].strip()
                    if k in updates:
                        lines.append(f'{k}="{updates[k]}"\n')
                        existing_keys.add(k)
                        continue
                lines.append(line)
    for k, v in updates.items():
        if k not in existing_keys:
            lines.append(f'{k}="{v}"\n')
    with open(ENV_PATH, "w") as f:
        f.writelines(lines)


def create_board(token: str, name: str, description: str) -> str:
    resp = requests.post(
        BOARDS_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        },
        json={"name": name, "description": description, "privacy": "PUBLIC"},
        timeout=15,
    )
    if resp.status_code in (200, 201):
        return resp.json()["id"]
    if resp.status_code == 409:
        # Board already exists — fetch it
        print(f"  ⚠  Board already exists, fetching ID...")
        fetch = requests.get(
            BOARDS_URL,
            headers={"Authorization": f"Bearer {token}"},
            params={"page_size": 50},
            timeout=15,
        )
        if fetch.status_code == 200:
            for b in fetch.json().get("items", []):
                if b["name"] == name:
                    return b["id"]
    print(f"  ✗ Failed ({resp.status_code}): {resp.text[:200]}")
    return ""


def main():
    print("\n=== Picky Products — Create Angle Boards ===\n")

    env = read_env()
    token = env.get("PINTEREST_ACCESS_TOKEN")
    if not token:
        print("ERROR: PINTEREST_ACCESS_TOKEN not in .env — run pinterest_auth.py first.")
        sys.exit(1)

    # Check if already done
    already = [b for b in BOARDS_TO_CREATE if env.get(b["env_key"])]
    if already:
        print(f"Some boards already created:")
        for b in already:
            print(f"  {b['env_key']} = {env[b['env_key']]}")
        print()

    created = {}
    for board in BOARDS_TO_CREATE:
        key = board["env_key"]
        if env.get(key):
            print(f"⏭  {board['name']} — already in .env ({env[key]})")
            created[key] = env[key]
            continue
        print(f"Creating: {board['name']}")
        board_id = create_board(token, board["name"], board["description"])
        if board_id:
            print(f"  ✓ ID: {board_id}")
            created[key] = board_id
        else:
            print(f"  ✗ Failed — add manually to .env as {key}=\"<id>\"")

    if created:
        write_env_keys(created)
        print(f"\n✅ Saved to .env: {', '.join(created.keys())}\n")

    # Print summary
    print("Board IDs:")
    for board in BOARDS_TO_CREATE:
        bid = created.get(board["env_key"], "NOT CREATED")
        print(f"  {board['env_key']:<30} = {bid}")
    catch_all = env.get("PINTEREST_BOARD_ID", "NOT SET")
    print(f"  {'PINTEREST_BOARD_ID':<30} = {catch_all}  (catch-all / Restless Sleeper)")

    print("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MANUAL STEP REQUIRED: Update Make scenario
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

In your Make scenario, edit the Pinterest "Make an API Call" module:

  Change:  "board_id": "1063764443174541558"
  To:      "board_id": "{{5.board_id}}"

The publish_due_pins.py script already passes board_id per record
in the webhook payload. Once Make is updated, each pin will route
to its angle-specific board automatically.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")


if __name__ == "__main__":
    main()
