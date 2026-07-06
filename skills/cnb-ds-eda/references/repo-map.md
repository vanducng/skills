# Repo Map

Main repo:

```text
/Users/vanducng/git/work/cnb/cnb-ds-eda
```

Common paths:

```text
notebooks/
notebooks/<topic>/<number>-<slug>.ipynb
notebooks/<topic>/README.md
notebooks/<topic>/queries/*.sql
notebooks/<topic>/snapshots/*.tsv
src/connectors/snowflake.py
src/utils/config.py
tests/
```

Useful examples:

```text
notebooks/rnd_disconnection_status/01-rnd-reassignment-analysis.ipynb
notebooks/lead_age_performance/01-answer-rate-by-lead-age.ipynb
notebooks/retellai_alert/transfer-ai-intelliapp-dashboard.ipynb
notebooks/scheduled_call_qualification/01-scheduled-callback-qualification-recheck.ipynb
```

Validation commands:

```bash
jq empty notebooks/<topic>/<notebook>.ipynb
.venv/bin/jupyter nbconvert --to notebook --execute --inplace notebooks/<topic>/<notebook>.ipynb
.venv/bin/jupyter nbconvert --to html notebooks/<topic>/<notebook>.ipynb --output /tmp/<report>.html
uv run --extra dev pytest
mise run lint
```

`mise run lint` may format unrelated `src/analysis/*.py` files. Check `git status` after lint and restore unrelated formatter-only side effects unless they are part of the requested change.

Use `query_snowflake(sql)` from `src/connectors/snowflake.py` in notebook live-refresh paths:

```python
from connectors.snowflake import query_snowflake
df = query_snowflake(read_query("some_query"))
```
