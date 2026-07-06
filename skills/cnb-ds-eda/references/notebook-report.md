# Notebook Report Standards

GitHub review is a first-class output. A notebook is not ready if GitHub shows only raw code and no executed tables/charts.

## Structure

Use this order:

1. Title, objective, snapshot timestamp, and exact date range.
2. Table of contents.
3. Method, definitions, and data sources.
4. Imports and path setup.
5. Query/snapshot loading.
6. Executive summary.
7. Root logic and detection rules.
8. Trend, concentration, distribution, and sample evidence.
9. Conclusion, fix direction, and refresh instructions.

## Code Cells

Keep cells short and readable. Put long SQL in `queries/*.sql`. Put offline data in `snapshots/*.tsv`; never paste large TSV payloads into code cells.

Use a project-root finder so the notebook works from both repo root and notebook directory:

```python
def find_project_root(start: Path) -> Path:
    for path in [start, *start.parents]:
        if (path / "src" / "connectors" / "snowflake.py").exists():
            return path
    raise FileNotFoundError("Could not find project root")
```

For Plotly GitHub rendering:

```python
import plotly.io as pio
pio.renderers.default = "png"
pio.renderers["png"].width = 1200
pio.renderers["png"].height = 600
```

## Snapshot Pattern

Use `RUN_LIVE = False` by default so GitHub-rendered reports are stable. When `RUN_LIVE = True`, load each SQL file through `query_snowflake()`. When `RUN_LIVE = False`, load committed TSV snapshots with `pd.read_csv(..., sep="\t")`.

After changing report logic, refresh snapshots from live data, execute in-place, and confirm the notebook has output payloads:

```bash
jq '[.cells[] | select(.cell_type=="code") | (.outputs // []) | length] | add' <notebook>
jq -r '.cells[] | select(.cell_type=="code") | (.outputs // [])[] | if .data then (.data | keys[]) else .output_type end' <notebook> | sort | uniq -c
```
