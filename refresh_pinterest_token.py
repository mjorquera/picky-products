#!/usr/bin/env python3
"""
refresh_pinterest_token.py

Uses the stored refresh token to get a new Pinterest access token
and updates .env. No browser required.

Usage:
    python3 refresh_pinterest_token.py
"""

import os
import sys

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests --break-system-packages")
    sys.exit(1)

WORKSPACE  = os.path.dirname(os.path.abspath(__file__))
ENV_PATH   = os.path.join(WORKSPACE, ".env")
TOKEN_URL  = "https://api.pinterest.com/v5/oauth/token"


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


def main():
    env = read_env()

    client_id     = env.get("PINTEREST_CLIENT_ID")
    client_secret = env.get("PINTEREST_CLIENT_SECRET")
    refresh_token = env.get("PINTEREST_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        missing = [k for k, v in {
            "PINTEREST_CLIENT_ID":     client_id,
            "PINTEREST_CLIENT_SECRET": client_secret,
            "PINTEREST_REFRESH_TOKEN": refresh_token,
        }.items() if not v]
        print(f"ERROR: Missing from .env: {', '.join(missing)}")
        print("Run python3 pinterest_auth.py to re-authenticate from scratch.")
        sys.exit(1)

    print("Refreshing Pinterest access token...")

    resp = requests.post(
        TOKEN_URL,
        auth=(client_id, client_secret),
        data={
            "grant_type":    "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=15,
    )

    if resp.status_code != 200:
        print(f"ERROR: Token refresh failed ({resp.status_code}): {resp.text[:300]}")
        print("\nThe refresh token may have expired too. Run python3 pinterest_auth.py")
        print("to do a full re-authentication via browser.")
        sys.exit(1)

    data = resp.json()
    new_access  = data.get("access_token")
    new_refresh = data.get("refresh_token")  # Pinterest may rotate the refresh token

    if not new_access:
        print(f"ERROR: No access_token in response: {data}")
        sys.exit(1)

    updates = {"PINTEREST_ACCESS_TOKEN": new_access}
    if new_refresh:
        updates["PINTEREST_REFRESH_TOKEN"] = new_refresh

    write_env_keys(updates)
    print(f"✅  New access token saved to .env ({new_access[:20]}...)")
    if new_refresh:
        print(f"✅  Refresh token rotated and saved.")
    print("\nRun python3 list_boards.py to verify.")


if __name__ == "__main__":
    main()
