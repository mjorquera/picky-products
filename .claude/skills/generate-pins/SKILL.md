---
name: generate-pins
description: |
  Generate Pinterest pin images for a Picky Products item, copy them to the
  GitHub Pages folder, update Notion Distribution status to Image Created,
  update Products DB Status to Scheduled, then commit and push so
  images are live for the daily publisher. Use after /process-product and once
  product.jpg is in the pins folder.
license: MIT
compatibility: claude-code
allowed-tools:
  - Read
  - Bash
  - mcp__notion__API-patch-page
---

# generate-pins

Generate pin images for a product, push them to GitHub Pages, and update Notion.

## Invocation

```
/generate-pins <product name or slug>
```

Accepts either the full product name ("Slumberdown British Wool Pillow") or the slug directly ("slumberdown-british-wool-pillow").

---

## Step 1 — Derive product slug

Derive the slug from the product name the same way `/process-product` does:
- Lowercase
- Spaces → hyphens
- Remove characters that aren't letters, numbers, or hyphens

Example: "SKYNY Cooling Side Sleeper Pillow" → `skyny-cooling-side-sleeper-pillow`

---

## Step 2 — Check prerequisites

Verify all three files exist before proceeding:
- `pins/<product-slug>/product.jpg`
- `pins/<product-slug>/hooks.json`
- `pins/<product-slug>/schedule_meta.json`

If any are missing, stop and report which file is absent.

---

## Step 3 — Generate pin images

From the project root, run:

```bash
python3 generate_pins.py <product-slug>
```

If the script exits with an error, stop and report the error output.

---

## Step 4 — Copy images to GitHub Pages folder

`mkdir -p` ensures the directory exists before copying — run both commands together.

```bash
mkdir -p docs/pins/<product-slug>
cp pins/<product-slug>/pin-*.png docs/pins/<product-slug>/
```

---

## Step 4.5 — Generate product landing page

Run the landing page generator. This creates `docs/products/<product-slug>/index.html`, copies `product.jpg` into the docs folder, and updates `schedule_meta.json` so every `affiliate_link` points to the GitHub Pages landing page instead of Amazon directly.

```bash
python3 generate_landing_page.py <product-slug>
```

If the script exits with an error, stop and report the error. The landing page is required — it removes the direct-affiliate-link spam signal that suppresses Pinterest distribution.

**Why this matters:** Pinterest suppresses accounts that link pins directly to Amazon affiliate URLs. The landing page is the intermediary that prevents this. The Amazon link becomes the CTA inside the landing page.

---

## Step 5 — Update Notion status

Read `pins/<product-slug>/schedule_meta.json` to get all 9 `notion_page_id` values and the `product_page_id`.

Update all 9 Distribution DB records in parallel using `mcp__notion__API-patch-page`:

```json
{"Status": {"select": {"name": "Image Created"}}}
```

Then update the Products DB record using the `product_page_id`:

```json
{"Status": {"select": {"name": "Scheduled"}}}
```

---

## Step 6 — Commit and push

Stage and commit both the pin images and the landing page together:

```bash
git add docs/pins/<product-slug>/ docs/products/<product-slug>/
git commit -m "Add <product-slug> pin images and landing page"
git push
```

**Note:** `git push` requires network access and git credentials. In sandboxed environments (e.g. Cowork), the push will fail with "No such device or address". If that happens, tell the user to run `git push` manually from their terminal. The commit will already be staged correctly. Git identity (`user.email`, `user.name`) may also need to be set for the commit step — use `git config user.email` / `git config user.name` if the commit fails with "Author identity unknown". If a stale lock file is present (from a prior crashed process), the sandbox cannot remove it — tell the user to remove it manually. Common lock files: `.git/index.lock`, `.git/HEAD.lock`. Run `rm .git/index.lock` or `rm .git/HEAD.lock` as appropriate before committing.

---

## Done

Report:
- 9 images generated and pushed to GitHub Pages
- Landing page live at: `https://mjorquera.github.io/picky-products/products/<product-slug>/`
- Distribution DB records → Image Created; Products DB → Scheduled
- `schedule_meta.json` affiliate_link updated to landing page URL (Amazon link is the CTA inside the page)

The daily publisher will pick up pins automatically from their scheduled `publish_at` times.
