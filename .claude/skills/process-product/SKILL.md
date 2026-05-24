---
name: process-product
description: |
  Create Pinterest pin distribution records for a Picky Products item. Looks up
  the product in Notion, writes copy for 9 pins (3 angles × 3 variants), creates
  Distribution DB records, asks for a start date, writes hooks.json and
  schedule_meta.json with 1 pin/day scheduling, and auto-downloads the product
  image from Amazon CDN. Use when processing a new product for Pinterest distribution.
license: MIT
compatibility: claude-code
allowed-tools:
  - Read
  - Write
  - Bash
  - Skill
  - AskUserQuestion
  - mcp__notion__API-query-data-source
  - mcp__notion__API-post-page
  - mcp__notion__API-patch-page
---

# process-product

Process a Picky Products item end-to-end: generate copy, create Notion distribution records, write `hooks.json`, auto-download the product image, ask for a start date, write `schedule_meta.json` with 1 pin/day scheduling, then automatically run `/generate-pins` if the image was downloaded successfully.

## Invocation

```
/process-product <product name>
```

Product name should match (or closely match) the `Product Name` field in the Notion Products DB.

---

## Step 1 — Derive product slug and set up folder

Derive a slug from the product name:
- Lowercase
- Replace spaces with hyphens
- Remove any characters that aren't letters, numbers, or hyphens
- Example: "SKYNY Cooling Side Sleeper Pillow" → `skyny-cooling-side-sleeper-pillow`

Create the folder `pins/<product-slug>/` in the project root if it doesn't already exist.

---

## Step 2 — Look up product in Notion

Query the Products DB using `mcp__notion__API-query-data-source`:
- `data_source_id`: `a2c18096-68b1-82cf-87d5-075ab33cfb3c`
- Filter: `{"property": "Product Name", "title": {"contains": "<product name>"}}`

Extract from the result:
- `id` — the Notion page ID for the Product record
- `properties.Affiliate Link.url` — the affiliate link
- `properties["Amazon Main Image URL"].url` — the Amazon CDN image URL (may be null — handle gracefully)

**Affiliate link validation:** the correct Amazon Associates tag is `pickyproducts-21`. If the extracted URL contains `pickyprod-21` (no 's'), it is wrong — stop and report the mismatch before creating any Distribution records. If the link is an `amzn.to` short URL, accept it as-is (these resolve correctly).

If no result is found, stop and report: "Product not found in Notion — check the Products DB."

---

## Step 3 — Choose 3 angles

Choose 3 personas that genuinely fit the product. Base the choice on what the product actually does.

Valid angles:
- **Hot Sleeper** — use for cooling, breathable, temperature-regulating products
- **Light Sleeper** — use for most sleep products (near-universal fit)
- **Anxious/Insomniac** — use for weighted, calming, or wind-down products
- **Restless Sleeper** — use for support, movement, or position-related products

Pick the 3 that fit most honestly. Do not force a persona that doesn't fit the product.

Note: "Restless Sleeper" is a valid angle label for copy and `hooks.json` but is **not a valid select option** in the Notion Distribution DB `Angle` field. When writing Notion records for the Restless Sleeper angle, **omit the `Angle` field entirely**.

---

## Step 4 — Write copy for all 9 pins

Generate title, description, and hook for each of the 9 pins (3 angles × 3 pins per angle).

**Pin structure per angle:**
- Pin 1: hook = null (Template A — clean, no hook text)
- Pin 2: hook = variant A (a punchy question or statement)
- Pin 3: hook = variant B (a different hook angle)

**Copy rules — titles:**
- Max 100 characters
- First 40 characters must lead with a specific outcome or benefit
- Never append "UK" to a title
- No double dashes (`--`) — use a colon or reword
- No hype: game-changer, life-changing, revolutionary, must-have, ultimate, perfect, amazing
- No overclaiming health or sleep outcomes
- British spelling throughout (prioritise, organise, recognise, etc.)

**Copy rules — descriptions:**
- 150–250 characters
- Natural language, conversational tone
- Weave in relevant keywords naturally — do not stuff or label them
- Same tone/hype rules as titles

**High-value keywords to use where relevant:**
`"cooling pillow uk"`, `"sleep accessories uk"`, `"weighted blanket uk"`, `"best sleep products uk"`, `"light sleeper tips"`, `"how to sleep better uk"`, `"anxiety blanket uk"`

**Hook text rules:**
- Short — 3 to 6 words
- Question or statement format
- Must match exactly what gets written to the Notion Distribution DB `Hook` field

---

## Step 5 — Create 9 Notion Distribution DB records

Create all 9 records in parallel using `mcp__notion__API-post-page`.

**Parent:**
```json
{"type": "database_id", "database_id": "c7718096-68b1-83ea-8ab2-01b6e3a2b2fe"}
```

**Field mapping per record:**

| SKILL field | Notion property | Type |
|---|---|---|
| Pin title | `Pin Title` | title |
| Description | `Pin Description` | rich_text |
| Angle label | `Angle` | select — omit for Restless Sleeper |
| Variant | `Variant` | select: "A", "B", or "C" |
| Hook text | `Hook` | rich_text — only set for B and C variants |
| Product page ID | `Product` | relation: `[{"id": "<product-page-id>"}]` |
| — | `Status` | select: "Candidate" |
| — | `Channel` | select: "Pinterest" |

Variant map: Pin 1 of each angle → "A", Pin 2 → "B", Pin 3 → "C"

Valid `Angle` select values: `"Hot Sleeper"`, `"Light Sleeper"`, `"Anxious/Insomniac"`. Do not set `Angle` for Restless Sleeper pins.

