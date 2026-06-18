# Picky Products — Consolidated Plan

**Last updated:** 2026-06-18  
**Source:** Consolidates `llm-council/runs/20260523-analyse-picky-products-and-produce-a-pri/final-plan-clean.md` with W25 analytics findings and Pinterest algorithm research.

---

## Status legend
- ✅ Done
- 🔄 In progress
- ⬜ Not started
- 🆕 New (added post-research)

---

## Phase 0 — Fix Distribution 🆕 **Highest priority**

Root cause of the -96% impression drop and 10+ weeks of 0 saves: pins link directly to Amazon affiliate URLs. Pinterest's algorithm classifies this as affiliate spam, suppresses distribution after day 1, and users who click through dwell on Amazon for <30 seconds — a strong negative engagement signal. This phase fixes the structural problem before any optimisation work has value.

### 0.1: Product landing pages on GitHub Pages ✅

**Why:** Pinterest favours pins that link to owned content. Landing pages give users a destination with longer dwell time, remove the direct-affiliate-link spam signal, and create a surface for saves.

- Create `docs/products/<slug>/index.html` per product: title, short description, price, affiliate CTA button, `#ad` disclosure
- Keep it minimal — one CTA, the product image, a sentence of copy
- Update `schedule_meta.json` `affiliate_link` field to use `https://mjorquera.github.io/picky-products/products/<slug>/` instead of direct Amazon URL
- Update Make webhook body accordingly (`"link"` field)
- Add landing page generation to `/process-product` skill (runs after image download, writes the HTML)
- Backfill: update existing Scheduled/Published Distribution DB records with the new landing page URL

### 0.2: Pinterest board split by angle ✅

**Why:** One board = one niche signal = capped distribution surface. Angle-specific boards give the algorithm stronger categorisation to surface content to the right users.

- Create 3 additional boards: `Hot Sleeper — Sleep Accessories`, `Light Sleeper — Sleep Accessories`, `Anxious/Insomniac — Sleep Accessories`
- Add `board_id` map to `hooks.json` / `schedule_meta.json` keyed by angle
- Update Make webhook to use the angle-matched board ID per pin
- Keep the existing `UK Comfort Products for Sleep` board as a catch-all for Restless Sleeper pins

---

## Phase 1 — Content Pipeline

### 1.1: Affiliate link hygiene audit ✅

Done. Tag corrected from `pickyprod-21` → `pickyproducts-21` across all products (audited 2026-05-23).

### 1.2: Process Candidate products 🔄

**Done:** Manta Sleep Mask, Brown Noise Machine, Dreamegg D11, Hydomi, Sleepymoon, Yogasleep Dohm, Color Noise Sound Machine, Cosi Home Pillow, LC-Dolida Sleep Mask, LINENWALAS Bedding Set, Cooling Pillow Shredded Memory Foam, Bambaw Bamboo Fitted Sheet.

**Non-sleep archive task: complete.** All 13 previously flagged off-niche products (COSORI, Tapo, TidyTrove, Russell Hobbs, Echo Dot, AIDEA, ENJOYBASICS, Aujen, LEMIKKLE, Global Gourmet, Nulaxy, MONSGA, Checkmart) are already at "Published" status — they were processed before the niche pivot. Nothing to archive.

**Remaining Candidate:** Sacred Thread Bamboo Viscose Bed Sheet Set (6 PC) — cooling bedding, in-niche, ready to process.

Queue extends to 2026-08-11 after today's batch.

---

## Phase 2 — Automation

### 2.1: Auto-download product image from Amazon CDN ✅

Done. `fetch_product_image.py` in place; `/process-product` chains into it automatically after writing `hooks.json`.

### 2.2: Template C (tinted backgrounds) + `#ad` compliance ✅

Done. `generate_pins.py` renders persona-tinted Template C (clean) and Template B (hook pills) with `#ad` bottom-right. Price sub-line supported via `hooks.json`.

---

## Phase 3 — Analytics Feedback Loop

### 3.1: Pinterest baseline documented ✅

