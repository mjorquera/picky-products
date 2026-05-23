#!/usr/bin/env python3
"""
fetch_product_image.py <product-slug>

Downloads the product image from Amazon CDN and saves it as
pins/<slug>/product.jpg. Reads the URL from hooks.json.

Skips silently if product.jpg already exists and is ≥500KB.
Exits with a clear error message (no stack trace) on failure.
"""

import json
import os
import re
import sys
from pathlib import Path

# --- constants -----------------------------------------------------------

MIN_FILE_SIZE_BYTES = 500 * 1024   # 500 KB — skip threshold for existing file
MIN_SHORT_EDGE_PX   = 600          # minimum acceptable image dimension
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# Amazon CDN URLs embed resolution/quality params as a dot-separated suffix
# block before the file extension. The format varies by how the URL was
# captured — common patterns seen in the Products DB:
#   ._AC_UL320_.jpg
#   ._AC_SY300_SX300_QL70_ML2_.jpg
#   ._AC_SX300_SY300_QL70_ML2_.jpg
# Rather than enumerate every variant, this regex strips the entire suffix
# block in one pass and replaces it with the highest-res variant.
_AMAZON_SUFFIX_RE = re.compile(r"(\._[A-Z0-9_]+)+\.jpg$", re.IGNORECASE)


def upgrade_url(url: str) -> str:
    """Strip any Amazon CDN resolution suffix and request the full-res image."""
    upgraded = _AMAZON_SUFFIX_RE.sub("._AC_SL1500_.jpg", url)
    if upgraded == url:
        print("⚠  No Amazon resolution suffix detected in URL — using as-is.")
    return upgraded


def err(msg: str) -> None:
    print(f"\n❌  {msg}", file=sys.stderr)
    print(
        "    Fallback: drop product.jpg manually into "
        f"pins/<slug>/ and re-run /generate-pins.",
        file=sys.stderr,
    )
    sys.exit(1)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 fetch_product_image.py <product-slug>", file=sys.stderr)
        sys.exit(1)

    slug = sys.argv[1].strip("/").strip()
    project_root = Path(__file__).parent
    pin_dir = project_root / "pins" / slug
    out_path = pin_dir / "product.jpg"
    hooks_path = pin_dir / "hooks.json"

    # --- guard: folder must exist ----------------------------------------
    if not pin_dir.is_dir():
        err(f"Folder not found: pins/{slug}/\n    Run /process-product first.")

    # --- guard: skip if product.jpg already present and large enough ------
    if out_path.exists():
        size = out_path.stat().st_size
        if size >= MIN_FILE_SIZE_BYTES:
            print(f"⏭  product.jpg already exists ({size // 1024} KB) — skipping.")
            sys.exit(0)
        else:
            print(
                f"⚠  product.jpg exists but is only {size // 1024} KB "
                "(below 500 KB threshold) — re-downloading."
            )

    # --- read URL from hooks.json ----------------------------------------
    if not hooks_path.exists():
        err(f"hooks.json not found in pins/{slug}/\n    Run /process-product first.")

    with hooks_path.open() as f:
        hooks = json.load(f)

    # hooks.json is a list; amazon_image_url is a top-level key in new format
    # Support both list (legacy) and dict (new format with amazon_image_url)
    amazon_url = None
    if isinstance(hooks, dict):
        amazon_url = hooks.get("amazon_image_url")
    elif isinstance(hooks, list):
        # Legacy format — no image URL available
        err(
            "hooks.json uses the legacy list format and does not contain "
            "amazon_image_url.\n"
            "    This product was processed before auto-download was added.\n"
            "    Drop product.jpg manually."
        )

    if not amazon_url:
        err(
            "amazon_image_url is missing or empty in hooks.json.\n"
            "    Check the Products DB 'Amazon Main Image URL' field."
        )

    full_res_url = upgrade_url(amazon_url)
    print(f"📥  Fetching image from Amazon CDN …")
    print(f"    URL: {full_res_url}")

    # --- download --------------------------------------------------------
    try:
        import urllib.request

        req = urllib.request.Request(full_res_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            if status != 200:
                err(
                    f"Amazon CDN returned HTTP {status}.\n"
                    "    The URL may have expired or the product was removed."
                )
            image_bytes = resp.read()
    except Exception as exc:
        err(f"Download failed: {exc}")

    # --- validate: file size ---------------------------------------------
    if len(image_bytes) < 10 * 1024:
        err(
            f"Downloaded file is only {len(image_bytes)} bytes — "
            "likely not a valid image.\n"
            "    Amazon CDN may have returned an error page."
        )

    # --- validate: minimum image dimensions ------------------------------
    try:
        import io
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        w, h = img.size
        short_edge = min(w, h)
        if short_edge < MIN_SHORT_EDGE_PX:
            err(
                f"Image is {w}×{h}px — short edge {short_edge}px is below "
                f"the {MIN_SHORT_EDGE_PX}px minimum.\n"
                "    Drop a higher-resolution image manually."
            )
        print(f"✅  Image OK — {w}×{h}px ({len(image_bytes) // 1024} KB)")
    except ImportError:
        # Pillow not available — skip dimension check, warn user
        print(
            "⚠  Pillow not installed — skipping dimension check.\n"
            "   Install with: pip3 install Pillow --break-system-packages"
        )

    # --- save ------------------------------------------------------------
    out_path.write_bytes(image_bytes)
    print(f"💾  Saved to pins/{slug}/product.jpg")


if __name__ == "__main__":
    main()
