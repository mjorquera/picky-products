# Plan

## Overview

Accelerate Picky Products to first £ of affiliate revenue by sequencing work in revenue-impact order: fix monetisation hygiene, fill the content queue with the first five Candidates, automate the remaining manual steps, add visual differentiation and a feedback loop, then process the remaining five Candidates informed by early data. All changes target solo operation under 30 minutes per week.

## Scope

- In: affiliate link audit; batch-processing 10 Candidates in two staged tranches; auto-image download from Amazon CDN; pin template improvements including ASA `#ad` compliance; Pinterest analytics feedback loop via API; Pinterest SEO enrichment in descriptions; PA API readiness script; weekly digest script
- Out: paid tools, paid advertising, new channels (Pinterest is primary until 50+ distributed pins), changes to the Make webhook or Pinterest OAuth flow, structural Notion schema changes beyond adding fields

---

## Phases

### Phase 1: Revenue Foundation

**Goal**: Ensure every live and queued pin links correctly and fill the first content tranche before any other work. Both tasks require no new infrastructure.

#### Task 1.1: Affiliate link hygiene audit

- Location: Notion Products DB (`a2c18096-68b1-8219-bb44-01b7fa5c9611`), Distribution DB (`c7718096-68b1-83ea-8ab2-01b6e3a2b2fe`)
- Description: Verify `tag=pickyprod-21` is present in the final destination URL for all products (3 distributed, 2 active, 10 Candidates). Confirm the Distribution DB `Affiliate Link` rollup is non-null for all Scheduled/Distributed records. Fix any gaps in Products DB. This is the highest-leverage change — a broken tag means zero commission on every click.
- Estimated Tokens: 3,000
- Dependencies: None
- Steps:
  - Query Products DB; extract `Affiliate Link` for all records
  - For each `amzn.to` link, follow redirect and confirm `tag=pickyprod-21` in final URL
  - For any missing tag, patch Products DB with full `amazon.co.uk/dp/ASIN?tag=pickyprod-21` URL
  - Query Distribution DB for all Scheduled/Distributed records; confirm `Affiliate Link` rollup is populated (non-null)
  - Add a note to the `/process-product` skill: always use full `amazon.co.uk` URL with tag, never bare `amzn.to` without verified tag
- Acceptance Criteria:
  - All 15 products have `tag=pickyprod-21` in their resolved affiliate URL
  - Zero Scheduled/Distributed Distribution DB records return null for `Affiliate Link` rollup

#### Task 1.2: Process first 5 Candidate products

- Location: `pins/`, Notion Products DB and Distribution DB
- Description: Process the five Candidates with highest review count and best fit for the three supported personas — these are most likely to generate early clicks. Order: Manta Sleep Mask (~14k reviews), Brown Noise Machine (~11k), Dreamegg D11 (~3.6k), LectroFan (~2.2k), Good Nite Weighted Blanket. Run `/process-product` then `/generate-pins` for each, using rolling start dates continuing from the current last scheduled pin.
- Estimated Tokens: 60,000 (5 × ~12,000)
- Dependencies: Task 1.1 complete (links verified before new records created)
- Steps:
  - Run a single test product end-to-end before batching to catch any skill bugs
  - Query Distribution DB for the latest `Publish Date` across all active records — this is the start date for product 1
  - For each product: run `/process-product <name> --start-date <date>`, then drop `product.jpg` from Amazon listing, then run `/generate-pins <name>`
  - Verify `Enrichment Status = Scheduled` in Notion and GitHub Pages images resolve (HTTP 200) before moving to the next product
  - Confirm `publish_due_pins.py` dry-run returns the next 7 pins in correct date order after the final product
- Acceptance Criteria:
  - 5 products at `Enrichment Status = Scheduled`; 45 Distribution DB records created with valid `Publish Date`, `Pin Title`, `Affiliate Link`
  - 45 pin images live at `https://mjorquera.github.io/picky-products/pins/<slug>/`
  - No publish-date collisions: no two Distribution DB records share the same `Publish Date`

---

### Phase 2: Automation and Visual Quality

**Goal**: Eliminate the manual image-save step and improve pin visual differentiation before the second Candidate tranche is processed.

#### Task 2.1: Auto-download product image from Amazon CDN