Done. Weekly analytics reports live in `analytics/` from W21 through W25.

### 3.2: Pin ID capture and metrics sync 🔄

Needed for data-driven hook selection. Without this, performance assessment is manual and imprecise.

- Add `Pinterest Pin ID`, `Impressions`, `Outbound Clicks` fields to Distribution DB
- Modify `publish_due_pins.py` to parse the Pin ID from the Make webhook response and PATCH Notion
- Write `analytics_sync.py`: queries Distribution DB for published pins, calls Pinterest Analytics API v5 (`GET /v5/pins/{pin_id}/analytics?metric_types=IMPRESSION,OUTBOUND_CLICK`), updates Notion weekly
- Add `Performance` formula: `Outbound Clicks / Impressions * 100`
- Schedule via Cowork weekly cron

**Status:** `analytics_sync.py` written. Two manual steps remaining: (1) add `Pinterest Pin ID`, `Impressions`, `Outbound Clicks` fields to Distribution DB in Notion; (2) add a Notion "Update a database item" module to the Make scenario after module 6, mapping `{{5.notion_page_id}}` → page ID and `{{6.id}}` → `Pinterest Pin ID`.

### 3.3: Hook A/B performance tracking agent 🆕 ⬜

Once analytics data exists, this closes the feedback loop.

- Weekly agent parses analytics, groups impressions/clicks by variant suffix (`-clean`, `-hook-a`, `-hook-b`)
- Flags hook patterns with >0 long-click signals; flags angles with consistently 0 performance
- Output feeds into `/process-product` copy generation — adjust hook defaults based on what's working

---

## Phase 4 — Operations

### 4.1: Weekly digest script ⬜

- `weekly_digest.py`: prints last 7 days published, next 7 scheduled, any `Publish Date < today` with null `Published Link` (failed publishes), top 5 by Outbound Clicks
- Add to CLAUDE.md session-open checklist
- Runs in under 5 seconds

### 4.2: PA API readiness ⬜

3 qualifying sales recorded 2026-05-21. Check Amazon Associates dashboard — if the 180-day window applies, apply now.

- Add `PAAPI_ACCESS_KEY`, `PAAPI_SECRET_KEY`, `PAAPI_PARTNER_TAG` placeholders to `.env`
- Write `pa_api_check.py`: calls `GetItems` for one ASIN; prints title, price, availability; clear error if credentials empty

---

## Prioritised next actions

| # | Action | Phase | Effort |
|---|---|---|---|
| 1 | Build product landing page template + generator | 0.1 | ~3h |
| 2 | Update `schedule_meta.json` + Make webhook to use landing page URLs | 0.1 | ~1h |
| 3 | Backfill existing Scheduled pins with landing page links | 0.1 | ~1h |
| 4 | Create angle boards + update board routing in Make | 0.2 | ~1h |
| 5 | Process Sacred Thread Bamboo Viscose Bed Sheet Set (only remaining Candidate) | 1.2 | ~30m |
| 6 | Add Notion fields to Distribution DB + update Make scenario (manual) | 3.2 | ~30m |
| 7 | Weekly digest script | 4.1 | ~1h |
| 8 | PA API readiness + apply | 4.2 | ~30m |

---

## Key risks

- **Landing page won't help if affiliate links were the only problem:** Phase 0.1 is the highest-confidence fix but not guaranteed. Monitor impressions for 2 weeks post-launch before concluding.
- **Impression drop may be algorithm-level suppression:** The W25 -96% drop coincides with a known Pinterest algorithm shift (documented in community forums). Landing pages reduce the spam signal but don't override platform-level changes.
- **Board split requires Make update:** The Make scenario currently hardcodes `board_id`. Updating it for per-angle routing requires editing the Make flow — low technical risk but requires access.
- **PA API 180-day window:** If the clock started at sign-up (not at first qualifying sale), the window may close before activation. Check the Associates dashboard.

---

## Reference

Original LLM council plan: `llm-council/runs/20260523-analyse-picky-products-and-produce-a-pri/final-plan-clean.md`
