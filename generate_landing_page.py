#!/usr/bin/env python3
"""
generate_landing_page.py <product-slug>

Generates an intermediate landing page between Pinterest pins and Amazon.

What it does:
  1. Reads pins/<slug>/schedule_meta.json and hooks.json
  2. Copies pins/<slug>/product.jpg → docs/products/<slug>/product.jpg
  3. Writes docs/products/<slug>/index.html
  4. Updates affiliate_link in schedule_meta.json to use the landing page URL
     (so publish_due_pins.py posts the landing page URL to Pinterest, not Amazon)

Landing page URL: https://mjorquera.github.io/picky-products/products/<slug>/
Amazon affiliate link is the CTA on the landing page itself.

Usage:
    python3 generate_landing_page.py <product-slug>
"""

import json
import os
import re
import shutil
import sys
from html import escape
from pathlib import Path

GITHUB_PAGES = "https://mjorquera.github.io/picky-products"
PROJECT_ROOT = Path(__file__).parent

ANGLE_COLORS = {
    "Hot Sleeper":        "#E8F4FD",
    "Light Sleeper":      "#E8EEF5",
    "Anxious/Insomniac":  "#F0EEF8",
    "Restless Sleeper":   "#EEF5F0",
}
ANGLE_LABELS = {
    "Hot Sleeper":        "For hot sleepers",
    "Light Sleeper":      "For light sleepers",
    "Anxious/Insomniac":  "For anxious sleepers",
    "Restless Sleeper":   "For restless sleepers",
}


def slug_to_title(slug: str) -> str:
    """Convert 'bambaw-bamboo-fitted-sheet-cooling-bedding' to title case."""
    return " ".join(w.capitalize() for w in slug.replace("-", " ").split())


def derive_angle_from_pin_file(pin_file: str) -> str:
    """Extract angle slug from filename like 'pin-1-hot-clean.png'."""
    m = re.match(r"pin-\d+-(\w+)-", pin_file)
    if not m:
        return ""
    slug = m.group(1)
    return {
        "hot":      "Hot Sleeper",
        "light":    "Light Sleeper",
        "anxious":  "Anxious/Insomniac",
        "restless": "Restless Sleeper",
    }.get(slug, "")


