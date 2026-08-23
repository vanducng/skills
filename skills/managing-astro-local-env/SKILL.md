---
name: managing-astro-local-env
description: "Manage a local Astronomer/Airflow environment with Astro CLI. Use when the user says astro dev start/stop/restart, local scheduler, astro dev parse, astro dev pytest, local task logs, localhost Airflow UI, or Makefile wrappers like make airflow / make scheduler-restart. Not for staging/prod inspection (vd:astro-airflow) and not for YAML DAG authoring (vd:dag-factory)."
license: MIT
metadata:
  author: vanducng
  version: "0.1.0"
  upstream: "https://github.com/astronomer/agents/tree/main/skills/managing-astro-local-env"
---

# managing-astro-local-env

Local Airflow via Astro CLI. Docker mode is the default. Do not assume port 8080 - read the project config.

## Port and credentials

```bash
astro config get          # webserver port, postgres port, mode
astro dev ps
```

Check `.astro/config.yaml` and `airflow_settings.yaml` for the UI port. Default credentials are `admin` / `admin` unless the project overrides them.

## Lifecycle

```bash
astro dev start                 # UI on the configured port
astro dev stop                  # keep volumes
astro dev kill                  # wipe volumes
astro dev restart
astro dev restart --scheduler   # faster than full restart after DAG edits
astro dev parse                 # import errors without waiting for the scheduler
astro dev pytest
astro dev logs --scheduler
astro dev logs -f
astro dev bash
astro dev run airflow dags list
```

Restart after `requirements.txt`, `packages.txt`, or `Dockerfile` changes (`kill` then `start` if packages fail to install).

If the repo Makefile already wraps these, prefer the target that exists (`airflow`, `scheduler-restart`, `dags-import-errors`, `dags-reparse`). Do not invent Make targets.

## Local API

Prefer a configured `af` instance named `local` (see `vd:astro-airflow`). Otherwise:

```bash
# Astro CLI (local only) - operation ids, not raw paths
astro api airflow ls
astro api airflow get_import_errors
astro api airflow get_dags -q '.dags[].dag_id'
astro api airflow get_dag_runs -p dag_id=<dag_id>
```

`astro api airflow` defaults to localhost + admin/admin. Override with `--api-url` / `--username` / `--password` when the project is not on 8080.

For remote staging/prod, stop using this skill and use `vd:astro-airflow`.

## Parse loop (new or edited DAG)

```bash
astro dev parse
# or: make dags-import-errors
```

YAML/loader errors show up here, not as a failed task. After parse is clean, unpause before the first trigger.

## Troubleshooting

| Issue | Fix |
|---|---|
| Port in use | `astro config get`; stop the other stack or change the project port |
| DAG missing | `astro dev parse`; missing `from airflow import DAG` in the loader |
| Scheduler not picking up YAML | `astro dev restart --scheduler` or the repo's reparse target |
| Package install failed | requirements syntax; then `astro dev kill && astro dev start` |
| Disk full | `docker system prune` |
| `Variable.get` ImportError at parse | Airflow 3 parse isolation; wrap or use YAML `AIRFLOW_VARIABLE__` params |

## Standalone / proxy (only if the user asks)

`astro dev start --standalone` needs Airflow 3 + `uv`, no Docker. Pass `--standalone` on every follow-up command unless `astro config set dev.mode standalone`. Reverse proxy: `astro dev proxy status` (default 6563) for multiple local projects.

## Related

- Remote Astro: `vd:astro-airflow`
- YAML DAGs: `vd:dag-factory`
- Otto: `vd:delegating-to-otto`
- Upstream: https://github.com/astronomer/agents/blob/main/skills/managing-astro-local-env/SKILL.md
