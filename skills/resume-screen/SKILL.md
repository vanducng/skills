---
name: resume-screen
description: "Screens a batch of operator-supplied resumes against a job description and writes a scored Excel workbook (knockouts, 100-point factors, overlays, logged-in fact-check). Use when screening resumes, scoring candidates against a JD, building a hiring scorecard, ranking applicants, or producing a candidate spreadsheet. Activates when the user says 'screen these resumes', 'score candidates against the JD', 'resume scorecard', 'rank these applicants', or 'build a hiring spreadsheet'. Role scorecards live as profiles (default data-platform-engineer). Fact-check composes vd:ego-browser or a named vd:browser-profile plus vd:agent-browser in connect mode — it does not reimplement a browser. Do not use for LinkedIn Recruiter sourcing, Google Drive download/upload, writing a JD, or browser-based file transfer."
license: MIT
argument-hint: "<jd-path> <resumes-dir-or-files> [--profile <id>] [--browser-profile <name>]"
metadata:
  author: vanducng
  version: "1.0.0"
---

# resume-screen

> Operator supplies a JD + resume files. Agent scores them against a **role profile** and writes an Excel workbook. No Drive, no Recruiter, no browser file transfer.

## What this skill is - and isn't

| Skill / activity | Question it answers | This skill? |
|---|---|---|
| **`vd:resume-screen`** (this) | "Given these files, who advances, and why?" | Yes — scored workbook |
| `vd:ego-browser` / `vd:browser-profile` + `vd:agent-browser` | "Open this logged-in page" | Composed for fact-check only — do not reimplement |
| Sourcing / LinkedIn Recruiter | "Who should we reach out to?" | No |
| Google Drive or browser file transfer | "Fetch or upload the packet" | No — operator already has the files |
| Writing or rewriting a JD | "What should this role say?" | No |
| HR screens (comp, hybrid, timezone, visa) | "Will the logistics work?" | No — never put these in `Screen_questions` |

Role-specific judgement lives in `references/profiles/`. The scoring engine, fact-check rules, and Excel shape are shared. Adding "Backend Engineer" is a new profile file plus one index row — not a fork of this skill.

## Inputs

| Input | Required | Notes |
|---|---|---|
| Job description | Yes | Local `.md` / `.txt` / `.pdf`, or pasted URL text the operator already captured |
| Resume files | Yes | A folder or an explicit list: `.pdf` / `.docx` / `.txt` / `.md` |
| Role profile | No | Default `data-platform-engineer`. Must be a row in `references/profiles/README.md` |
| Browser profile name | No | `--browser-profile <name>` for the `vd:browser-profile` fallback when ego-browser is not available. Operator is already logged into LinkedIn/GitHub in that Chrome. |

Resolve the skill root from the loaded `SKILL.md` path. Load, in order:

1. [`references/profiles/README.md`](references/profiles/README.md) — pick the profile id
2. `references/profiles/<id>.md` — role rubrics, knockouts, band, screen themes
3. [`references/scorecard.md`](references/scorecard.md) — shared engine (knockouts, 100-pt factors, overlays, tiers)
4. [`references/fact-check.md`](references/fact-check.md) — URL / cert / contradiction rules
5. [`references/output-spec.md`](references/output-spec.md) — Excel columns and formulas

Worked (fully fake) packet: [`examples/`](examples/README.md).

## Outputs

One `.xlsx` with sheets `Candidates` and `Scorecard`.

- Write to the injected `Reports:` path when the hook provides one. Otherwise use the operator's `--out` path, or `resume-screen-{date}-{profile}.xlsx` in the current working directory.
- `File` is a hyperlink to the **operator-provided** resume path or URL — never an extracted `.txt` basename.
- `Total` is an Excel formula (`=SUM(H{row}:N{row})` for the default seven factors), not a hardcoded number.
- `LinkedIn_URL` is a hyperlink only when a URL was extracted from the resume. Never invent a URL.

Do not commit real candidate files or a workbook that contains real PII.

## Hard rules

1. **Operator-supplied files only.** Do not download from Google Drive, scrape Recruiter, or use a browser to move files. If a file is missing, stop and ask.
2. **Never invent a URL.** Extract LinkedIn / GitHub / portfolio / blog / cert badge URLs from the resume. Open only those. Missing URL = Unverified, not a guess.
3. **Compose the two catalog browsers — do not reimplement one, do not invent a third driver.** Hard rules are copied in [`references/fact-check.md`](references/fact-check.md). Prefer `vd:ego-browser` (`skills/ego-browser/`). Else `vd:browser-profile` + `vd:agent-browser` connect (`profile-attach.sh`). Never `agent-browser --profile`. Never ask for a password.
4. **`Total` is a formula.** Use `scripts/write-scorecard.py`. A baked-in number will drift from the factor cells.
5. **Still score Out rows.** A knockout sets `Tier=Out` and fills `Knockouts`; the seven factors and overlays are still filled.
6. **Overlays do not rewrite `Total`.** Low startup fit may cap P1 → P2. A years-knockout plus High fit is a **waiver flag**, not a silent Out → P1 promotion.
7. **HR owns logistics.** Never put hybrid / timezone / salary / "does this band work" in `Screen_questions`. Location/hours is a factor and a knockout **only** when the resume clearly says they cannot meet the JD.
8. **Never ask for cert IDs.** Unverified SnowPro/AWS/Databricks → a *technical* question in `Cert_notes` or `Screen_questions`, not "show me the badge."
9. **Resume mills are not automatic Out.** Identical stack on every job or JD-copied bullets → `Claim_feasibility=Stretched` and `Startup_fit=Low`, unless employers/titles fail fact-check.
10. **No real hiring PII in this skill.** Examples stay fictional. Do not write real candidate names, LinkedIn slugs, or employer packets into `skills/resume-screen/`.