- Location: New `fetch_product_image.py`; integrated into `/process-product` skill
- Description: Products DB stores `Amazon Main Image URL` (e.g. `https://m.media-amazon.com/images/I/71eiAJ99OgL._AC_UL320_.jpg`). Replace `_AC_UL320_` with `_AC_SL1500_` to request the full-resolution image. Download and save as `pins/<slug>/product.jpg` at `/process-product` time — not at `/generate-pins` time — to avoid mid-batch failures from expired CDN URLs.
- Estimated Tokens: 3,000
- Dependencies: Task 1.2 complete (validates `Amazon Main Image URL` field is consistently populated)
- Steps:
  - Write `fetch_product_image.py <slug>`: reads `Amazon Main Image URL` from `hooks.json`, substitutes `_AC_UL320_` → `_AC_SL1500_`, fetches with `requests.get` and a `Mozilla/5.0` User-Agent, saves to `pins/<slug>/product.jpg`
  - Verify fetched image is ≥600px on short edge via `Image.open().size`; abort with clear error if smaller or if CDN returns non-200
  - Integrate call into `/process-product` skill immediately after writing `hooks.json`; skip gracefully if `product.jpg` already exists (≥500KB)
  - Add `amazon_image_url` key to the `hooks.json` schema written by `/process-product`
  - Update CLAUDE.md to remove manual image-save step from content workflow
- Acceptance Criteria:
  - Running `/process-product <name>` on a new Candidate produces `pins/<slug>/product.jpg` without manual intervention
  - Fetched image is ≥600px short edge
  - Graceful error (not stack trace) if CDN returns 403/404, with fallback instruction to drop `product.jpg` manually

#### Task 2.2: Add persona-tinted template and ASA compliance

- Location: `generate_pins.py`
- Description: Two changes in one pass. First, add Template C: a subtle persona-tinted background (Hot Sleeper `#E8F4FD` cool blue, Anxious/Insomniac `#F0EEF8` warm lavender, Light Sleeper `#E8EEF5` pale slate) replacing the current Template A (clean label) — same filename convention, no Distribution DB changes. Second, add `#ad` in 9pt at the bottom-right of the pill on all templates to satisfy ASA requirements. Optionally add a `£XX on Amazon` sub-line in the pill if `price` is set in `hooks.json`.
- Estimated Tokens: 6,000
- Dependencies: Task 2.1 (validates image pipeline is stable before modifying the generator)
- Steps:
  - Define `PERSONA_TINTS = {\"Hot Sleeper\": (232,244,253), \"Light Sleeper\": (232,238,245), \"Anxious/Insomniac\": (240,238,248)}` in `generate_pins.py`
  - Add `render_template_c(product_img, hook_text, angle)`: fill canvas with tint, paste product image centred at 60% height, render hook text without pill
  - Replace Template A output with Template C; keep Templates B (hook-a) and B-variant (hook-b) unchanged
  - Add `#ad` label (9pt, 50% opacity dark text) to bottom-right of pill in all templates
  - Add `price` to `hooks.json` schema in `/process-product`; if populated, render `£XX on Amazon` as secondary pill line
  - Verify contrast ratio ≥4.5:1 programmatically before committing
  - Limit initial rollout to newly processed products; do not regenerate already-scheduled pins (Pinterest caches image URLs at pin-creation time)
- Acceptance Criteria:
  - Three angle variants are visually distinct from each other and from the prior all-white output
  - `#ad` label present on every generated pin
  - Pill height adjusts for two-line price variant without clipping
  - Template B (hook variants) logic is unmodified

---

### Phase 3: Analytics Feedback Loop

**Goal**: Create a lightweight weekly signal on which hooks, angles, and products are generating outbound clicks — automated, no new paid tools.

#### Task 3.1: One-time Pinterest account health baseline

- Location: Pinterest Business Analytics (web UI) — 10 minutes, manual
- Description: Before investing in visual work, confirm pins are being distributed. Check board-level impressions and profile reach for the past 30 days. If impressions are near zero, the issue is account age or thin profile — not visual quality — and Phase 2 effort should be deprioritised. Document the baseline in Notion.
- Estimated Tokens: 500
- Dependencies: None
- Steps:
  - Open Pinterest Business Analytics → Overview → select UK Comfort Products for Sleep board → note impressions, saves, outbound clicks for last 30 days
  - Create a Notion page: \"Pinterest Baseline [date]\" with these three numbers
  - If board impressions < 500 in the last 30 days, flag this as a distribution problem rather than a creative problem
- Acceptance Criteria:
  - Baseline numbers documented in Notion before Task 2.2 work begins
  - Go/no-go decision on visual overhaul recorded

#### Task 3.2: Add Pinterest Pin ID capture and analytics sync

