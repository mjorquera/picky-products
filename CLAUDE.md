# Picky Products — Project Context

## What this is

Picky Products is a Pinterest-focused affiliate marketing side project. The goal is largely autonomous operation: AI agents select, create, and distribute affiliate content with minimal daily input. It's also the first product in a broader vision for a solo-founder development agency.

- **Niche:** Sleep Optimization Accessories (UK buyers)
- **Audience personas:** hot sleepers, light sleepers, anxious/insomniac sleepers, restless sleepers — select 3 per product based on fit
- **Distribution:** Pinterest (primary)
- **Monetisation:** Amazon Associates (UK); PA API pending activation at 3 qualifying sales

---

## Stack

| Tool | Role |
|---|---|
| **Apify** (MCP) | Product discovery |
| **Notion** (MCP) | Source of truth for products and distribution data |
| **Python + Pillow** | Pin image generation (`generate_pins.py`) |
| **Pinterest API v5** | Pin scheduling via Make (`schedule_via_make.py`, `publish_due_pins.py`) |
| **Amazon PA API** | Pending activation (3 qualifying sales) |

---

## Notion databases

- **Products DB:** `ddf18096-68b1-8219-bb44-01b7fa5c9611` (collection: `a2c18096-68b1-82cf-87d5-075ab33cfb3c`)
- **Distribution DB:** `c7718096-68b1-83ea-8ab2-01b6e3a2b2fe` (collection: `34618096-68b1-8227-ade9-0785f977dfae`)
- `Enrichment Status` field (Products DB) valid values: `"Empty"`, `"Candidate"`, `"Enriched"`, `"Scheduled"`, `"Distributed"`. Set to `"Scheduled"` by `/generate-pins` once images are live and pins are queued for the daily publisher.
- Distribution DB `Affiliate Link` is a **rollup** from the Product relation — read-only, auto-populated.
- Distribution DB `Angle` valid values: `"Hot Sleeper"`, `"Light Sleeper"`, `"Anxious/Insomniac"`. `"Restless Sleeper"` is not a valid select option — omit the field when writing Restless Sleeper pins.

---

## Content workflow

**Step 1 — Process product**
Run `/process-product <product name>`. The skill handles everything: looks up the product in Notion, generates copy for 9 pins, creates Distribution DB records, writes `hooks.json` and `schedule_meta.json`, and assigns publish dates at 1 pin/day from a start date you provide.

**Step 2 — Add product image**
Drop `product.jpg` into `pins/<product-slug>/` (save the highest-res image from the Amazon listing — right-click the main product photo).

**Step 3 — Generate pin images**
Run `/generate-pins <product name>`. The skill runs `generate_pins.py`, copies images to `docs/pins/<slug>/`, updates Notion status → `Image Created`, and commits and pushes so images are live at `https://mjorquera.github.io/picky-products/pins/<slug>/`.

**Step 5 — Daily publisher handles the rest**
`publish_due_pins.py` runs automatically via Cowork at 9 PM local. It picks up pins where `publish_at <= now (UTC)`, sends them to the Make webhook → Pinterest, updates Notion → `Scheduled`, and moves completed product folders to `pins/scheduled/`.

**Pinterest boards:** All pins go to the **UK Comfort Products for Sleep** board.

---

## Pinterest scheduling

- **`publish_due_pins.py`** — daily publisher, run automatically by Cowork (9 PM local). Publishes one-by-one based on `publish_at`.
- **`schedule_via_make.py`** — manual full-batch publisher. Sends all 9 pins at once. Use for testing or emergency publish only.

Make's Pinterest connector has Standard API access, bypassing the Trial restriction on the local Pinterest app (App ID `1570355`).

**Timing note:** Make posts pins immediately (no native `publish_at` support). The timestamps in `schedule_meta.json` control when `publish_due_pins.py` sends each pin — pins land on Pinterest within ~1 hour of the scheduled time.

### Make scenario

- **Webhook URL**: `https://hook.eu2.make.com/1ug4xsjoxp8jycg7dungek86smnuuorn`
- **Flow**: Webhooks (module 2) → Flow Control Iterator (module 5) → Pinterest Make an API Call (module 6)
- **Pinterest body**:
```json
{
  "board_id": "1063764443174541558",
  "title": "{{5.title}}",
  "description": "{{5.description}}",
  "link": "{{5.affiliate_link}}",
  "media_source": { "source_type": "image_url", "url": "{{5.image_url}}" }
}
```

### One-time setup

**Status: complete as of 2026-05-15.** All `.env` keys are populated and the Notion integration is connected.

For reference if re-doing from scratch:

1. Create a Pinterest app at https://developers.pinterest.com/apps/
   - App ID: `1570355` — set redirect URI: `http://localhost:8080/callback`
   - **Do not use the "Generate token" button** on the app page — it omits `pins:write`
2. `pip3 install requests --break-system-packages`
3. `python3 pinterest_auth.py` — follow prompts to get tokens + board ID saved to `.env`
4. Create a Notion internal integration at https://www.notion.so/my-integrations
   - Add `NOTION_TOKEN` to `.env` and share both databases with the integration

### .env keys

```
PINTEREST_CLIENT_ID="..."
PINTEREST_CLIENT_SECRET="..."
PINTEREST_ACCESS_TOKEN="..."
PINTEREST_REFRESH_TOKEN="..."
PINTEREST_BOARD_ID="..."
NOTION_TOKEN="ntn_..."
```

---

## Image generation

**Script:** `generate_pins.py <product_slug>`  
**Canvas:** 1000×1500px — white background, large product image, rounded pill at bottom with bold dark text  
**Prerequisites:** `product.jpg` and `hooks.json` must both be present in `pins/<product-slug>/` before running.

**Output:**
```
pins/<product-slug>/
  hooks.json
  product.jpg
  pin-1-{angle}-clean.png       ← Template A: pill = angle label
  pin-2-{angle}-hook-a.png      ← Template B: hook variant A
  pin-3-{angle}-hook-b.png      ← Template B: hook variant B
  ... (9 total)
```

---

## Folder conventions

```
pins/
  <product-slug>/       ← active: processing or awaiting scheduling
  scheduled/
    <product-slug>/     ← all 9 pins scheduled in Pinterest
```

---

## Agent instructions

- Niche: Sleep Optimization Accessories targeting UK buyers
- Target price range: £20–£80
- Minimum quality bar: 50 reviews, 4★+
- All Amazon links must use amazon.co.uk
- Notion is the source of truth — always write to Products DB before Distribution DB

---

## Session close

Run `/bye` at the end of every working session. The skill reviews the session for corrections and feedback, then updates the relevant skill files so the next session starts better.

---

## Principles

- **Agent-first:** Build toward autonomous operation; human input = triggering and reviewing.
- **Iterative validation:** Test new integrations manually (curl, direct API calls) before wiring into workflows.
- **Nothing is fixed:** All tools and channels remain open to challenge — including strategic direction.
- **Momentum over perfection:** Manual steps are acceptable short-term trade-offs.
- **AI-led strategy is welcome:** The niche pivot to Sleep Optimization Accessories came from the CEO agent's analysis. That's the model.
