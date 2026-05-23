---
name: bye
description: |
  Session-close routine for Picky Products. Reviews the session for corrections,
  feedback, or improvements to skill outputs, then patches the relevant skill
  SKILL.md files so future sessions benefit. Run at the end of every working session.
license: MIT
compatibility: claude-code
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - mcp__notion__API-patch-page
---

# bye

Session-close routine. Reviews what happened, finds anything that needed correcting or could be improved, and updates the relevant skills so the next session starts better than this one.

## When to run

At the end of every working session — after tasks are done, before closing.

---

## Step 1 — Review the session

Look back over the conversation and identify:

- Any correction to a skill's output (copy rewritten, fields changed, dates adjusted)
- Any step the skill got wrong or had to be overridden
- Any workaround that had to be applied (e.g. a field name was wrong, a Notion filter failed)
- Any rule that was applied but isn't yet in the skill
- Any friction that could be removed with a better instruction

Focus on what would have made this session run faster or cleaner if it had been in the skill from the start.

---

## Step 2 — Map findings to skills

For each finding, identify which skill file it belongs to:

- Copy quality, angle selection, hook text → `process-product`
- Notion field names, DB IDs, record creation → `process-product`
- Scheduling logic, date handling, timestamps → `process-product`
- Image generation, file naming, Notion status update → `generate-pins`
- General project rules that apply to both → update both

Skill files live at:
- `/Users/mariojorquera/Documents/Claude/Projects/Picky Products/.claude/skills/process-product/SKILL.md`
- `/Users/mariojorquera/Documents/Claude/Projects/Picky Products/.claude/skills/generate-pins/SKILL.md`

---

## Step 3 — Apply updates

For each finding, make a targeted edit to the relevant skill using the Edit tool.

**Guidelines for edits:**
- Add missing rules where a gap caused a problem
- Sharpen ambiguous instructions where judgement calls went wrong
- Fix incorrect field names, IDs, or format examples
- Remove instructions that turned out to be wrong
- Keep skill files concise — don't pad, don't over-document

If nothing needs changing in a skill, say so explicitly rather than making cosmetic edits.

---

## Step 4 — Check CLAUDE.md for needed updates

Review `/Users/mariojorquera/Documents/Claude/Projects/Picky Products/CLAUDE.md` against the session. Update it if any of these changed:

- Project facts that are now stale (e.g. affiliate tag, PA API status, tool setup)
- Workflow steps that were corrected during the session
- Agent instructions that led to wrong output

Don't add commentary or summaries — CLAUDE.md is reference documentation, not a log.

---

## Step 5 — Commit and push

If any skill files or CLAUDE.md were edited, commit and push:

```bash
git add .claude/skills/ CLAUDE.md
git commit -m "bye: update skills from session [YYYY-MM-DD]"
git push
```

If nothing was changed, skip this step.

---

## Step 6 — Report

Give a brief summary:

- Which skills were updated and why (one line each)
- Whether CLAUDE.md was updated and why
- Any learning worth flagging for future sessions that doesn't fit in a skill (e.g. a one-off infrastructure issue)

Keep it short — this is a log, not a debrief.
