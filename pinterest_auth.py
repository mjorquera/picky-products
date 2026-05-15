#!/usr/bin/env python3
"""
Picky Products — Pinterest OAuth Setup
One-time run to authenticate and save API tokens.

Usage:
    python3 pinterest_auth.py

What it does:
    1. Opens your browser to Pinterest's OAuth page
    2. Captures the auth code via a local callback server
    3. Exchanges the code for access + refresh tokens
    4. Lists your boards so you can pick the right board ID
    5. Saves everything to .env

Prerequisites:
    1. Create a Pinterest app at https://developers.pinterest.com/apps/
    2. Set redirect URI to: http://localhost:8080/callback
    3. Request scopes: pins:read, pins:write, boards:read, boards:write
    4. Have your App ID and App Secret ready
"""

import sys
import os
import json
import webbrowser
import urllib.parse
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests --break-system-packages")
    sys.exit(1)

# ── Config ─────────────────────────────────────────────────────────────────────
REDIRECT_URI  = "http://localhost:8080/callback"
AUTH_URL      = "https://www.pinterest.com/oauth/"
TOKEN_URL     = "https://api.pinterest.com/v5/oauth/token"
BOARDS_URL    = "https://api.pinterest.com/v5/boards"
SCOPE         = "pins:read,pins:write,boards:read,boards:write"
CALLBACK_PORT = 8080

WORKSPACE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH  = os.path.join(WORKSPACE, ".env")

# ── Shared state for callback ───────────────────────────────────────────────────
_auth_code  = None
_auth_error = None


class CallbackHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler to capture the OAuth callback."""

    def do_GET(self):
        global _auth_code, _auth_error
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            _auth_code = params["code"][0]
            body = b"<h2 style='font-family:sans-serif'>Auth successful! You can close this tab.</h2>"
        elif "error" in params:
            _auth_error = params.get("error_description", ["unknown error"])[0]
            body = f"<h2 style='font-family:sans-serif'>Auth failed: {_auth_error}</h2>".encode()
        else:
            body = b"<h2 style='font-family:sans-serif'>Unexpected response.</h2>"

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # suppress server noise


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


def write_env(updates: dict):
    """Merge updates into .env, preserving existing keys."""
    env = read_env()
    env.update(updates)
    lines = [f'{k}="{v}"\n' for k, v in env.items()]
    with open(ENV_PATH, "w") as f:
        f.writelines(lines)
    print(f"  ✓ Saved to {ENV_PATH}")


# ── OAuth flow ─────────────────────────────────────────────────────────────────

def wait_for_code(timeout: int = 120) -> str:
    """Block until the callback arrives or timeout (seconds)."""
    elapsed = 0
    while _auth_code is None and _auth_error is None and elapsed < timeout:
        time.sleep(0.5)
        elapsed += 0.5

    if _auth_error:
        print(f"ERROR: Pinterest returned an error: {_auth_error}")
        sys.exit(1)
    if _auth_code is None:
        print("ERROR: Timed out waiting for Pinterest callback (120s).")
        sys.exit(1)

    return _auth_code


def exchange_code(client_id: str, client_secret: str, code: str) -> dict:
    resp = requests.post(
        TOKEN_URL,
        auth=(client_id, client_secret),
        data={
            "grant_type":   "authorization_code",
            "code":         code,
            "redirect_uri": REDIRECT_URI,
        },
    )
    if resp.status_code != 200:
        print(f"ERROR: Token exchange failed ({resp.status_code}): {resp.text}")
        sys.exit(1)
    return resp.json()


def fetch_boards(access_token: str) -> list:
    resp = requests.get(
        BOARDS_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        params={"page_size": 50},
    )
    if resp.status_code != 200:
        print(f"WARNING: Could not fetch boards ({resp.status_code}): {resp.text}")
        return []
    return resp.json().get("items", [])


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=== Picky Products — Pinterest OAuth Setup ===\n")
    print("Before you start, make sure you have:")
    print("  1. A Pinterest app at https://developers.pinterest.com/apps/")
    print(f"  2. Redirect URI set to: {REDIRECT_URI}")
    print("  3. Requested scopes: pins:read, pins:write, boards:read, boards:write\n")

    env = read_env()

    # Check if already set up
    if env.get("PINTEREST_ACCESS_TOKEN") and env.get("PINTEREST_BOARD_ID"):
        print("Tokens already in .env.")
        print("To re-auth: delete PINTEREST_ACCESS_TOKEN from .env and re-run.\n")
        choice = input("Re-run auth anyway? [y/N] ").strip().lower()
        if choice != "y":
            print("Exiting. No changes made.")
            sys.exit(0)

    # Get client credentials
    client_id = env.get("PINTEREST_CLIENT_ID")
    if not client_id:
        client_id = input("Pinterest App ID (Client ID): ").strip()
    else:
        print(f"Using PINTEREST_CLIENT_ID from .env: {client_id[:8]}...")

    client_secret = env.get("PINTEREST_CLIENT_SECRET")
    if not client_secret:
        client_secret = input("Pinterest App Secret: ").strip()
    else:
        print("Using PINTEREST_CLIENT_SECRET from .env.")

    if not client_id or not client_secret:
        print("ERROR: Client ID and Secret are required.")
        sys.exit(1)

    # Build the auth URL
    auth_params = urllib.parse.urlencode({
        "client_id":     client_id,
        "redirect_uri":  REDIRECT_URI,
        "response_type": "code",
        "scope":         SCOPE,
    })
    auth_url = f"{AUTH_URL}?{auth_params}"

    # Start local callback server
    server = HTTPServer(("localhost", CALLBACK_PORT), CallbackHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    print(f"\nOpening browser for Pinterest auth...")
    print(f"If it doesn't open: {auth_url}\n")
    webbrowser.open(auth_url)

    # Wait for callback
    print("Waiting for auth callback (approve in browser)...")
    code = wait_for_code(timeout=120)
    server.shutdown()
    print(f"  ✓ Got auth code\n")

    # Exchange code for tokens
    print("Exchanging code for tokens...")
    tokens = exchange_code(client_id, client_secret, code)

    access_token  = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token", "")

    if not access_token:
        print(f"ERROR: No access_token in response: {tokens}")
        sys.exit(1)

    print(f"  ✓ Access token:  {access_token[:20]}...")
    print(f"  ✓ Refresh token: {str(refresh_token)[:20]}..." if refresh_token else "  ⚠ No refresh token returned")

    # Fetch boards
    print("\nFetching your Pinterest boards...")
    boards = fetch_boards(access_token)

    board_id = ""
    if boards:
        print("\nYour boards:")
        for i, b in enumerate(boards, 1):
            print(f"  {i:2}. {b['name']:<50}  id: {b['id']}")

        print("\nEnter the number for 'UK Comfort Products for Sleep': ", end="")
        choice = input().strip()
        try:
            board = boards[int(choice) - 1]
            board_id = board["id"]
            print(f"  ✓ Board: {board['name']} ({board_id})")
        except (ValueError, IndexError):
            print("Invalid selection.")
            board_id = input("Enter board ID manually: ").strip()
    else:
        print("No boards found (or fetch failed).")
        board_id = input("Enter PINTEREST_BOARD_ID manually: ").strip()

    # Save everything to .env
    print("\nSaving to .env...")
    write_env({
        "PINTEREST_CLIENT_ID":     client_id,
        "PINTEREST_CLIENT_SECRET": client_secret,
        "PINTEREST_ACCESS_TOKEN":  access_token,
        "PINTEREST_REFRESH_TOKEN": refresh_token,
        "PINTEREST_BOARD_ID":      board_id,
    })

    print("\n✅ Done. Next steps:")
    print("  1. Add NOTION_TOKEN to .env (see CLAUDE.md for how to get it)")
    print("  2. Process a product in Cowork — it will write schedule_meta.json")
    print("  3. Generate pins: python3 generate_pins.py <product-slug>")
    print("  4. Schedule:      python3 schedule_pins.py <product-slug>")


if __name__ == "__main__":
    main()
