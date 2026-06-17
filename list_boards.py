#!/usr/bin/env python3
"""
list_boards.py

Lists all Pinterest boards with their IDs.
Use this after creating angle boards on pinterest.com to get the IDs
needed for .env.

Usage:
    python3 list_boards.py
"""

import os
import sys

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests --break-system-packages")
    sys.exit(1)

WORKSPACE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH  = os.path.join(WORKSPACE, ".env")


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


def main():
    env = read_env()
    token = env.get("PINTEREST_ACCESS_TOKEN")
    if not token:
        print("ERROR: PINTEREST_ACCESS_TOKEN not in .env")
        sys.exit(1)

    resp = requests.get(
        "https://api.pinterest.com/v5/boards",
        headers={"Authorization": f"Bearer {token}"},
        params={"page_size": 50},
        timeout=15,
    )

    if resp.status_code != 200:
        print(f"ERROR: Pinterest API returned {resp.status_code}: {resp.text[:200]}")
        sys.exit(1)

    boards = resp.json().get("items", [])
    if not boards:
        print("No boards found.")
        return

    print(f"\n{'NAME':<55} ID")
    print("─" * 75)
    for b in boards:
        print(f"{b['name']:<55} {b['id']}")

    print(f"\nAdd the IDs for your angle boards to .env:")
    print("  PINTEREST_BOARD_HOT=\"<id>\"")
    print("  PINTEREST_BOARD_LIGHT=\"<id>\"")
    print("  PINTEREST_BOARD_ANXIOUS=\"<id>\"")
    print("  PINTEREST_BOARD_RESTLESS=\"<id>\"")


if __name__ == "__main__":
    main()
