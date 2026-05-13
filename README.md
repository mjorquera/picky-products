# Picky Products

Pinterest-focused affiliate marketing automation for sleep accessories (UK market). AI agents select products, generate pin images, write copy, and schedule to Pinterest — with minimal daily input.

## What it does

- Discovers sleep accessory products on Amazon UK via Apify
- Scores products against 3–4 buyer personas (hot sleepers, light sleepers, anxious sleepers, restless sleepers)
- Generates 9 Pinterest pins per product: 3 angles × 3 pins (1 clean + 2 hook variants)
- Schedules pins via Pinterest API v5 with priority time slots for UK audience

## Stack

| Tool | Role |
|---|---|
| Cowork (Claude) | Orchestration, copy, Notion writes |
| Apify | Product discovery |
| Notion | Source of truth for products + distribution |
| Python + Pillow | Pin image generation |
| Pinterest API v5 | Scheduling |
| Amazon Associates | Monetisation |

## Setup

### 1. Install dependencies

```bash
pip install requests Pillow --break-system-packages
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in your values
```

### 3. Pinterest API auth (one-time)

Create an app at [developers.pinterest.com/apps](https://developers.pinterest.com/apps/):
- Redirect URI: `http://localhost:8080/callback`
- Scopes: `pins:read`, `pins:write`, `boards:read`

Then run:
```bash
python3 pinterest_auth.py
```

### 4. Notion integration (one-time)

Create an internal integration at [notion.so/my-integrations](https://www.notion.so/my-integrations), add the token to `.env` as `NOTION_TOKEN`, then share the Distribution DB with the integration inside Notion.

## Workflow

**Process a product** — triggered in Cowork:
```
process [product name]
```
Creates 9 Notion Distribution records, writes `hooks.json` and `schedule_meta.json`.

**Generate pin images:**
```bash
python3 generate_pins.py <product-slug>
```
Requires `pins/<product-slug>/product.jpg` (save from Amazon listing).

**Schedule to Pinterest:**
```bash
python3 schedule_pins.py <product-slug>
```
Reads `schedule_meta.json`, posts all 9 pins via API, updates Notion, moves folder to `pins/scheduled/`.

## Privacy

This tool posts content to a single Pinterest account owned by the developer. No end-user data is collected, stored, or processed. Affiliate links use the Amazon Associates programme.