- Location: `publish_due_pins.py`, new `analytics_sync.py`, Notion Distribution DB
- Description: Add three fields to Distribution DB — `Pinterest Pin ID` (text), `Impressions` (number), `Outbound Clicks` (number). Modify `publish_due_pins.py` to parse the Pin ID from the Make webhook response and write it back to Notion. Write `analytics_sync.py` to call Pinterest Analytics API weekly per published pin and update both numeric fields.
- Estimated Tokens: 8,000
- Dependencies: Task 3.1 (account health confirmed before building analytics)
- Steps:
  - Add `Pinterest Pin ID`, `Impressions`, `Outbound Clicks` fields to Distribution DB via `mcp__notion__API-update-a-data-source`
  - Test one manual Make run to inspect the webhook response format and confirm Pin ID is present; if not, use Pinterest Analytics API date-range query to match by title as fallback
  - Modify `publish_due_pins.py`: after successful Make call, parse Pin ID from response and PATCH the Notion record
  - Write `analytics_sync.py`: query all Distribution DB records with non-null `Pinterest Pin ID` and `Status = Scheduled`; call `GET /v5/pins/{pin_id}/analytics?metric_types=IMPRESSION,OUTBOUND_CLICK` for trailing 30 days; PATCH Notion records. Run weekly via Cowork cron.
  - Add `Performance` formula field to Distribution DB: `Outbound Clicks / Impressions * 100`
- Acceptance Criteria:
  - `publish_due_pins.py` writes non-null `Pinterest Pin ID` to Notion after a live publish
  - `analytics_sync.py` runs without error and populates fields for at least one pin with >48h of data
  - Script handles missing/revoked pins gracefully (logs warning, skips, continues)
  - Weekly cron added alongside existing daily publisher

---

### Phase 4: Scale and Pinterest SEO Deepening

**Goal**: Process the remaining 5 Candidates informed by 2–3 weeks of early analytics data, and improve discoverability of all published pins with keyword enrichment.

#### Task 4.1: Pinterest SEO enrichment in `/process-product`