def build_html(
    slug: str,
    product_name: str,
    amazon_url: str,
    price: str | None,
    clean_pins: list[dict],
) -> str:
    """Return the full HTML for the landing page."""

    landing_page_url = f"{GITHUB_PAGES}/products/{slug}/"
    image_url = f"{GITHUB_PAGES}/products/{slug}/product.jpg"

    price_badge = ""
    if price:
        price_badge = f'<span class="price">£{escape(price)}</span>'

    ad_pill = '<span class="ad-pill">#ad</span>'

    # Build angle cards from clean pin variants
    angle_cards = ""
    for rec in clean_pins:
        angle = derive_angle_from_pin_file(rec.get("pin_file", ""))
        color = ANGLE_COLORS.get(angle, "#F5F5F5")
        label = ANGLE_LABELS.get(angle, angle)
        desc = escape(rec.get("description", ""))
        if not desc:
            continue
        angle_cards += f"""
      <div class="angle-card" style="background:{color};">
        <span class="angle-label">{escape(label)}</span>
        <p>{desc}</p>
      </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(product_name)} — Picky Products</title>
  <meta name="description" content="{escape(clean_pins[0].get('description', '') if clean_pins else '')}">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #fafafa;
      color: #1a1a1a;
      line-height: 1.6;
    }}
    header {{
      background: #fff;
      border-bottom: 1px solid #eee;
      padding: 16px 24px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    header a {{ text-decoration: none; color: #1a1a1a; }}
    header .logo {{ font-size: 1rem; font-weight: 700; letter-spacing: -0.02em; }}
    header .divider {{ color: #ccc; }}
    header .crumb {{ font-size: 0.9rem; color: #666; }}
    .hero {{
      max-width: 520px;
      margin: 0 auto;
      padding: 32px 24px 0;
    }}
    .product-image {{
      width: 100%;
      max-height: 340px;
      object-fit: contain;
      border-radius: 12px;
      background: #fff;
      padding: 16px;
      border: 1px solid #eee;
    }}
    .meta {{
      padding: 24px 0 0;
    }}
    .meta-top {{
      display: flex;
      align-items: baseline;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 8px;
    }}
    h1 {{
      font-size: 1.4rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      line-height: 1.3;
    }}
    .price {{
      font-size: 1.1rem;
      font-weight: 600;
      color: #1a6f2e;
      white-space: nowrap;
    }}
    .ad-pill {{
      display: inline-block;
      font-size: 0.7rem;
      color: #999;
      border: 1px solid #ddd;
      border-radius: 3px;
      padding: 1px 5px;
      vertical-align: middle;
      letter-spacing: 0.02em;
    }}
    .cta-wrap {{
      margin: 20px 0;
    }}
    .cta {{
      display: block;
      width: 100%;
      padding: 14px 20px;
      background: #FF9900;
      color: #111;
      text-align: center;
      text-decoration: none;
      font-weight: 700;
      font-size: 1rem;
      border-radius: 8px;
      letter-spacing: -0.01em;
    }}
    .cta:hover {{ background: #e88a00; }}
    .cta-sub {{
      text-align: center;
      font-size: 0.75rem;
      color: #888;
      margin-top: 6px;
    }}
    .angles {{
      max-width: 520px;
      margin: 32px auto 0;
      padding: 0 24px;
    }}
    .angles h2 {{
      font-size: 0.85rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #888;
      margin-bottom: 12px;
    }}
    .angle-card {{
      border-radius: 10px;
      padding: 14px 16px;
      margin-bottom: 10px;
    }}
    .angle-label {{
      display: block;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: #666;
      margin-bottom: 4px;
    }}
    .angle-card p {{
      font-size: 0.88rem;
      color: #333;
      line-height: 1.5;
    }}
    footer {{
      max-width: 520px;
      margin: 48px auto 0;
      padding: 24px 24px 40px;
      font-size: 0.8rem;
      color: #aaa;
      border-top: 1px solid #eee;
    }}
    footer a {{ color: #aaa; }}
    .disclosure {{
      font-size: 0.78rem;
      color: #aaa;
      margin-bottom: 8px;
    }}
  </style>
</head>
<body>
  <header>
    <a href="{GITHUB_PAGES}/" class="logo">Picky Products</a>
    <span class="divider">›</span>
    <span class="crumb">{escape(product_name)}</span>
  </header>

  <div class="hero">
    <img
      src="{image_url}"
      alt="{escape(product_name)}"
      class="product-image"
      width="488" height="340"
    >
    <div class="meta">
      <div class="meta-top">
        <h1>{escape(product_name)}</h1>
        {price_badge}
        {ad_pill}
      </div>
      <div class="cta-wrap">
        <a href="{escape(amazon_url)}" class="cta" rel="nofollow sponsored" target="_blank">
          View on Amazon UK
        </a>
        <p class="cta-sub">Opens Amazon UK in a new tab</p>
      </div>
    </div>
  </div>

  <div class="angles">
    <h2>Who it's for</h2>{angle_cards}
  </div>

  <footer>
    <p class="disclosure">
      This page contains affiliate links to Amazon UK. Picky Products earns a small commission on qualifying purchases at no extra cost to you.
    </p>
    <a href="{GITHUB_PAGES}/privacy.html">Privacy Policy</a>
    &nbsp;·&nbsp; © 2026 Picky Products
  </footer>
</body>
</html>
"""


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 generate_landing_page.py <product-slug>", file=sys.stderr)
        sys.exit(1)

    slug = sys.argv[1].strip("/").strip()
    pin_dir = PROJECT_ROOT / "pins" / slug
    docs_dir = PROJECT_ROOT / "docs" / "products" / slug

    # ── Guards ─────────────────────────────────────────────────────────────
    if not pin_dir.is_dir():
        print(f"❌  pins/{slug}/ not found — run /process-product first.", file=sys.stderr)
        sys.exit(1)

    meta_path = pin_dir / "schedule_meta.json"
    hooks_path = pin_dir / "hooks.json"

    for p, name in [(meta_path, "schedule_meta.json"), (hooks_path, "hooks.json")]:
        if not p.exists():
            print(f"❌  {name} missing in pins/{slug}/", file=sys.stderr)
            sys.exit(1)

    product_jpg = pin_dir / "product.jpg"
    if not product_jpg.exists():
        print(f"❌  product.jpg missing in pins/{slug}/ — run fetch_product_image.py first.", file=sys.stderr)
        sys.exit(1)

    # ── Read inputs ────────────────────────────────────────────────────────
    with meta_path.open() as f:
        meta = json.load(f)
    with hooks_path.open() as f:
        hooks = json.load(f)

    records: list[dict] = meta.get("records", [])
    if not records:
        print(f"❌  No records in schedule_meta.json.", file=sys.stderr)
        sys.exit(1)

    # The original Amazon affiliate link (from any record — they're all the same)
    amazon_url: str = records[0].get("affiliate_link", "")
    if not amazon_url:
        print("❌  affiliate_link missing from schedule_meta.json records.", file=sys.stderr)
        sys.exit(1)

    price: str | None = hooks.get("price") if isinstance(hooks, dict) else None
    product_name = slug_to_title(slug)
    landing_page_url = f"{GITHUB_PAGES}/products/{slug}/"

    # Identify clean (Variant A) pins for angle cards
    clean_pins = [r for r in records if r.get("pin_file", "").endswith("-clean.png")]

    # ── Create output dir ──────────────────────────────────────────────────
    docs_dir.mkdir(parents=True, exist_ok=True)

    # ── Copy product image ─────────────────────────────────────────────────
    dest_jpg = docs_dir / "product.jpg"
    shutil.copy2(product_jpg, dest_jpg)
    print(f"📸  Copied product.jpg → docs/products/{slug}/product.jpg")

    # ── Write HTML ─────────────────────────────────────────────────────────
    html = build_html(slug, product_name, amazon_url, price, clean_pins)
    html_path = docs_dir / "index.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"📄  Written docs/products/{slug}/index.html")

    # ── Update schedule_meta.json: replace affiliate_link with landing page URL
    updated = False
    for rec in records:
        if rec.get("affiliate_link") != landing_page_url:
            rec["affiliate_link"] = landing_page_url
            updated = True

    if updated:
        with meta_path.open("w") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"🔗  Updated affiliate_link → {landing_page_url}")
        print(f"    Amazon link is the CTA inside the landing page.")
    else:
        print(f"⏭  affiliate_link already set to landing page URL — skipping.")

    print(f"\n✅  Landing page ready: {landing_page_url}")
    print(f"    Notion records need updating too — run the /generate-pins skill")
    print(f"    to patch Distribution DB affiliate_link fields.\n")

    # Emit the notion page IDs so the calling skill can update them
    notion_ids = [r["notion_page_id"] for r in records]
    print("NOTION_IDS:" + json.dumps(notion_ids))


if __name__ == "__main__":
    main()
