# Picky Products — Consolidated Plan

> **Live backlog and status now tracked in Linear** (project `Picky Products`, team `Wallmapu`). This file stays as phase rationale, risk notes, and history — don't add new backlog items here, create a Linear issue instead.

**Last updated:** 2026-06-29  
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

### 2.3: Pinterest SEO — keyword and hashtag improvements 🔄

**Why:** Audit (2026-06-29) found product-category keywords severely underused — `"cooling pillow uk"` appeared once across 171 pins. Generic broad keywords were well covered but product-specific terms weren't. No hashtags beyond `#ad`.

- ✅ Updated `process-product` skill with two-tier keyword system (broad + product-category) and mandatory usage minimums
- ✅ Added 14-hashtag rotation list, angle-matched, to all future pin descriptions
- ⬜ Write keyword-rich descriptions for all 5 Pinterest boards (manual, ~20 min on Pinterest directly)

### 2.4: Pin image quality — angle label pill ⬜

**Why:** Current Template C pins (clean, tinted background) have no text beyond the `#ad` label. Adding a persona pill at the bottom ("Hot Sleeper", "Light Sleeper", "Anxious Sleeper") makes the purpose of each pin immediately legible and more visually intentional. Do this after Phase 3.3 data confirms clean pins are underperforming, so the change is data-driven rather than speculative.

- Add a rounded pill (white or angle-tinted) at bottom-centre of Template C with the angle label
- Match pill style to Template B for visual consistency
- Update `generate_pins.py` — Template C branch only
- Backfill is not required; new products will pick it up automatically

---

## Phase 3 — Analytics Feedback Loop

### 3.1: Pinterest baseline documented ✅

Done. Weekly analytics reports live in `analytics/` from W21 through W25.

### 3.2: Pin ID capture and metrics sync ✅

Needed for data-driven hook selection. Without this, performance assessment is manual and imprecise.

- Add `Pinterest Pin ID`, `Impressions`, `Outbound Clicks` fields to Distribution DB
- Modify `publish_due_pins.py` to parse the Pin ID from the Make webhook response and PATCH Notion
- Write `analytics_sync.py`: queries Distribution DB for published pins, calls Pinterest Analytics API v5 (`GET /v5/pins/{pin_id}/analytics?metric_types=IMPRESSION,OUTBOUND_CLICK`), updates Notion weekly
- Add `Performance` formula: `Outbound Clicks / Impressions * 100`
- Schedule via Cowork weekly cron

**Done.** `analytics_sync.py` live. Notion Distribution DB has `Pinterest Pin ID`, `Impressions`, `Outbound Clicks` fields. Make scenario captures Pin ID at publish time. Cowork weekly task runs sync every Sunday 08:00 UTC.

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

### 4.2: PA API readiness ⬜ — blocked

**Eligibility:** Amazon's Creators API route requires 10 qualifying sales within the past 30 days. Current count: 3 total (recorded 2026-05-21), none in the last 30 days. Account is active and approved — this is a volume gate, not an account issue.

**When to revisit:** once the dashboard shows 10+ qualifying sales in a rolling 30-day window, apply via the Creators API page (Tools → Product Advertising API). Until then, no action.

- Add `PAAPI_ACCESS_KEY`, `PAAPI_SECRET_KEY`, `PAAPI_PARTNER_TAG` placeholders to `.env`
- Write `pa_api_check.py`: calls `GetItems` for one ASIN; prints title, price, availability; clear error if credentials empty

---

## Prioritised next actions

| # | Action | Phase | Effort | Why now |
|---|---|---|---|---|
| 1 | ~~Process Sacred Thread Bamboo Viscose Bed Sheet Set~~ ✅ | 1.2 | done | Phase 1 complete |
| 2 | Hook A/B performance tracking agent | 3.3 | ~3h | Closes the feedback loop; improves copy quality autonomously once impression data exists |
| 3 | Write keyword-rich Pinterest board descriptions | 2.3 | ~20m | Manual on Pinterest — completes SEO audit actions |
| 4 | Pin image quality — angle label pill | 2.4 | ~2h | Do after 3.3 confirms clean pins are underperforming |
| 5 | Weekly digest script | 4.1 | ~1h | Operational — do after pipeline volume justifies it |
| 6 | PA API | 4.2 | — | Blocked: needs 10 qualifying sales in 30 days |

---

## Key risks

- **Landing page won't help if affiliate links were the only problem:** Phase 0.1 is the highest-confidence fix but not guaranteed. Monitor impressions for 2 weeks post-launch before concluding.
- **Impression drop may be algorithm-level suppression:** The W25 -96% drop coincides with a known Pinterest algorithm shift (documented in community forums). Landing pages reduce the spam signal but don't override platform-level changes.
- **Board split requires Make update:** The Make scenario currently hardcodes `board_id`. Updating it for per-angle routing requires editing the Make flow — low technical risk but requires access.
- **PA API 180-day window:** If the clock started at sign-up (not at first qualifying sale), the window may close before activation. Check the Associates dashboard.

---

## Reference

Original LLM council plan: `llm-council/runs/20260523-analyse-picky-products-and-produce-a-pri/final-plan-clean.md`
