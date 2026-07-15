---
name: update-dashboard
description: |
  Refresh the Picky Products Control Center dashboard (control-center.html in
  the project root) with current Notion, Linear, and local schedule data —
  KPI strip, feedback loop tracker, pipeline health cards, and the pin runway
  gantt chart. Use when asked to update, refresh, or regenerate the dashboard,
  or after processing products / closing Linear issues in the same session.
license: MIT
compatibility: claude-code
allowed-tools:
  - Read
  - Edit
  - Bash
  - Artifact
  - mcp__claude_ai_Linear__list_issues
  - mcp__claude_ai_Linear__get_issue
---

# update-dashboard

Refresh `control-center.html` (project root) with a fresh pipeline snapshot. The file is a self-contained HTML document — no build step, no server-rendered data. Every number is hand-updated by this skill each time it runs.

## Invocation

```
/update-dashboard
```

No arguments. Always pulls fresh data — never trust numbers already in the file.

---

## Step 1 — Gather fresh data

Run these in parallel where possible.

**Products DB status counts** (query directly via REST, not the Notion MCP tool — `API-query-data-source` on the full Products DB exceeds the tool's output token limit):

```bash
python3 << 'EOF'
import requests
env = {}
with open('.env') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, _, v = line.partition('=')
            env[k.strip()] = v.strip().strip('"')
headers = {"Authorization": f"Bearer {env['NOTION_TOKEN']}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
url = "https://api.notion.com/v1/databases/ddf18096-68b1-8219-bb44-01b7fa5c9611/query"
counts, cursor, total = {}, None, 0
while True:
    payload = {"page_size": 100}
    if cursor: payload["start_cursor"] = cursor
    d = requests.post(url, headers=headers, json=payload).json()
    for page in d["results"]:
        total += 1
        st = page["properties"]["Status"]["select"]
        counts[st["name"] if st else "None"] = counts.get(st["name"] if st else "None", 0) + 1
    if not d.get("has_more"): break
    cursor = d["next_cursor"]
print(total, counts)
EOF
```

Same pattern against the Distribution DB (`c7718096-68b1-83ea-8ab2-01b6e3a2b2fe`) for the pins-published / image-created split.

For the legacy-vs-niche breakdown: legacy non-sleep count = products where `Category` is `Electronics`, `Kitchen`, `Home`, or `Cleaning` (20 as of 2026-07-15 — recount if it's been a while, discovery could add more pre-pivot leftovers only if the schema changes, which it shouldn't).

**Active product timeline** (drives the Pin Runway KPI and the gantt chart) — scan `pins/*/schedule_meta.json`, excluding `pins/scheduled/`:

```bash
python3 << 'EOF'
import json, glob
from datetime import datetime, timezone
now = datetime.now(timezone.utc)
for f in sorted(glob.glob('pins/*/schedule_meta.json')):
    with open(f) as fp:
        meta = json.load(fp)
    recs = meta.get('records', [])
    if not recs: continue
    dates = [r['publish_at'] for r in recs]
    done = sum(1 for d in dates if datetime.fromisoformat(d.replace('Z','+00:00')) <= now)
    print(meta['product_slug'], min(dates)[:10], max(dates)[:10], done, len(recs))
EOF
```

Each row is one gantt bar: `start` = min date, `end` = max date, `done` = pins already due (assume the daily publisher fired on schedule — spot-check against Notion if WAL-5-style sync bugs are suspected). Convert slugs to the same title-case display names used elsewhere in the project (e.g. `cosi-home-luxury-memory-foam-pillow-with-bamboo-cover` → "Cosi Home Memory Foam Pillow").

**Linear issue status** — pull the Picky Products backlog:

```
mcp__claude_ai_Linear__list_issues with project: "Picky Products"
```

Cross-reference against the Feedback Loop Tracker rows already in the file (search for `linear-id` spans) — update `linear-status` text and the verdict `badge` class (`good`/`warning`/`critical`/`neutral`) for any issue whose state changed. Add a new row for any newly-opened WAL issue tied to a recurring analytics finding; don't add rows for one-off Linear issues unrelated to a repeated flag (those belong in Linear only, not this table).

**Latest weekly report** — read the most recent `analytics/YYYY-Www.md` (excluding `_template.md`) for the Summary line (impressions, WoW delta, clicks, saves) and append its data point to the `sparkData` array in the gantt `<script>` block.

**Queue depth** — Candidate count from Products DB. Discovery auto-pauses while `Candidate + Processed > 2`; note whether the queue is still gated.

---

## Step 2 — Update `control-center.html`

The file is a flat HTML document — `<style>` block (fonts + CSS custom properties, static, don't touch), then body content, then a `<script>` block driving the sparkline and gantt SVGs. Edit the specific values, not the structure.

**Header** (`<div class="ts">Generated ...`) — today's date.

**KPI strip** (`section.kpi-strip`, 4 `.kpi-tile` blocks in order — Pin Runway, Queue Depth, Latest Report, Open Loops):
- Pin Runway: days from today to the last scheduled pin across all active products; sub-line gets the end date, product count, and total pin count (`products × 9`).
- Queue Depth: Candidate count; sub-line notes how long the oldest candidate has waited and whether discovery is gated.
- Latest Report: latest week's impressions; sub-line gets WoW %, clicks, saves. Tile `--stripe` color: `var(--good)` on a strong week, `var(--critical)` on a crash week, `var(--accent)` if flat/inconclusive.
- Open Loops: this tracks findings *without* a Linear issue (should stay `0` — every recurring finding gets a WAL issue). Sub-line summarizes what changed this run (issues closed, still open, pending verification).

**Feedback Loop Tracker** (`table.loop tbody`): update the `<h2>` count/week-range text, then patch each affected `<tr>` — `weeks-count` + `weeks-list` if flagged again, `linear-status`, and the verdict `badge` (swap the class and icon dot: `good` = closed/explained, `warning` = still open/tracked, `neutral` = fixed ad hoc with no Linear issue). Add new `<tr>` blocks for new ad-hoc fixes or new recurring findings, matching the existing markup pattern exactly (`--row-stripe` on the `<tr>` matches the badge tone).

**Pipeline Health** (`section` with `.health-row`, 3 `.health-card`):
- Daily Publisher: note any newly-diagnosed routing/sync issues.
- Discovery Engine: candidate count, gating status, which products still need `/process-product`.
- Notion DB Split: recompute the `.stack-seg` width percentages (`count / total * 100`, one decimal) for Candidate/Processed/Scheduled/Published, update the legend `<b>` counts, and the `aria-label` on `.stack-bar`. Update the summary line's product/pin totals.

**Pin Runway gantt** (`<script>` at the bottom):
- `products` array — one `{ name, start, end, done }` object per active product, chronological by start date.
- `today` — today's date string.
- `domainDays` — must cover from the chart's fixed domain start (`domainStart` in the script, currently `2026-07-07`) through the furthest product end date, plus a small margin. Recompute: `(furthest_end_date - domainStart).days + 1`.
- `weekTicks` / `weekLabels` — one tick every 7 days from 0 to `domainDays`; extend the arrays if the range grew.
- `todayLabel.textContent` — update the date shown on the dashed "today" marker.
- `sparkData` — append the latest week's impressions (see Step 1).

---

## Step 3 — Verify before shipping

`claude.ai` artifact previews don't scroll reliably for verification — always check via a local server instead, never trust a visual read of the raw HTML:

```bash
python3 -m http.server 8934 &
# navigate Chrome to http://localhost:8934/control-center.html, screenshot, scroll to check the gantt + health cards render correctly
kill %1   # or: pkill -f "http.server 8934"
```

Confirm: KPI numbers match Step 1's fresh pulls, the feedback loop table has no stale badges, the gantt bars land on the correct dates with the today-marker in the right place, and the Notion DB split bar segments visually match their percentages.

---

## Step 4 — Publish

**Local file:** already edited in place at `control-center.html` — no extra step needed beyond the commit below.

**Claude.ai artifact (optional, ask first):** this dashboard is also published as a claude.ai Artifact for easy sharing. If the user wants the hosted copy updated too, republish the same content via the `Artifact` tool with `url` set to the existing artifact URL (find it with `action: "list"` if not already known — title "Picky Products — Control Center"). The artifact tool wraps the file in its own `<!doctype>/<html>/<head>/<body>` skeleton, so pass it a version of the file **without** the outer `<html>`/`<head>`/`<body>` tags — strip the first two lines (`<!doctype html>`, `<html lang="en">`) and the `<head>`/`</head>`/`<body>`/`</body>`/`</html>` wrapper tags before publishing, keeping everything between `<meta charset...>` and the final `</script>`.

**Commit:**

```bash
git add control-center.html
git commit -m "Update Control Center dashboard"
git push
```

If a stale `.git/index.lock` or `.git/HEAD.lock` blocks the commit and no git process is actually running (`ps aux | grep git`), remove it and retry — same pattern as `/generate-pins`.

---

## Done

Report: what changed since the last snapshot (KPI deltas, issues closed/opened, products added to the runway), and the local file path. Mention the claude.ai artifact URL only if it was republished this run.