- Location: `/process-product` skill prompt
- Description: Update the skill to include 2–3 long-tail UK search terms in every pin description (e.g. \"best cooling pillow UK\", \"pillow for hot sleepers UK review\", \"sleep accessories UK\"). No code change — prompt update only. This is near-zero effort with meaningful long-term discoverability impact on Pinterest's search index.
- Estimated Tokens: 1,000
- Dependencies: None — can be applied before processing the second tranche
- Steps:
  - Update `/process-product` skill prompt: add instruction to include 2–3 UK-specific long-tail sleep product search terms in each pin description, formatted naturally (not keyword-stuffed)
  - Verify output on one test product before batch processing
- Acceptance Criteria:
  - New Distribution DB records contain at least one long-tail UK search term per pin description (e.g. contains \"UK\")
  - Terms are embedded naturally, not appended as a raw keyword list

#### Task 4.2: Process remaining 5 Candidate products

- Location: `pins/`, Notion Products DB and Distribution DB
- Description: Process the remaining 5 Candidates — Memory Foam Neck Support Pillow, Sacred Thread Bamboo Sheet Set, Bambaw Bamboo Fitted Sheet, LINENWALAS Bedding Set, Cooling Pillow Shredded Memory Foam — using the same rolling start-date approach. By this point auto-image download (Task 2.1), the updated template (Task 2.2), and the SEO-enriched skill (Task 4.1) are all in place, so these products benefit from all improvements.
- Estimated Tokens: 60,000 (5 × ~12,000)
- Dependencies: Tasks 2.1, 2.2, 4.1 complete; at least 2 weeks of analytics data available from Phase 1 products to validate or adjust approach
- Steps:
  - Review `analytics_sync.py` output: if any angle or hook type shows zero outbound clicks across Phase 1 products, adjust `/process-product` skill defaults before this batch
  - Process each product sequentially; verify `Enrichment Status = Scheduled` and GitHub Pages live before moving to the next
- Acceptance Criteria:
  - All 10 Candidates at `Enrichment Status = Scheduled`
  - 90 total new Distribution DB records with no publish-date collisions
  - Publishing queue extends at least 90 days from today

---

### Phase 5: Operational Efficiency and PA API Readiness

**Goal**: Reduce weekly manual work to under 15 minutes and prepare for PA API activation.

#### Task 5.1: Weekly digest script

- Location: New `weekly_digest.py`
- Description: A terminal-printable weekly health check. Prints: pins published in the last 7 days, upcoming 7 scheduled pins, any records where `Publish Date < today` and `Published Link` is null (failed publishes), and top 5 by `Outbound Clicks` once analytics are populated.
- Estimated Tokens: 2,000
- Dependencies: Task 3.2
- Steps:
  - Write `weekly_digest.py`: queries Distribution DB for last 7 days, next 7 days, and failed-publish flags; prints structured stdout summary in under 5 seconds
  - Add to CLAUDE.md session-open checklist: \"run `python3 weekly_digest.py` first\"
- Acceptance Criteria:
  - Script completes in under 5 seconds
  - Failed publish detection correctly identifies `Publish Date < today` + null `Published Link`
  - Renders cleanly when analytics fields are null (no division by zero)

#### Task 5.2: PA API readiness script

- Location: New `pa_api_check.py`, `.env`
- Description: When the 3 qualifying sales milestone is reached, activation is not automatic. This script reduces integration time to under 15 minutes once credentials are granted. It also validates that the tag and partner configuration are correct.
- Estimated Tokens: 2,000
- Dependencies: Task 1.1 (affiliate links verified clean)
- Steps:
  - Add `PAAPI_ACCESS_KEY`, `PAAPI_SECRET_KEY`, `PAAPI_PARTNER_TAG` as empty placeholders with comments to `.env`
  - Write `pa_api_check.py`: calls `GetItems` for one known ASIN; prints title, price, availability; exits with human-readable error (not stack trace) if credentials are empty
  - Document in CLAUDE.md: \"run `python3 pa_api_check.py` after adding credentials\"
- Acceptance Criteria:
  - Script exists with no hardcoded credentials
  - Clear human-readable error if `.env` keys are empty
  - No additional packages required beyond `requests` (already installed)

---

## Testing Strategy

- **Task 1.1**: Follow each affiliate link with `curl -sIL <url> | grep -i location`; confirm `tag=pickyprod-21` appears in final redirect URL for all 15 products.
- **Task 1.2**: After full batch, run `publish_due_pins.py` in dry-run mode; confirm next 7 pins return valid image URLs and non-null affiliate links. Verify no two records share a `Publish Date`.
- **Task 2.1**: Delete `product.jpg` from a test slug; run `/process-product`; confirm file appears at `pins/<slug>/product.jpg` with short edge ≥600px (`Image.open().size`). Test graceful failure with a broken URL.
- **Task 2.2**: Eyeball-test all three tinted variants alongside existing Templates B. Programmatically verify contrast ratio ≥4.5:1. Confirm `#ad` present on every output. Test empty `price` field renders without error.
- **Task 3.2**: Publish one live pin; confirm `Pinterest Pin ID` written to Notion within 60 seconds. Run `analytics_sync.py` next day and confirm `Impressions` field populated for at least one pin.
- **Task 4.1**: Spot-check three new Description fields from the second batch and confirm at least one UK search term present per description.
- **Regression**: After each phase, run `publish_due_pins.py` dry-run to confirm pipeline is intact.

---

## Risks

- **Amazon CDN URL expiry**: `_AC_SL1500_` URLs for product images are generally stable but can rotate. Mitigation: `fetch_product_image.py` validates file size >10KB after download; prints a clear fallback instruction if CDN returns non-200. Downloading at `/process-product` time (not `/generate-pins`) reduces the window for expiry between write and use.
- **Make webhook may not return Pinterest Pin ID**: If the Make Pinterest module does not surface the created Pin ID in its response, `publish_due_pins.py` write-back will silently fail. Mitigation: test with one manual Make run before coding; if unavailable, fall back to Pinterest Analytics API date-range query matching by title to recover Pin IDs.
- **Template C may underperform white backgrounds**: Pinterest's algorithm behaviour varies by category; no A/B evidence exists. Mitigation: limit Template C to the second Candidate tranche initially; compare `Outbound Clicks` via `analytics_sync.py` before rolling back or forward. Do not regenerate already-scheduled pins (Pinterest caches image URLs at creation time — regeneration is ineffective for live pins).
- **10 Candidates queued without performance data**: Filling 90 days of queue with unvalidated content risks poor product-type fit. Mitigation: staged approach — process 5 first (Phase 1), validate with analytics, then process 5 more (Phase 4) with adjustments if needed.
- **Pinterest account distribution problem**: If the account is penalised for being new or thin, visual improvements have no effect. Mitigation: Task 3.1 baseline check gates Phase 2 visual work. If impressions are near zero, investigate account health before investing further.
- **PA API 180-day application window**: Amazon Associates UK closes accounts without 3 qualifying sales within 180 days. Confirm application date; if fewer than 60 days remain, prioritise higher-price products (Weighted Blanket £65, LectroFan £70) in the publishing queue to maximise conversion value per click.

---

## Rollback Plan

- **Task 1.1 (link patches)**: All Products DB changes recoverable from Notion page history. Revert via Notion UI if a link was overwritten incorrectly.
- **Task 1.2 (batch processing)**: Distribution DB records created after the batch start date can be set to `in_trash: true` via Notion MCP. GitHub Pages images removed by deleting `docs/pins/<slug>/` and committing. Products DB `Enrichment Status` reset to `Candidate` manually.
- **Task 2.1 (image auto-download)**: If a fetched image is lower quality than expected, `git checkout HEAD -- pins/<slug>/product.jpg` restores a manually-placed version. Guard: script skips fetch if `product.jpg` already exists and is ≥500KB.
- **Task 2.2 (template change)**: `git revert` on `generate_pins.py` restores prior templates. Re-run `/generate-pins` for affected not-yet-published products and push to GitHub Pages. Already-published pins are unaffected (Pinterest caches the image URL).
- **Task 3.2 (Notion schema)**: New Distribution DB fields can be removed via `update-a-data-source` with the property set to `null`. `publish_due_pins.py` changes revert via git.
- **Task 5.2 (PA API script)**: Additive file with no effect until credentials are added. Delete `pa_api_check.py` and remove `.env` placeholder keys if unwanted.

---

## Edge Cases

- **Candidate with no `Amazon Main Image URL`**: `fetch_product_image.py` must check for null before fetching; log a clear warning and fall through to manual-drop instruction rather than aborting the batch.
- **Publish-date collisions**: When processing multiple products, each product's start date must be the previous product's last `Publish Date` + 1 day. Query Distribution DB for `MAX(Publish Date)` before each `/process-product` call; do not use today's date.
- **Restless Sleeper angle**: CLAUDE.md specifies `Restless Sleeper` is not a valid Angle select option and the field must be omitted. Scan all new Distribution DB records for `Angle = Restless Sleeper` before the first publish run from the new batch.
- **`publish_due_pins.py` runs during GitHub Pages propagation**: If a pin image URL returns 404 when Make fetches it, the Pinterest publish fails silently. Add an HTTP HEAD check for the image URL before sending to the Make webhook; retry once after a 30-second delay.
- **Slug collision**: If two products normalise to the same directory name, `/process-product` may overwrite an existing folder. Add a collision check that appends `-2` if the directory already exists.
- **PA API activation mid-batch**: If PA API activates while Candidates are mid-process, do not mix `amzn.to` and PA API links within a single product's 9 pins. Process all pending products with the current link format first; switch link type at a clean product boundary.

---

## Open Questions

- What is the Amazon Associates UK application date? If fewer than 60 days remain in the 180-day activation window, reorder the Candidate queue to prioritise higher-price products.
- Does the Make Pinterest module return the created Pin ID in its webhook response? The answer determines whether Task 3.2 is a 2-hour task or requires a Pinterest API polling fallback.
- Is there a Cowork interface accessible from Claude Code for adding cron entries, or does the weekly `analytics_sync.py` cron need to be added via shell?","stop_reason":"end_turn","session_id":"250857e8-2157-481d-b42e-4f24ccc54d60","total_cost_usd":0.2595933,"usage":{"input_tokens":2,"cache_creation_input_tokens":27872,"cache_read_input_tokens":23981,"output_tokens":8493,"server_tool_use":{"web_search_requests":0,"web_fetch_requests":0},"service_tier":"standard","cache_creation":{"ephemeral_1h_input_tokens":0,"ephemeral_5m_input_tokens":27872},"inference_geo":"","iterations":[{"input_tokens":2,"output_tokens":8493,"cache_read_input_tokens":23981,"cache_creation_input_tokens":27872,"cache_creation":{"ephemeral_5m_input_tokens":27872,"ephemeral_1h_input_tokens":0},"type":"message"}],"speed":"standard"},"modelUsage":{"claude-haiku-4-5-20251001":{"inputTokens":20388,"outputTokens":18,"cacheReadInputTokens":0,"cacheCreationInputTokens":0,"webSearchRequests":0,"costUSD":0.020478,"contextWindow":200000,"maxOutputTokens":32000},"claude-sonnet-4-6":{"inputTokens":2,"outputTokens":8493,"cacheReadInputTokens":23981,"cacheCreationInputTokens":27872,"webSearchRequests":0,"costUSD":0.2391153,"contextWindow":200000,"maxOutputTokens":32000}},"permission_denials":[],"terminal_reason":"completed","fast_mode_state":"off","uuid":"1040389a-5ef1-4ec3-a408-8fea9a733b7b"}