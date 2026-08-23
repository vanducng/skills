---
name: dag-factory
description: "Author Airflow DAGs from dag-factory YAML. Use when creating or editing YAML DAG configs, loaders, callbacks, custom operators in YAML, dynamic mapping, datasets, or validating dag-factory files. Covers both map-style tasks (task_id as YAML key) used by in-repo plugins and the PyPI dag-factory v1 list format. Not for remote run/log inspection (vd:astro-airflow) or local astro dev lifecycle (vd:managing-astro-local-env)."
license: MIT
metadata:
  author: vanducng
  version: "0.1.0"
  upstream: "https://github.com/astronomer/agents/tree/main/skills/dag-factory"
---

# dag-factory

Declarative Airflow DAGs from YAML. Detect the repo's dialect **before** writing YAML. Official Astronomer skill targets PyPI `dag-factory` v1+ (list-format `tasks`). Many production repos still use a vendored plugin and **map-format** `tasks` keyed by `task_id`. Mixing the two breaks parse.

## 1. Detect dialect

```bash
rg -n "load_yaml_dags|from dagfactory|from plugins.dagfactory" --glob '*.py' dags plugins | head
rg -n "^  tasks:" -g '*.yaml' -g '*.yml' -A 6 | head -40
```

| Signal | Dialect |
|---|---|
| `from plugins.dagfactory import load_yaml_dags` (or similar in-repo plugin) | **map** - `tasks.<task_id>.operator` |
| `from dagfactory import load_yaml_dags` + `dag-factory>=1` in deps | **list** - `tasks: [{task_id, operator}]` |
| `tasks:` then a nested key that is a task id, not `- task_id:` | **map** |
| `tasks:` then `- task_id:` | **list** |

Match neighboring YAML in the same folder. Do not "modernize" map-format files to list-format unless the user asks and the loader is PyPI v1+.

Keep `from airflow import DAG` in every loader module even if it looks unused. The DAG processor requires it.

## 2. Loader

Map-style in-repo plugin (typical):

```python
from airflow import DAG
from plugins.dagfactory import load_yaml_dags

load_yaml_dags(globals_dict=globals(), dags_folder=".../configs")
```

PyPI v1:

```python
from airflow import DAG
from dagfactory import load_yaml_dags

load_yaml_dags(globals_dict=globals(), dags_folder="/usr/local/airflow/dags")
```

`globals_dict=globals()` is required.

## 3. YAML shape

### Map format (in-repo / pre-1.0)

```yaml
default:
  default_args:
    owner: data-team
    retries: 3
    retry_delay_sec: 180
    on_failure_callback: package.callbacks.task_failed
  on_failure_callback: package.callbacks.dag_failed
  catchup: false

elt_source_object:
  schedule: 0 2 * * *
  max_active_runs: 1
  params:
    stg_database: AIRFLOW_VARIABLE__source/stg_database
  tasks:
    extract:
      operator: package.operators.extract.ExtractOperator
      http_conn: source_conn
    load:
      operator: package.operators.load.LoadOperator
      dependencies:
        - extract
```

Task id = YAML key. `dependencies` is a list of upstream task ids (not `>>`).

### List format (PyPI v1+)

```yaml
default:
  default_args:
    start_date: 2025-01-01

elt_source_object:
  schedule: 0 2 * * *
  catchup: false
  tasks:
    - task_id: extract
      operator: airflow.providers.standard.operators.empty.EmptyOperator
    - task_id: load
      operator: airflow.providers.standard.operators.empty.EmptyOperator
      dependencies: [extract]
```

## 4. Hard rules

- **Full operator import path.** `airflow.providers.standard.operators.python.PythonOperator`, not a short name. Airflow 3: prefer `airflow.providers.*` over `airflow.operators.*`.
- **Callbacks are string paths** that the factory imports. Two layers: task `default_args.on_failure_callback` (after retries) plus DAG `on_failure_callback` (run summary). DAG-level does **not** fire on each failed task.
- **Do not add `on_retry_callback`** unless the user asks. Retries are expected.
- **Params** may use an `AIRFLOW_VARIABLE__` prefix when the factory resolves Airflow Variables at parse/runtime. Copy the prefix from sibling YAML; do not invent it.
- **Custom operators** live in Python (`plugins/operators/` or equivalent). YAML only references them. New reusable logic → operator + YAML task, not a one-off Python DAG.
- **Python callables** in YAML: `python_callable_file` + `python_callable_name` (absolute path inside the image, usually `/usr/local/airflow/dags/...`).
- **`max_active_runs: 1`** means a manual trigger can sit queued behind a scheduled run.

## 5. Validate

Prefer parse over hoping the UI will show the DAG:

```bash
astro dev parse
```

If the repo wraps Airflow CLI:

```bash
# only if these targets exist
make dags-import-errors
make airflow CMD='dags list'
```

Broken YAML = import error, not a runtime task failure. Fix the YAML/loader, then re-parse.

PyPI v1 also ships `dagfactory convert` (Airflow 2 YAML → 3 operator paths). Do not run convert on map-format in-repo YAML.

## 6. New DAG checklist

1. Read one sibling YAML in the same source folder and copy structure.
2. DAG id: `[job_type]_[source]_[object]` if the repo already uses that pattern (`elt_`, `mon_`, `mnt_`, `rpt_`, ...).
3. Loader `dag.py` in the source folder; YAML under `configs/`.
4. Both callback layers + `catchup: false` unless backfill is the point.
5. `astro dev parse` clean before claiming done.

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| DAG missing in UI | YAML syntax, bad operator path, missing `from airflow import DAG` | `astro dev parse` / import-errors |
| `cannot import name 'SUPERVISOR_COMMS'` | `Variable.get()` at parse time on Airflow 3 | Do not call `Variable.get` in loader; use `AIRFLOW_VARIABLE__` params or try/except fallback |
| Task never runs | wrong `dependencies` key vs list-format `task_id` | Match file dialect |
| Callback import error | dotted path not importable in the image | Use the same prefix as sibling YAML |
| Official v1 examples fail to parse | list-format YAML in a map-format factory | Rewrite as map keys |

## Related

- Remote runs/logs: `vd:astro-airflow`
- Local `astro dev`: `vd:managing-astro-local-env`
- Otto: `vd:delegating-to-otto`
- Upstream v1 reference: https://github.com/astronomer/dag-factory
- Official skill (list-format): https://github.com/astronomer/agents/blob/main/skills/dag-factory/SKILL.md
