"""
Picky Products — Pin Image Generator
Generates 9 Pinterest pins (1000×1500px) per product using Python + Pillow.

Style: clean white background, large product image, simple rounded pill at bottom.

Usage:
    python3 generate_pins.py <product_slug>

Example:
    python3 generate_pins.py musicozy-sleep-headphones

Expects:
    pins/<product_slug>/product.jpg   — product image
    pins/<product_slug>/hooks.json    — pin definitions (written by Cowork)

hooks.json format:
    [
      {"angle": "Hot Sleeper",     "hook": null},
      {"angle": "Hot Sleeper",     "hook": "Hook text for pin 2"},
      {"angle": "Hot Sleeper",     "hook": "Hook text for pin 3"},
      {"angle": "Light Sleeper",   "hook": null},
      {"angle": "Light Sleeper",   "hook": "Hook text for pin 5"},
      {"angle": "Light Sleeper",   "hook": "Hook text for pin 6"},
      {"angle": "Anxious Sleeper", "hook": null},
      {"angle": "Anxious Sleeper", "hook": "Hook text for pin 8"},
      {"angle": "Anxious Sleeper", "hook": "Hook text for pin 9"}
    ]

Outputs 9 PNGs to pins/<product_slug>/.
"""

import sys
import os
import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── Paths ─────────────────────────────────────────────────────────────────────
WORKSPACE = os.path.dirname(os.path.abspath(__file__))
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# ── Canvas ────────────────────────────────────────────────────────────────────
W, H = 1000, 1500

# ── Colours ───────────────────────────────────────────────────────────────────
WHITE     = (255, 255, 255)
PILL_BG   = (237, 237, 237)
PILL_TEXT = (20,  20,  20)

# ── Angle → short slug (for filenames) ───────────────────────────────────────
ANGLE_SLUG = {
    "Hot Sleeper":      "hot",
    "Light Sleeper":    "light",
    "Anxious Sleeper":  "anxious",
    "Restless Sleeper": "restless",
}


def load_pins(base_dir):
    """
    Load pin definitions from hooks.json in the product folder.
    Returns a list of (filename, hook_or_None, angle_label) tuples.
    Exits with a clear error if hooks.json is missing or malformed.
    """
    hooks_path = os.path.join(base_dir, "hooks.json")
    if not os.path.exists(hooks_path):
        print(f"ERROR: hooks.json not found at {hooks_path}")
        print("       Create distribution records in Notion first — Cowork writes hooks.json automatically.")
        sys.exit(1)

    with open(hooks_path) as f:
        data = json.load(f)

    if len(data) != 9:
        print(f"ERROR: hooks.json must contain exactly 9 entries, found {len(data)}")
        sys.exit(1)

    pins = []
    angle_counters = {}  # track position within each angle for filename suffix

    for i, entry in enumerate(data, start=1):
        angle = entry.get("angle", "")
        hook  = entry.get("hook")  # None for clean pins

        slug = ANGLE_SLUG.get(angle, angle.lower().replace(" ", "-"))

        # Count how many pins we've seen for this angle so far
        count = angle_counters.get(slug, 0)
        angle_counters[slug] = count + 1

        if hook is None:
            suffix   = "clean"
            pin_type = "clean"
        else:
            suffix   = f"hook-{'ab'[count - 1]}" if count > 0 else "hook-a"
            pin_type = "hook"

        filename = f"pin-{i}-{slug}-{suffix}.png"
        pins.append((filename, hook, angle))

    return pins


