# af CLI

Airflow REST wrapper from `astro-airflow-mcp`. Install with `uv tool install astro-airflow-mcp`, or run one-shot via `uvx --from astro-airflow-mcp af`. Otto bundles the same CLI.

Adapted from Astronomer's [airflow skill](https://github.com/astronomer/agents/blob/main/skills/airflow/SKILL.md). Verify flags with `af --help` before relying on memory.

## Config

Default file is `~/.astro/config.yaml` (`AF_CONFIG` overrides). Legacy `~/.af/config.yaml` still works; `af migrate` moves it (ask first).

```bash
af instance list
af instance use staging
AIRFLOW_API_URL=https://staging.example.com AIRFLOW_AUTH_TOKEN=$STG af dags list
```

Do not `af instance add --token "$TOKEN"` - that persists the secret in `~/.astro/config.yaml`. Use `${AIRFLOW_AUTH_TOKEN}` in YAML instead.

`af instance discover` creates Astro API tokens. Always `--dry-run` and get approval first.

Tokens in YAML may use `${VAR}`:

```yaml
instances:
- name: prod
  url: https://airflow.example.com
  auth:
    token: ${AIRFLOW_API_TOKEN}
```

## Commands

All commands print JSON except `instance` (tables). Pipe through `jq`.

| Command | Description |
|---------|-------------|
| `af health` | System health |
| `af dags list` | List DAGs |
| `af dags get <dag_id>` | DAG details |
| `af dags explore <dag_id>` | Metadata + tasks + source |
| `af dags source <dag_id>` | DAG source |
| `af dags pause / unpause <dag_id>` | Schedule on/off (write) |
| `af dags errors` | Import/parse errors |
| `af dags warnings` | DAG warnings |
| `af dags stats` | Run statistics |
| `af runs list` | DAG runs |
| `af runs get <dag_id> <run_id>` | One run |
| `af runs trigger <dag_id>` | Trigger (write) |
| `af runs trigger-wait <dag_id>` | Trigger and block (write) |
| `af runs delete <dag_id> <run_id>` | Delete run (write) |
| `af runs clear <dag_id> <run_id>` | Clear for re-run (write) |
| `af runs diagnose <dag_id> <run_id>` | Failed-run diagnosis |
| `af tasks list <dag_id>` | Tasks in DAG |
| `af tasks instance <dag_id> <run_id> <task_id>` | Task instance |
| `af tasks logs <dag_id> <run_id> <task_id>` | Task logs (`--try`, `--map-index`) |
| `af config version` | Airflow version |
| `af config connections` | Connections (filtered) |
| `af config variables` / `af config variable <key>` | Variables |
| `af config pools` / `af config pool <name>` | Pools |
| `af api <endpoint>` | Raw REST |
| `af api ls` / `af api ls --filter X` | Endpoint discovery |
| `af registry providers` | Provider registry |

Writes are opt-in. This skill stays read-only unless the user asks to mutate.

## `af api`

```bash
af api ls --filter xcom
af api dags -F limit=10 -F only_active=true
af api xcom-entries -F dag_id=X -F dag_run_id=Y -F task_id=Z
af api event-logs -F dag_id=X -F limit=50
af api dags/my_dag -X PATCH -F is_paused=false    # write
```

`-F` auto-converts types; `-f` keeps a string; `--body '{}'` for nested JSON.

## jq snippets

```bash
af runs list | jq '.dag_runs[] | select(.state == "failed")'
af dags list | jq '.dags[].dag_id'
af dags list | jq '[.dags[] | select(.is_paused == true)]'
```
