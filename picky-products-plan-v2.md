# Picky Products — Forward Plan

**Last updated: April 2026**

---

## Where things stand

The core stack is live and working. Phases 1–4 of the original plan are done — though the tools ended up different from what was planned (Python/Pillow replaced Canva for image generation; Pinterest native scheduler replaced Tailwind; Claude in Chrome handles scheduling).

The current workflow is documented in CLAUDE.md. This document covers what's still to be done.

---

## Current automation vs. manual split

| Step | Status |
|---|---|
| Product discovery (Apify scrape + scoring) | ✅ Tools connected — not yet running on a schedule |
| Write products to Notion | ✅ Automated |
| Generate pin copy (9 variants) | ✅ Automated via Cowork |
| Generate pin images | ✅ Automated via `generate_pins.py` |
| Upload PNGs to Pinterest | ❌ Manual (Pinterest blocks file injection) |
| Fill pin fields + schedule | ✅ Claude in Chrome |
| Mark as Published after publish date | ❌ Manual (no automation yet) |

**Recurring effort: ~30 mins/week** when the discovery loop is running. Currently more because discovery is manual.

---

## Next: Schedule the Discovery Loop

The weekly product discovery pipeline is built but not scheduled. This is the highest-leverage remaining step.

**Set it up:**
- Use `/schedule` in Cowork to run the discovery task every Monday at 9 AM
- The task should trigger Apify (`junglee/amazon-bestsellers` + `junglee/amazon-crawler`), score results against the quality bar (4★+, 50+ reviews, £20–£80, Pinterest visual appeal 7+), and write qualifying products to the Notion Products DB
- Claude Desktop must be running for scheduled tasks to fire — leave it open in the background

**Weekly routine once live:**
1. Monday: review new Notion shortlist (10 mins)
2. Trigger processing for approved products in Cowork
3. Save product images from Amazon, generate PNGs, run a Pinterest scheduling session
4. Done

**Apify actors:**
- Discovery: `junglee/amazon-bestsellers` — amazon.co.uk, Health & Personal Care → Sleep & Snoring, `maxItems: 30`
- Search: `junglee/amazon-crawler` — keywords: "weighted blanket uk", "sleep eye mask uk", "white noise machine uk", "cooling pillow uk", `maxItems: 10` per keyword

**Scoring criteria:**
- Pinterest visual appeal: 7+/10
- Persona fit: hot / light / anxious / restless sleeper
- Price: £20–£80
- Reviews: 50+, 4★+
- Monthly sales estimate as demand signal

---

## Scale: PA API

**Trigger: 3 qualifying Amazon Associates sales.**

Once active, the Amazon Product Advertising API replaces Apify for product data — real-time prices, stock status, and official product images. This removes the manual `product.jpg` download step (currently the only manual part of image generation) and gives cleaner, higher-res product images.

Apply via the Associates dashboard once 3 qualifying sales are confirmed.

---

## Scale: Pinterest trend signal

Once volume is up, add a Pinterest trend layer to scoring:

- Scrape trending sleep-niche pins weekly (format, keywords, engagement patterns)
- Feed top-performing formats into the scoring criteria — e.g. if hook-style pins are outperforming clean pins for a given persona, weight that in product selection
- Use this to refine which angles to lead with per product type

No MCP exists for this yet. Options: Apify Pinterest scraper, or manual review of Pinterest Trends weekly.

---

## Scale: Second niche

Once sleep is running steadily (discovery loop live, 3+ products cycling through each week), the stack is ready to expand.

To add a niche: new Apify keyword set, new Notion DB (or separate workspace), new Pinterest board, new social media context file. The CLAUDE.md structure, `generate_pins.py`, and the Cowork workflow are all reusable.

Target niche criteria: visually strong products, clear Amazon UK audience, affiliate-friendly price range (£20–£100), clear pain-point personas (same hook-driven content model).

---

## Quick reference

**Notion DB IDs**
- Products DB: `ddf18096-68b1-8219-bb44-01b7fa5c9611`
- Distribution DB: `c7718096-68b1-83ea-8ab2-01b6e3a2b2fe`

**Enrichment Status field value:** `Distibuted` (one 't' — match exactly)

**Pin structure:** 9 pins per product = 3 angles × 3 pins per angle. Per angle: 1× clean (Template A) + 2× hook variants (Template B).

**Scoring threshold:** 7+/10 → add to Notion Products DB
