"""
Picky Products — Pin Image Generator
Generates 9 Pinterest pins (1000×1500px) per product using Python + Pillow.

Templates:
  C (clean) — persona-tinted background, large product image, no pill.
               Replaces the former "For {angle}s" label design.
  B (hook)  — white background, product image, rounded pill with hook text + #ad.

Usage:
    python3 generate_pins.py <product_slug>

Expects:
    pins/<product_slug>/product.jpg   — product image
    pins/<product_slug>/hooks.json    — pin definitions (written by /process-product)

hooks.json format (object form):
    {
      "amazon_image_url": "...",
      "price": "29.99",           # optional — renders £XX on Amazon as pill sub-line
      "pins": [
        {"angle": "Hot Sleeper",     "hook": null},
        {"angle": "Hot Sleeper",     "hook": "Hook text for pin 2"},
        ...
      ]
    }
"""

import sys
import os
import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── Paths ─────────────────────────────────────────────────────────────────────
WORKSPACE = os.path.dirname(os.path.abspath(__file__))

def _find_font(candidates):
    for path in candidates:
        if os.path.exists(path):
            return path
    return None

FONT_BOLD = _find_font([
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
])
FONT_REG = _find_font([
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
])

# ── Canvas ────────────────────────────────────────────────────────────────────
W, H = 1000, 1500

# ── Colours ───────────────────────────────────────────────────────────────────
WHITE     = (255, 255, 255)
PILL_BG   = (237, 237, 237)
PILL_TEXT = (20,  20,  20)

# ── Persona tints — Template C ────────────────────────────────────────────────
PERSONA_TINTS = {
    "Hot Sleeper":       (232, 244, 253),  # #E8F4FD — cool blue
    "Light Sleeper":     (232, 238, 245),  # #E8EEF5 — pale slate
    "Anxious/Insomniac": (240, 238, 248),  # #F0EEF8 — warm lavender
    "Anxious Sleeper":   (240, 238, 248),  # legacy alias
    "Restless Sleeper":  WHITE,             # no tint defined — falls back to white
}

# ── Angle → short slug (for filenames) ───────────────────────────────────────
ANGLE_SLUG = {
    "Hot Sleeper":        "hot",
    "Light Sleeper":      "light",
    "Anxious Sleeper":    "anxious",
    "Anxious/Insomniac":  "anxious",
    "Restless Sleeper":   "restless",
}


# ── Contrast helpers ──────────────────────────────────────────────────────────

