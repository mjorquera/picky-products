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
| **Cowork** | Orchestration + scheduling |
| **Apify** (MCP) | Product discovery |
| **Notion** (MCP) | Source of truth for products and distribution data |
| **Python + Pillow** | Pin image generation (`generate_pins.py`) |
| **Canva** (MCP) | Asset storage only (product images via `get-assets` if needed) |
| **Pinterest API v5** | Pin scheduling via `schedule_pins.py` (no browser) |
| **Amazon PA API** | Pending activation (3 qualifying sales) |

---

## Notion databases

- **Products DB:** `ddf18096-68b1-8219-bb44-01b7fa5c9611` (collection: `a2c18096-68b1-82cf-87d5-075ab33cfb3c`)
- **Distribution DB:** `c7718096-68b1-83ea-8ab2-01b6e3a2b2fe` (collection: `34618096-68b1-8227-ade9-0785f977dfae`)
- Product relation field requires full Notion page URL format as a list string
- `Enrichment Status` field (Products DB) valid values: `"Empty"`, `"Candidate"`, `"Enriched"`, `"Distributed"` (fully spelled, no typo)
- Distribution DB `Variant` field: `"A"` = Template A (clean), `"B"` = Template B hook variant 1, `"C"` = Template B hook variant 2
- Distribution DB `Affiliate Link` is a **rollup** from the Product relation — read-only, auto-populated. Do not attempt to write it directly.
- Distribution DB `Angle` valid values: `"Hot Sleeper"`, `"Light Sleeper"`, `"Anxious/Insomniac"`. `"Restless Sleeper"` is not a valid select option — use it in pin copy/hooks.json angle labels but map to the nearest valid option (or leave blank) when writing the Angle field in Notion.

---

## Content workflow

**Trigger:** Say "process [product name]" in Cowork.

**Output:** 9 pins per product — 3 angles × 3 pins per angle, plus two local files (`hooks.json` and `schedule_meta.json`) that drive image generation and Pinterest API scheduling.

### Step-by-step sequence

**Step 1 — Choose angles.** Pick 3 personas that genuinely fit the product. Common options: Hot Sleeper, Light Sleeper, Anxious Sleeper, Restless Sleeper. A weighted blanket fits anxious/restless/light better than hot. Don't force a persona that doesn't fit.

**Step 2 — Write copy using `social-post-writer`.** For each of the 9 pins, generate title + description. Do not write copy manually — always use the skill.

Copy rules (also in `.agents/social-media-context.md`):
- Titles: max 100 chars; first 40 chars lead with outcome or benefit
- Descriptions: 150–250 chars; natural language, keyword-integrated
- Never append "UK" to a title
- No double dashes (`--`) — use a colon or reword
- No hype language: game-changer, life-changing, revolutionary, must-have
- No overclaiming health or sleep outcomes
- British spelling throughout

**Step 3 — Create 9 Notion Distribution DB records.** One per pin. For each record set: Name (title), Description, Angle, Variant (A/B/C), Product relation, Status = `Candidate`. Capture the Notion page ID returned for each record — needed in step 6.

**Step 4 — Write `hooks.json`** to `pins/<product-slug>/hooks.json`. 9 entries in pin order (angle 1 × 3, angle 2 × 3, angle 3 × 3). Format:

```json
[
  {"angle": "Angle 1 Label",  "hook": null},
  {"angle": "Angle 1 Label",  "hook": "Hook text for pin 2"},
  {"angle": "Angle 1 Label",  "hook": "Hook text for pin 3"},
  {"angle": "Angle 2 Label",  "hook": null},
  ...
]
```

`hook: null` = Template A (clean). `hook: "..."` = Template B. Hooks must match exactly what was written to the Notion Distribution DB.

**Step 5 — Confirm available dates with Mario.** Do not guess or infer from the Distribution DB (Notion MCP search is capped at 25 records and unordered — leads to conflicts). Ask Mario to check the calendar view and provide the next free dates:

> Calendar: https://www.notion.so/mariojz/c771809668b183ea8ab201b6e3a2b2fe?v=db51809668b183aab383885aa864c2d2

Rules: max 2 pins per day, minimum 1 pin every 2 days, aim for daily. Start date = day after processing.

**Step 6 — Assign publish_at timestamps** using the priority time slots below. Match each date to its priority time based on weekday. Update the corresponding Notion Distribution DB records with the publish date.

**Priority time slots (GMT = UTC, UK audience):**
| Weekday | Time | Reason |
|---|---|---|
| Sunday | 8 PM | Highest intent — winding down, sleep mindset |
| Monday | 9 PM | Post-weekend, purchase planning |
| Tuesday | 8 PM | Mid-week peak + evening sweet spot |
| Thursday | 10 AM | UK data peak, lunch-break browse |
| Saturday | 9 AM | Weekend planning window |
| Other days | 8 PM | Fallback |