def draw_pill(draw, cx, cy, text, font, bg=PILL_BG, fg=PILL_TEXT, pad_x=60, pad_y=28, radius=None):
    """Draw a rounded pill centred at (cx, cy)."""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    pw = tw + pad_x * 2
    ph = th + pad_y * 2
    r  = radius if radius is not None else ph // 2

    x0 = cx - pw // 2
    y0 = cy - ph // 2
    x1 = cx + pw // 2
    y1 = cy + ph // 2

    draw.rectangle([x0 + r, y0, x1 - r, y1], fill=bg)
    draw.rectangle([x0, y0 + r, x1, y1 - r], fill=bg)
    draw.ellipse([x0,      y0,      x0+2*r, y0+2*r], fill=bg)
    draw.ellipse([x1-2*r,  y0,      x1,     y0+2*r], fill=bg)
    draw.ellipse([x0,      y1-2*r,  x0+2*r, y1    ], fill=bg)
    draw.ellipse([x1-2*r,  y1-2*r,  x1,     y1    ], fill=bg)

    draw.text((cx, cy - 2), text, font=font, fill=fg, anchor="mm")

    return x0, y0, x1, y1


def fit_text_to_width(text, font_path, target_width, start_size=52, min_size=28):
    """Return (font, size) that fits text within target_width."""
    size = start_size
    while size >= min_size:
        try:
            f = ImageFont.truetype(font_path, size)
        except Exception:
            f = ImageFont.load_default()
        dummy = Image.new("RGB", (1, 1))
        d = ImageDraw.Draw(dummy)
        bb = d.textbbox((0, 0), text, font=f)
        if bb[2] - bb[0] <= target_width:
            return f, size
        size -= 2
    return ImageFont.truetype(font_path, min_size), min_size


def place_product(canvas, product_img, area_top, area_bottom):
    """Paste product image centred in the vertical area, scaled to fill it."""
    max_w = int(W * 0.88)
    max_h = area_bottom - area_top

    iw, ih = product_img.size
    scale = min(max_w / iw, max_h / ih)
    new_w = int(iw * scale)
    new_h = int(ih * scale)

    img = product_img.resize((new_w, new_h), Image.LANCZOS)
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=140, threshold=3))

    iw, ih = img.size
    ix = (W - iw) // 2
    iy = area_top + (max_h - ih) // 2

    if img.mode == "RGBA":
        canvas.paste(img, (ix, iy), img)
    else:
        canvas.paste(img, (ix, iy))


def make_pin(product_img, pill_text, out_path):
    """Generate one pin."""
    canvas = Image.new("RGB", (W, H), WHITE)
    draw   = ImageDraw.Draw(canvas)

    pill_bottom_margin = 80
    pill_centre_y      = H - pill_bottom_margin - 55

    pill_max_text_w = int(W * 0.85) - 120
    font, _ = fit_text_to_width(pill_text, FONT_BOLD, pill_max_text_w)

    _, pill_top, _, _ = draw_pill(draw, W // 2, pill_centre_y, pill_text, font)

    img_area_top    = 60
    img_area_bottom = pill_top - 40

    place_product(canvas, product_img, img_area_top, img_area_bottom)

    canvas.save(out_path, "PNG", optimize=True)
    print(f"  ✓ {os.path.basename(out_path)}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 generate_pins.py <product_slug>")
        sys.exit(1)

    slug = sys.argv[1]
    base = os.path.join(WORKSPACE, "pins", slug)

    # Load product image
    product_img_path = os.path.join(base, "product.jpg")
    if not os.path.exists(product_img_path):
        product_img_path = os.path.join(base, "product.png")
    if not os.path.exists(product_img_path):
        print(f"ERROR: Product image not found at {base}/product.jpg")
        sys.exit(1)

    # Load pin definitions from hooks.json
    pins = load_pins(base)

    print(f"Loading: {product_img_path}")
    product_img = Image.open(product_img_path).convert("RGBA")

    print(f"\nGenerating 9 pins → {base}")
    for filename, hook, angle in pins:
        pill_text = hook if hook else f"For {angle}s"
        out_path  = os.path.join(base, filename)
        make_pin(product_img, pill_text, out_path)

    print(f"\nDone — 9 pins saved.")


if __name__ == "__main__":
    main()