## Workflow

### 1. Scope

Confirm JD path, resume list, role profile id (default `data-platform-engineer`), and optional `--browser-profile <name>`. List resume files; skip non-resume junk. Print the profile title and the JD's must-haves (language, warehouse, years, hours/location, band) before scoring.

**Verify:** every resume path you will score is a file the operator gave you.

### 2. Extract

For each resume, pull a fact sheet: name, claimed titles, employers, dates, relevant years (data/platform/cloud engineering only), stack, location/hours statements, and every LinkedIn / GitHub / portfolio / blog / cert URL **verbatim**.

Analyst-only, QA-only, or Tableau-only time does not count toward the years knockout. Unknown location/hours is not a knockout.

**Verify:** every URL on the fact sheet appears in the resume text. No extras.

### 3. Fact-check

Do not reimplement a browser. Do not invent a third driver. Load [`references/fact-check.md`](references/fact-check.md) and the sibling `SKILL.md` you compose:

- Prefer **`vd:ego-browser`** (`skills/ego-browser/`) when ego lite / the `ego-browser` CLI is available.
- Else **`vd:browser-profile`** + **`vd:agent-browser`** (`skills/browser-profile/`, `skills/agent-browser/`) — `profile-attach.sh`, never `--profile`.
- Public badge URLs: HTTP fetch. If neither browser skill is runnable: public fetch; login-walled LinkedIn is `Unverified`. Do not invent profile content.

Record `Verified` / `Partial` / `Unverified` / `Contradicted` with the source URL. Certs are Verified only with a working badge URL or a clear LinkedIn Licenses listing. Missing Licenses is **not** a contradiction.

**Verify:** `Fact_check` is one of those four values, every opened URL was on the fact sheet, and `FactIntegrity_10` matches the verdict.

### 4. Score

Apply Layer 1 knockouts, then the seven Layer 2 factors, then overlays — all from the profile + [`references/scorecard.md`](references/scorecard.md). Assign `Tier` / `Decision` from the tier table. Write 3–5 technical `Screen_questions` only for P1, P2, and waiver rows.

**Verify:** a 75+ / Verified row is P1 unless an overlay capped it to P2. A Contradicted or knockout row is Out. Waiver rows stay Out and say so in `Waiver`.

### 5. Write the workbook

Sort: P1, P2, P3, waiver-Out, other Out; within a group, higher computed total first. Emit JSON (see `references/output-spec.md`) and run:

```bash
python3 "<skill-root>/scripts/write-scorecard.py" \
  --input /tmp/resume-screen-candidates.json \
  --out "<Reports-or-cwd>/resume-screen-YYYY-MM-DD-<profile>.xlsx"
```

**Verify:** unzip the xlsx (or re-run the script) and confirm `Total` cells contain `SUM(`, `File` cells contain `HYPERLINK(`, and the `Scorecard` sheet names the profile and weights. Open `examples/sample-scorecard.csv` if the column order is unclear.

## Anti-patterns

- Hardcoding one job's stack or a company's Drive folder into the skill.
- Treating "no LinkedIn" or "Licenses tab empty" as a contradiction.
- Putting location/comp questions in `Screen_questions`.
- Using the extracted text dump as the `File` value.
- Promoting a waiver candidate to P1 because the GitHub is strong.
- Inventing Credly/LinkedIn URLs so the sheet looks complete.
- Driving fact-check with `agent-browser --profile` (empty logins) or a homegrown Playwright/Puppeteer script.
- Asking the operator to paste a LinkedIn or GitHub password.
- Escalating every page to `vd:browser` (Browserbase) when the local profile would have worked.

## Rationalizations to catch

| Thought | Reality |
|---|---|
| "I'll grab the packet from Drive; it's faster." | Operator supplies files. Stop and ask. |
| "The cert is probably real; I'll mark Verified." | No badge URL and no public Licenses listing → Unverified. |
| "I'll just launch agent-browser --profile; it's simpler." | That browser has no saved LinkedIn/GitHub session. Attach to `vd:browser-profile` instead. |
| "Paste your LinkedIn password so I can log in." | Never. Operator logs in once in their Chrome or ego lite; we reuse that session. |
| "LinkedIn asked me to sign in, so the resume is fake." | Login wall without a browser session → Unverified, not Contradicted. |
| "Low startup fit should drop the score." | Cap the tier. Do not rewrite `Total`. |
| "They're in the wrong timezone — knockout." | Only if the resume *says* they cannot meet the JD. Otherwise score `Location_10` and leave it to HR. |
| "Same bullets at every employer — Out." | Mill pattern → Stretched / Low fit, not a knockout, unless fact-check breaks. |