Distribute the 9 pins across the confirmed dates. Prefer the priority weekdays — if Mario's available dates include a Sunday, use it.

**Step 7 — Write `schedule_meta.json`** to `pins/<product-slug>/schedule_meta.json`. This file drives `schedule_pins.py` — get it right.

```json
{
  "product_slug": "<product-slug>",
  "records": [
    {
      "notion_page_id": "<id from step 3>",
      "pin_file":       "<derived — see rules below>",
      "title":          "<title from step 2>",
      "description":    "<description from step 2>",
      "affiliate_link": "<amazon.co.uk link with Associates tag>",
      "publish_at":     "<ISO 8601 UTC — e.g. 2026-05-15T20:00:00Z>"
    },
    ... 9 records total, in the same order as hooks.json ...
  ]
}
```

**`pin_file` derivation rules** (must match `generate_pins.py` exactly):

| hooks.json entry | Angle slug | pin_file |
|---|---|---|
| Entry 1 (hook=null) | e.g. `hot` | `pin-1-hot-clean.png` |
| Entry 2 (first hook for angle) | `hot` | `pin-2-hot-hook-a.png` |
| Entry 3 (second hook for angle) | `hot` | `pin-3-hot-hook-b.png` |
| Entry 4 (hook=null) | e.g. `light` | `pin-4-light-clean.png` |
| ...and so on | | |

Angle → slug map: `"Hot Sleeper" → "hot"`, `"Light Sleeper" → "light"`, `"Anxious Sleeper" → "anxious"`, `"Restless Sleeper" → "restless"`.

Pattern: `pin-{1-indexed position}-{angle-slug}-{clean|hook-a|hook-b}.png`

**Highest-priority keyword:** `"weighted blanket for anxiety uk"`

**Other high-value keywords (UK sleep niche):** `"sleep accessories uk"`, `"cooling pillow uk"`, `"weighted blanket uk"`, `"best sleep products uk"`, `"anxiety blanket uk"`, `"light sleeper tips"`, `"how to sleep better uk"`. Use these in pin titles and descriptions to maximise search reach. Keyword relevance is the primary ranking signal — timing is secondary.

**Pinterest boards:** All pins go to **UK Comfort Products for Sleep** board (single general board).

---

## Pinterest scheduling

Pins are scheduled via **Pinterest API v5** using `schedule_pins.py`. No browser required.

### End-to-end flow

1. **Process product** (`process [product name]`) — Cowork creates Notion Distribution records and writes two files to `pins/<product-slug>/`:
   - `hooks.json` — pin order, angles, hook text (existing)
   - `schedule_meta.json` — Notion IDs, titles, descriptions, affiliate links, publish_at timestamps (new — see format below)
2. Mario drops `product.jpg` into `pins/<product-slug>/`
3. **Generate pins** (`generate pins for [product name]`) — Cowork runs `generate_pins.py`, creates 9 PNGs, updates Notion status → `Image Created`
4. **Schedule**: `python3 schedule_pins.py <product-slug>`
   - Reads `schedule_meta.json` + PNGs
   - Base64-encodes each PNG and POSTs to Pinterest API with `publish_at`
   - Updates each Notion Distribution record → Status: `Scheduled`
   - Moves `pins/<product-slug>/` → `pins/scheduled/<product-slug>/`

### schedule_meta.json format

Cowork **must write this file** at the end of step 1, after Mario confirms the available dates. It must be in the same order as `hooks.json`.

```json
{
  "product_slug": "silentnight-cool-touch-pillow",
  "records": [
    {
      "notion_page_id": "abc123...",
      "pin_file":       "pin-1-hot-clean.png",
      "title":          "Cool pillow for hot sleepers — sleep better tonight",
      "description":    "Waking up overheated? The Silentnight Cool Touch Pillow...",
      "affiliate_link": "https://amazon.co.uk/dp/XXXXX/?tag=pickyproducts-21",
      "publish_at":     "2026-05-15T20:00:00Z"
    },
    ...9 records total, same order as hooks.json...
  ]
}
```

`publish_at` must be a full ISO 8601 UTC datetime. If only a date is available, `schedule_pins.py` will apply the priority time slot for that weekday automatically.

### One-time setup

1. Create a Pinterest app at https://developers.pinterest.com/apps/
   - Set redirect URI: `http://localhost:8080/callback`
   - Request scopes: `pins:read`, `pins:write`, `boards:read`
2. Run `python3 pinterest_auth.py` — follow the prompts to get tokens + board ID saved to `.env`
3. Create a Notion internal integration at https://www.notion.so/my-integrations
   - Add `NOTION_TOKEN="ntn_xxxx..."` to `.env`
   - Share the Distribution DB with the integration in Notion (open DB → … → Connections)

