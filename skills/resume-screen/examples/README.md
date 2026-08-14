# Examples (fully fictional)

These files exist so an agent can see the *shape* of a screen. They are not a real hiring packet.

**Do not copy real candidate names, LinkedIn slugs, Drive IDs, or employer packets into this folder.**

| File | What it is |
|---|---|
| [`sample-jd.md`](sample-jd.md) | Generic mid-level Data Platform Engineer JD at a mid-size product company |
| [`resumes/`](resumes/) | Four tiny fictional resumes (P1, P1→P2 cap, Out-contradiction, years-waiver) |
| [`sample-candidates.md`](sample-candidates.md) | How those four score against the DPE profile |
| [`scored-candidates.json`](scored-candidates.json) | Same scores, writer input |
| [`sample-scorecard.csv`](sample-scorecard.csv) | Same columns as the Excel spec; `Total` is `=SUM(H{row}:N{row})` |
| [`sample-scorecard.xlsx`](sample-scorecard.xlsx) | Generated workbook (`Candidates` + `Scorecard`) |

Rebuild the demo workbook from the scored JSON:

```bash
python3 ../scripts/write-scorecard.py \
  --input scored-candidates.json \
  --profile data-platform-engineer \
  --jd sample-jd.md \
  --out sample-scorecard.xlsx \
  --check
```

Assertions (formulas, columns, archetypes, no PII, browser-routing contract):

```bash
python3 ../scripts/test_example_screen.py
python3 ../scripts/test_write_scorecard.py
```

All people, URLs, and employers are invented. `example.com` / `github.com/example/` links are placeholders — a real screen would only include URLs that appeared on a resume, and would open them by composing `vd:ego-browser` or `vd:browser-profile` + `vd:agent-browser` (see `references/fact-check.md`). Never invent a URL or a third driver.

This packet does **not** run a live browser. If `vd:ego-browser` / `vd:agent-browser` are unavailable, follow the fallback in `fact-check.md` (public fetch; login-walled LinkedIn is `Unverified`).