**After creating all 9 records**, capture each returned `id` — these are the Notion page IDs needed for `schedule_meta.json`.

---

## Step 6 — Write hooks.json

Write to `pins/<product-slug>/hooks.json`.

**Format:** a JSON object with `amazon_image_url` at the top level and a `pins` array of 9 objects in pin order (angle 1 × 3, angle 2 × 3, angle 3 × 3).

```json
{
  "amazon_image_url": "<Amazon Main Image URL from Step 2, or null if not available>",
  "pins": [
    {"angle": "Angle 1 Label", "hook": null},
    {"angle": "Angle 1 Label", "hook": "Hook text for pin 2"},
    {"angle": "Angle 1 Label", "hook": "Hook text for pin 3"},
    {"angle": "Angle 2 Label", "hook": null},
    {"angle": "Angle 2 Label", "hook": "Hook text for pin 5"},
    {"angle": "Angle 2 Label", "hook": "Hook text for pin 6"},
    {"angle": "Angle 3 Label", "hook": null},
    {"angle": "Angle 3 Label", "hook": "Hook text for pin 8"},
    {"angle": "Angle 3 Label", "hook": "Hook text for pin 9"}
  ]
}
```

Hook text must match exactly what was written to the Notion `Hook` field.

If `Amazon Main Image URL` was null in Notion, set `amazon_image_url` to `null` and note this — the user will need to drop `product.jpg` manually before `/generate-pins` can run.

---

## Step 6.5 — Auto-download product image

After writing `hooks.json`, run `fetch_product_image.py` to download the product image automatically:

```bash
python3 fetch_product_image.py <product-slug>
```

The script:
- Reads `amazon_image_url` from `hooks.json`
- Upgrades the Amazon CDN URL to full resolution (`_AC_SL1500_`)
- Downloads and saves as `pins/<product-slug>/product.jpg`
- Skips if `product.jpg` already exists and is ≥500KB
- Validates the downloaded image is ≥600px on the short edge
- Exits with a clear error message (not a stack trace) if the CDN returns a non-200 status

Track the outcome — you will need it in the Done step to decide whether to chain into `/generate-pins`.

---

## Step 7 — Ask for start date

Ask the user for the start date using `AskUserQuestion`:

> "What date should pin 1 publish? (YYYY-MM-DD)"

Accept a date in `YYYY-MM-DD` format. Parse it and validate it's a real date.

---

## Step 8 — Calculate timestamps and update Notion

Calculate 9 consecutive dates starting from the provided date (1 pin per day, no gaps).

For each date, apply the priority time slot based on weekday (all times UTC):

| Weekday | Time (UTC) |
|---|---|
| Sunday | 20:00 |
| Monday | 21:00 |
| Tuesday | 20:00 |
| Thursday | 10:00 |
| Saturday | 09:00 |
| All other days | 20:00 |

Format each as ISO 8601 UTC: `2026-05-23T20:00:00Z`

Update all 9 Notion records in parallel using `mcp__notion__API-patch-page`:
```json
{"Publish Date": {"date": {"start": "YYYY-MM-DDTHH:MM:SSZ"}}}
```

---

## Step 9 — Write schedule_meta.json

Write to `pins/<product-slug>/schedule_meta.json`.

**pin_file derivation** — must match `generate_pins.py` exactly:

Angle → slug map:
- `"Hot Sleeper"` → `hot`
- `"Light Sleeper"` → `light`
- `"Anxious/Insomniac"` → `anxious`
- `"Restless Sleeper"` → `restless`

Variant → suffix map:
- null hook (Template A) → `clean`
- first hook for angle (Template B) → `hook-a`
- second hook for angle (Template B) → `hook-b`

Pattern: `pin-{1-indexed position}-{angle-slug}-{clean|hook-a|hook-b}.png`

Example for a 3-angle product with angles hot / light / restless:
```
pin-1-hot-clean.png
pin-2-hot-hook-a.png
pin-3-hot-hook-b.png
pin-4-light-clean.png
pin-5-light-hook-a.png
pin-6-light-hook-b.png
pin-7-restless-clean.png
pin-8-restless-hook-a.png
pin-9-restless-hook-b.png
```

**Full format:**

```json
{
  "product_slug": "<product-slug>",
  "product_page_id": "<product page ID from step 2>",
  "records": [
    {
      "notion_page_id": "<id from step 5>",
      "pin_file":       "<derived above>",
      "title":          "<title from step 4>",
      "description":    "<description from step 4>",
      "affiliate_link": "<affiliate link from step 2>",
      "publish_at":     "<ISO 8601 UTC from step 8>"
    }
  ]
}
```

9 records total, in the same order as `hooks.json`. `product_page_id` is used by `/generate-pins` to update the Products DB `Status` to `"Scheduled"`.

---

## Step 10 — Update product status in Notion

Update the product record using `mcp__notion__API-patch-page`:
- `page_id`: the product page ID from step 2

```json
{"Status": {"select": {"name": "Processed"}}}
```

---

## Done

Report a summary:
- Product slug
- 3 angles chosen
- Notion records created (count)
- Start date and end date of the schedule
- Files written: `hooks.json`, `schedule_meta.json`
- Image status: auto-downloaded ✅ or manual drop required ⚠️

**If the image was downloaded successfully (Step 6.5 succeeded):** proceed immediately — invoke the `generate-pins` skill using the Skill tool, passing the product name as the argument. Do not ask the user to run it separately.

**If the image download failed or `amazon_image_url` was null:** report the error clearly. Tell the user to drop `product.jpg` into `pins/<product-slug>/` then run `/generate-pins <product-name>`.