### .env keys required for scheduling

```
PINTEREST_CLIENT_ID="..."
PINTEREST_CLIENT_SECRET="..."
PINTEREST_ACCESS_TOKEN="..."
PINTEREST_REFRESH_TOKEN="..."
PINTEREST_BOARD_ID="..."
NOTION_TOKEN="ntn_..."
```

`schedule_pins.py` auto-refreshes the access token when expired using the refresh token.

## Folder conventions

```
pins/
  <product-slug>/          ← active: processing, images generated, not yet scheduled
  scheduled/
    <product-slug>/        ← all 9 pins scheduled in Pinterest
```

When a product's full 9-pin batch has been scheduled in Pinterest and Notion status is updated to `Scheduled`, its folder moves to `pins/scheduled/`. Products in `pins/` (root) are either mid-processing or awaiting a scheduling session.

---

## Image generation

Pin images are generated locally using **Python + Pillow** (`generate_pins.py` in the project root). Canva is no longer used for image generation — export URL expiry and proxy restrictions made it unworkable.

**Canvas:** 1000×1500px  
**Style:** White background, large product image, rounded pill at bottom with bold dark text (hook or angle label)  
**Script:** `generate_pins.py <product_slug>`

**Prerequisites before running the script:**
1. `pins/<product-slug>/product.jpg` — save the highest-res Amazon image (right-click main product photo on the Amazon listing)
2. `pins/<product-slug>/hooks.json` — written automatically by Cowork when creating distribution records (see below). The script will exit with a clear error if this file is missing.

**hooks.json format:**
```json
[
  {"angle": "Angle 1 Label",   "hook": null},
  {"angle": "Angle 1 Label",   "hook": "Hook text for pin 2"},
  {"angle": "Angle 1 Label",   "hook": "Hook text for pin 3"},
  {"angle": "Angle 2 Label",   "hook": null},
  {"angle": "Angle 2 Label",   "hook": "Hook text for pin 5"},
  {"angle": "Angle 2 Label",   "hook": "Hook text for pin 6"},
  {"angle": "Angle 3 Label",   "hook": null},
  {"angle": "Angle 3 Label",   "hook": "Hook text for pin 8"},
  {"angle": "Angle 3 Label",   "hook": "Hook text for pin 9"}
]
```
Angle labels are chosen per product — common options: Hot Sleeper, Light Sleeper, Anxious Sleeper, Restless Sleeper. Pick whichever 3 fit the product honestly.
`hook: null` = Template A (clean) — pill shows the angle label (e.g. "For Hot Sleepers").  
`hook: "..."` = Template B — pill shows the hook text.  
Hooks must match exactly what was written to the Notion Distribution DB.

**To generate pins for a product:**
1. Create distribution records in Notion first ("process [product name]") — Cowork writes `hooks.json` as part of that step
2. Drop `product.jpg` into `pins/<product-slug>/`
3. Say "generate pins for [product name]" — Claude runs the script and saves 9 PNGs to `pins/<product-slug>/`
4. Claude updates Distribution DB status → `Image Created`

**Output files per product:**
```
pins/<product-slug>/
  hooks.json                   ← pin definitions (source of truth for hooks)
  product.jpg                  ← source product image
  pin-1-hot-clean.png          ← Template A: pill = "For Hot Sleepers"
  pin-2-hot-hook-a.png         ← Template B: hook variant A
  pin-3-hot-hook-b.png         ← Template B: hook variant B
  pin-4-light-clean.png
  pin-5-light-hook-a.png
  pin-6-light-hook-b.png
  pin-7-anxious-clean.png
  pin-8-anxious-hook-a.png
  pin-9-anxious-hook-b.png
```

**Canva** (MCP still connected) is retained for asset storage only — product images can be fetched via `get-assets` if needed.

**Empty folders for upcoming products are pre-created** in `pins/` — just drop `product.jpg` in the relevant folder and trigger processing.

---

## Agent instructions

When working on Picky Products, always operate with the following context:

- Niche: Sleep Optimization Accessories targeting UK buyers
- Score products for three personas: hot sleepers, light sleepers, and anxious/insomniac sleepers
- Target price range: £20–£80
- Minimum quality bar: 50 reviews, 4★+
- All Amazon links must use amazon.co.uk
- Notion is the source of truth — always write to Products DB before Distribution DB

---

## Principles

- **Agent-first:** Build toward autonomous operation; human input = triggering and reviewing.
- **Iterative validation:** Test new integrations manually (curl, direct API calls) before wiring into workflows.
- **Nothing is fixed:** All tools and channels remain open to challenge — including strategic direction.
- **Momentum over perfection:** Manual steps are acceptable short-term trade-offs.
- **AI-led strategy is welcome:** The niche pivot to Sleep Optimization Accessories came from the CEO agent's analysis. That's the model.