def _to_linear(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def relative_luminance(rgb):
    r, g, b = [_to_linear(c) for c in rgb[:3]]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contrast_ratio(fg, bg):
    l1 = relative_luminance(fg)
    l2 = relative_luminance(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)

def check_contrast():
    """Print contrast ratios for all text/background pairs. Warn if below 4.5:1."""
    checks = [("Pill text on pill bg (Template B)", PILL_TEXT, PILL_BG)]
    for angle, tint in PERSONA_TINTS.items():
        if tint != WHITE:
            checks.append((f"Pill text on {angle} tint (Template C)", PILL_TEXT, tint))

    all_pass = True
    for label, fg, bg in checks:
        ratio = contrast_ratio(fg, bg)
        ok = ratio >= 4.5
        if not ok:
            all_pass = False
        print(f"  {'✓' if ok else '⚠'} {label}: {ratio:.1f}:1")

    if not all_pass:
        print("  ⚠ One or more contrast ratios below 4.5:1 — review before publishing.")


# ── Data loading ──────────────────────────────────────────────────────────────

def load_pins(base_dir):
    """
    Load pin definitions from hooks.json.
    Returns (pins, price) where pins is [(filename, hook_or_None, angle), ...]
    and price is a string like "29.99" or None.
    """
    hooks_path = os.path.join(base_dir, "hooks.json")
    if not os.path.exists(hooks_path):
        print(f"ERROR: hooks.json not found at {hooks_path}")
        print("       Run /process-product first — it writes hooks.json.")
        sys.exit(1)

    with open(hooks_path) as f:
        raw = json.load(f)

    price = None
    if isinstance(raw, dict):
        price = raw.get("price")
        data = raw.get("pins", raw)
    else:
        data = raw

    if len(data) != 9:
        print(f"ERROR: hooks.json must contain exactly 9 entries, found {len(data)}")
        sys.exit(1)

    pins = []
    angle_counters = {}

    for i, entry in enumerate(data, start=1):
        angle = entry.get("angle", "")
        hook  = entry.get("hook")

        slug  = ANGLE_SLUG.get(angle, angle.lower().replace(" ", "-"))
        count = angle_counters.get(slug, 0)
        angle_counters[slug] = count + 1

        if hook is None:
            suffix = "clean"
        else:
            suffix = f"hook-{'ab'[count - 1]}" if count > 0 else "hook-a"

        filename = f"pin-{i}-{slug}-{suffix}.png"
        pins.append((filename, hook, angle))

    return pins, price


# ── Drawing helpers ───────────────────────────────────────────────────────────

def _draw_pill_shape(draw, x0, y0, x1, y1, r, fill):
    draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
    draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
    draw.ellipse([x0,      y0,      x0+2*r, y0+2*r], fill=fill)
    draw.ellipse([x1-2*r,  y0,      x1,     y0+2*r], fill=fill)
    draw.ellipse([x0,      y1-2*r,  x0+2*r, y1    ], fill=fill)
    draw.ellipse([x1-2*r,  y1-2*r,  x1,     y1    ], fill=fill)


def draw_pill(draw, cx, cy, text, font, bg=PILL_BG, fg=PILL_TEXT,
              pad_x=60, pad_y=28, radius=None, sub_text=None, sub_font=None):
    """Draw a rounded pill centred at (cx, cy). Returns bounding box (x0, y0, x1, y1)."""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    if sub_text and sub_font:
        sub_bbox = draw.textbbox((0, 0), sub_text, font=sub_font)
        stw = sub_bbox[2] - sub_bbox[0]
        sth = sub_bbox[3] - sub_bbox[1]
        line_gap = 10
        combined_w = max(tw, stw)
        combined_h = th + line_gap + sth

        pw = combined_w + pad_x * 2
        ph = combined_h + pad_y * 2
        r  = radius if radius is not None else ph // 2

        x0, y0 = cx - pw // 2, cy - ph // 2
        x1, y1 = cx + pw // 2, cy + ph // 2
        _draw_pill_shape(draw, x0, y0, x1, y1, r, bg)

        content_top = y0 + pad_y
        draw.text((cx, content_top + th // 2),                  text,     font=font,     fill=fg, anchor="mm")
        draw.text((cx, content_top + th + line_gap + sth // 2), sub_text, font=sub_font, fill=fg, anchor="mm")
    else:
        pw = tw + pad_x * 2
        ph = th + pad_y * 2
        r  = radius if radius is not None else ph // 2

        x0, y0 = cx - pw // 2, cy - ph // 2
        x1, y1 = cx + pw // 2, cy + ph // 2
        _draw_pill_shape(draw, x0, y0, x1, y1, r, bg)
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


def place_product(canvas, product_img, area_top, area_bottom, centre_y=None):
    """Paste product image scaled to fill the area, centred horizontally.

    If centre_y is given, the product's vertical centre is placed at that y
    coordinate (clamped to stay within area bounds).
    """
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

    if centre_y is not None:
        iy = centre_y - ih // 2
        iy = max(area_top, min(iy, area_bottom - ih))
    else:
        iy = area_top + (max_h - ih) // 2

    if img.mode == "RGBA":
        canvas.paste(img, (ix, iy), img)
    else:
        canvas.paste(img, (ix, iy))


def add_ad_label(canvas):
    """Overlay a small '#ad' label at bottom-right at 50% opacity. Returns new canvas."""
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    try:
        ad_font = ImageFont.truetype(FONT_REG, 22)
    except Exception:
        ad_font = ImageFont.load_default()
    od.text((W - 24, H - 24), "#ad", font=ad_font, fill=(20, 20, 20, 128), anchor="rb")
    result = Image.alpha_composite(canvas.convert("RGBA"), overlay)
    return result.convert("RGB")


# ── Templates ─────────────────────────────────────────────────────────────────

def make_template_c(product_img, angle, out_path):
    """Template C: persona-tinted background, full product image, no pill."""
    tint = PERSONA_TINTS.get(angle, WHITE)
    canvas = Image.new("RGB", (W, H), tint)
    place_product(canvas, product_img, 60, H - 80, centre_y=int(H * 0.55))
    canvas = add_ad_label(canvas)
    canvas.save(out_path, "PNG", optimize=True)
    print(f"  ✓ {os.path.basename(out_path)}")


def make_template_b(product_img, hook_text, out_path, price=None):
    """Template B: white background, product image, rounded pill with hook text."""
    canvas = Image.new("RGB", (W, H), WHITE)
    draw   = ImageDraw.Draw(canvas)

    pill_centre_y   = H - 80 - 55
    pill_max_text_w = int(W * 0.85) - 120
    font, _         = fit_text_to_width(hook_text, FONT_BOLD, pill_max_text_w)

    sub_text = f"£{price} on Amazon" if price else None
    sub_font = None
    if sub_text:
        try:
            sub_font = ImageFont.truetype(FONT_REG, 26)
        except Exception:
            sub_font = ImageFont.load_default()

    _, pill_top, _, _ = draw_pill(
        draw, W // 2, pill_centre_y, hook_text, font,
        sub_text=sub_text, sub_font=sub_font,
    )

    place_product(canvas, product_img, 60, pill_top - 40)
    canvas = add_ad_label(canvas)
    canvas.save(out_path, "PNG", optimize=True)
    print(f"  ✓ {os.path.basename(out_path)}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 generate_pins.py <product_slug>")
        sys.exit(1)

    slug = sys.argv[1]
    base = os.path.join(WORKSPACE, "pins", slug)

    product_img_path = os.path.join(base, "product.jpg")
    if not os.path.exists(product_img_path):
        product_img_path = os.path.join(base, "product.png")
    if not os.path.exists(product_img_path):
        print(f"ERROR: Product image not found at {base}/product.jpg")
        sys.exit(1)

    pins, price = load_pins(base)

    print("\nContrast check:")
    check_contrast()

    print(f"\nLoading: {product_img_path}")
    product_img = Image.open(product_img_path).convert("RGBA")

    print(f"\nGenerating 9 pins → {base}")
    for filename, hook, angle in pins:
        out_path = os.path.join(base, filename)
        if hook is None:
            make_template_c(product_img, angle, out_path)
        else:
            make_template_b(product_img, hook, out_path, price=price)

    print(f"\nDone — 9 pins saved.")


if __name__ == "__main__":
    main()
