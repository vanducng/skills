# Output spec — Excel workbook

The workbook has exactly two sheets: `Candidates` and `Scorecard`.

Produce it with `scripts/write-scorecard.py`. The script writes `Total` as `=SUM(H{row}:N{row})` and `File` / `LinkedIn_URL` as `=HYPERLINK(...)`. Do not hand-type those cells.

## `Candidates` columns

Order is fixed for the default seven-factor engine. Do not insert columns before `FactIntegrity_10`.

| Col | Header | Type | Notes |
|---|---|---|---|
| A | `Rank` | int | 1..n after sort (P1, P2, P3, waiver-Out, other Out; then `Total` desc) |
| B | `Name` | text | From the resume. Examples in this skill are fictional |
| C | `File` | hyperlink | Operator-provided path or URL. Display text may be the basename. **Never** an extracted `.txt` name. The writer resolves relative paths against the `--out` directory (`--file-base`) so a demo packet uses `resumes/<name>.md` beside the xlsx |
| D | `Tier` | `P1` \| `P2` \| `P3` \| `Out` | After overlay caps |
| E | `Decision` | `Advance` \| `Maybe` \| `Hold` \| `Out` \| `Waiver candidate` | |
| F | `Total` | **formula** | `=SUM(H{row}:N{row})` — never a literal |
| G | `Knockouts` | text | Empty if none; else semicolon-separated reasons |
| H | `Pipelines_25` | number 0–25 | |
| I | `CoreStack_20` | number 0–20 | |
| J | `Cloud_15` | number 0–15 | |
| K | `Extras_10` | number 0–10 | |
| L | `Band_10` | number 0–10 | |
| M | `Location_10` | number 0–10 | |
| N | `FactIntegrity_10` | number 0–10 | |
| O | `Claim_feasibility` | `Credible` \| `Stretched` \| `Implausible` | |
| P | `Company_type` | `startup` \| `scaleup` \| `mid-market` \| `enterprise` \| `IT-services` \| `staffing/vendor` | |
| Q | `Startup_fit` | `High` \| `Medium` \| `Low` | Small / fast product-company fit |
| R | `Fit_decision` | text | e.g. `Cap P1 → P2` or `Holds` |
| S | `Timeline_gaps` | text | |
| T | `Timeline_consistency` | `Holds` \| `Soft mismatch` \| `Breaks` | |
| U | `Years_relevant` | number | |
| V | `Fact_check` | `Verified` \| `Partial` \| `Unverified` \| `Contradicted` | From the live page read; login wall without a session is Unverified |
| W | `Waiver` | text | `No` or `Yes — …` |
| X | `LinkedIn_URL` | hyperlink or empty | Only an extracted URL |
| Y | `GitHub_URL` | text/URL or empty | Extracted only |
| Z | `Portfolio_URL` | text/URL or empty | Extracted portfolio and/or blog URL |
| AA | `Certs_claimed` | text | |
| AB | `Certs_verified` | text | Include the source URL in the cell |
| AC | `Certs_unverified` | text | |
| AD | `Cert_notes` | text | Technical probe if claimed-only; never "show the badge" |
| AE | `Screen_questions` | text | 3–5; P1/P2/waiver only; no HR logistics |
| AF | `Notes` | text | Short rationale; include fact-check source URLs that are not already in X–Z / `Certs_verified` |

A future profile may rename the seven factor headers and reweight them (still summing to 100) via the JSON `factors` array. Column letters H–N stay the factor block; `Total` stays `=SUM(H:N)`.

## JSON input for `write-scorecard.py`

```json
{
  "profile": "data-platform-engineer",
  "jd": "path/or/label-of-the-jd",
  "candidates": [
    {
      "name": "Jordan Hale",
      "file": "/absolute/or/operator/path/jordan-hale.pdf",
      "tier": "P1",
      "decision": "Advance",
      "knockouts": "",
      "Pipelines_25": 22,
      "CoreStack_20": 18,
      "Cloud_15": 13,
      "Extras_10": 7,
      "Band_10": 9,
      "Location_10": 8,
      "FactIntegrity_10": 9,
      "claim_feasibility": "Credible",
      "company_type": "scaleup",
      "startup_fit": "High",
      "fit_decision": "Holds",
      "timeline_gaps": "None noted",
      "timeline_consistency": "Holds",
      "years_relevant": 4.5,
      "fact_check": "Verified",
      "waiver": "No",
      "linkedin_url": "https://example.com/in/jordan-hale",
      "github_url": "https://github.com/example/jordan-hale",
      "portfolio_url": "",
      "certs_claimed": "SnowPro Core",
      "certs_verified": "SnowPro Core — https://example.com/badges/snowpro-core-demo",
      "certs_unverified": "",
      "cert_notes": "",
      "screen_questions": "1) …; 2) …; 3) …",
      "notes": "4.5y DE; warehouse+dbt+Airflow; LI matches."
    }
  ]
}
```

Keys are case-insensitive for factor ids. Extra keys are ignored. `rank` and `total` in the JSON are ignored; the script assigns `Rank` and writes `Total` as a formula.

CSV is accepted (`--input *.csv`) with the same headers as the sheet (`Pipelines_25`, `LinkedIn_URL`, …). A `Total` column in the CSV is ignored.

## `Scorecard` sheet

Documentation, not scores. The script fills:

- Profile id
- JD label/path the operator supplied
- Generated timestamp (UTC)
- Factor table: id, max, one-line meaning
- Knockout list
- Tier rules
- Overlay reminder: they do not change `Total`
- Note that `File` points at the operator-provided resume, not an extracted text dump

## Checks before handing the file over

1. Open or unzip: every data row's `F` cell is a `SUM` formula over `H:N`.
2. `File` is a `HYPERLINK` to the path/URL the operator gave.
3. `LinkedIn_URL` is a `HYPERLINK` only when non-empty.
4. No P1 row has `Fact_check=Unverified` (that row is P2) or `Contradicted` (that row is Out).
5. Waiver rows are `Tier=Out`, `Decision=Waiver candidate`, and have screen questions.
6. Out-contradiction rows have empty `Screen_questions`.
7. `Screen_questions` contain no hybrid / timezone / salary / band-acceptance language.
8. Every non-empty LinkedIn/GitHub/portfolio/cert URL on the row was extracted from the resume (never invented). A login-walled LinkedIn without a browser session is `Unverified`, not `Contradicted`.
