# Examples (fully fictional)

These files exist so an agent can see the *shape* of a screen. They are not a real hiring packet.

**Do not copy real candidate names, LinkedIn slugs, Drive IDs, or employer packets into this folder.**

| File | What it is |
|---|---|
| [`sample-jd.md`](sample-jd.md) | Generic mid-level Data Platform Engineer JD at a mid-size product company |
| [`sample-candidates.md`](sample-candidates.md) | Four anonymized archetypes: P1, P1→P2 cap, Out-contradiction, years-waiver |
| [`sample-scorecard.csv`](sample-scorecard.csv) | Same columns as the Excel spec; `Total` is `=SUM(H{row}:N{row})` |

Rebuild a demo workbook (writes next to the CSV unless `--out` is set):

```bash
python3 ../scripts/write-scorecard.py \
  --input sample-scorecard.csv \
  --profile data-platform-engineer \
  --jd sample-jd.md \
  --out /tmp/resume-screen-sample.xlsx
```

All people, URLs, and employers below are invented. `example.com` / `github.com/example/` links are placeholders — a real screen would only include URLs that appeared on a resume.
