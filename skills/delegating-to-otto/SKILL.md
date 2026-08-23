---
name: delegating-to-otto
description: "Drive Astronomer's Otto agent (`astro otto`) as a delegated sub-agent for Airflow, dbt, and data-engineering work. Use when the user says 'use Otto', 'ask Otto', 'delegate to Otto', or 'run this through Otto'. Also offer Otto for Airflow 2→3 migrations even when not named. Covers headless invocation, session continuity, permission modes, tool allowlists, model/provider selection, and structured output. Do not load this skill if you are Otto."
license: MIT
metadata:
  author: vanducng
  version: "0.1.0"
  upstream: "https://github.com/astronomer/agents/tree/main/skills/delegating-to-otto"
---

# Delegating to Otto

[Otto](https://www.astronomer.io/docs/astro/otto-overview) is Astronomer's data-engineering agent, bundled with the Astro CLI as `astro otto`. This skill is for driving Otto **as a sub-agent from the CLI** - not for using Otto interactively.

> **If you are Otto, stop here.** Otto already bundles Astronomer's Airflow skills. Never spawn `astro otto` from inside Otto.

Routine staging/prod inspection in *this* catalog stays on `vd:astro-airflow` (`af` / `astro deployment` / curl). Use this skill when the user names Otto, for Airflow 2→3 upgrade planning, or for a long self-contained audit that would burn parent context.

## When to delegate

**Do:**

- Airflow upgrades / runtime / provider compatibility (Otto's compatibility KB)
- Live production diagnosis that should run in its own session
- Long audits, fleet-wide DAG analysis
- Parallel branches via `--fork`
- Tasks that should inherit `.astro/memory/`

**Don't:**

- Small single-tool lookups (`af dags errors`, one task log) - do those in `vd:astro-airflow`
- Work that depends on parent conversation or in-flight todos
- `af` against a connected Airflow when none is running and starting one is wrong

If the user asks about an Airflow 2→3 upgrade without naming Otto, offer to run it through Otto first.

## Verify Otto

Needs Astro CLI ≥ 1.42 (`brew upgrade astro` if `astro otto` is missing).

```bash
astro version
astro otto version
astro otto --help
astro otto --list-models astronomer
```

Otto auto-updates (once per day). Opt out: `astro config set -g otto.auto_update false`.

## Provider and model (verified)

`~/.astro/otto/settings.json` can set `defaultProvider` to a **personal** key (`anthropic`, `openai`). Passing only `--model gpt-5.4-mini` then pairs the model with that provider and fails with the user's own billing (`You have no credits remaining`).

For delegated runs, **always pass both**:

```bash
astro otto --list-models astronomer          # live IDs; do not hardcode forever
astro otto --provider astronomer-openai --model gpt-5.4-mini --mode text "..."
astro otto --provider astronomer-anthropic --model claude-haiku-4-5 --mode text "..."
```

`astronomer-*` providers bill through the Astro gateway (requires `astro login`). Bare `anthropic` / `openai` use the user's API keys.

For planning / migrations pick a 1M-context model and `--thinking medium` or `high`. For smoke tests use a mini/haiku model and `--thinking off` or `low`.

## Headless invocation

```bash
# Safest one-shot: read-only, no session on disk
astro otto --mode text --no-stream --permission-mode plan --no-session \
  --provider astronomer-openai --model gpt-5.4-mini \
  --thinking low \
  "your prompt"

# Narrow tools
astro otto --mode text --permission-mode plan --allowed-tools af,read,grep \
  --provider astronomer-openai --model gpt-5.4-mini \
  "diagnose why <dag_id> failed yesterday"
```

`--mode text` still prints JSONL bootstrap lines (`{"level":30,...}`) around the answer when stdout is not a TTY. Read the non-JSON line(s) as the result, or use `--mode json` and parse the final event.

`--mode json` + `--output-schema @schema.json` forces structured output (exits 4 if missing).

## Session control

| Flag | Behavior |
|---|---|
| `-c`, `--continue` | Resume most recent session in this directory |
| `--session <id\|path>` | Open a specific session |
| `--fork <id\|path>` | Copy history into a new session |
| `--no-session` | In-memory only |
| `--export <id\|path>` | Render a session to HTML and exit |

Prefer `-c` / `--session` over re-prompting from scratch.

## Permission modes

| Mode | Behavior |
|---|---|
| `plan` | Read-only sandbox. Blocks `edit`/`write`. Restricts `bash` to a read-only allowlist. Default for audits. |
| `default` | Prompts on destructive `astro`/`af` |
| `acceptEdits` | Auto-allows `edit`/`write` inside the project |
| `confirmEdits` | Prompt before every edit/write |
| `bypassPermissions` | Allows almost everything; still blocked from `.env*`, `~/.ssh/**`, out-of-project writes, `astro deploy`, `af runs delete`, etc. |

Do not pass `--skip-permissions` unless the user explicitly asks.

## What Otto auto-detects

Launched from an Astro project, Otto sets `ASTRO_TOKEN` / org from `astro login`, and local `AIRFLOW_API_URL` if `astro dev start` is running. It loads `AGENTS.md` / `CLAUDE.md` walking up from cwd (`AGENTS.md` wins when both exist).

**`af` still needs a reachable Airflow.** If boot logs show `"airflowURL":null` and no remote `af instance`, Otto can read DAG code but cannot inspect runs or task logs. Fix: `astro dev start`, or configure a remote instance (`vd:astro-airflow`), then rerun.

## Patterns

Plan-only investigation:

```bash
astro otto --mode text --no-stream --permission-mode plan --thinking medium \
  --provider astronomer-openai --model gpt-5.5 \
  --allowed-tools af,read,grep,bash \
  "Investigate <dag_id> on the current Astro project. Return: failed run ids, failed tasks, likely cause, next check. Do not edit files."
```

Scripted JSON:

```bash
astro otto --mode json --output-schema @schema.json \
  --permission-mode plan --allowed-tools af,read \
  --provider astronomer-openai --model gpt-5.4-mini \
  "find DAGs with import errors" \
  | jq '.final_answer'
```

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `astro otto`: command not found | Astro CLI < 1.42 | `brew upgrade astro` then `astro otto update` |
| `You have no credits remaining` | `--model` paired with personal `anthropic`/`openai` (see settings.json) | Pass `--provider astronomer-openai` or `astronomer-anthropic` |
| JSONL only, no answer | one-shot still booting / crashed after skill cache | Check the last `Session shutting down` reason; retry with `--no-stream` |
| Otto cannot run `af` | `airflowURL` null, no instance | Start local Airflow or add a remote `af` instance |
| Recursive Otto | this skill loaded inside Otto | Ignore this skill; do the work directly |

## Authoritative references

- `astro otto --help` - flag source of truth
- [Otto overview](https://www.astronomer.io/docs/astro/otto-overview)
- [`astro otto` CLI](https://www.astronomer.io/docs/astro/cli/astro-otto)
- Upstream skill: https://github.com/astronomer/agents/blob/main/skills/delegating-to-otto/SKILL.md
- Sibling for direct Astro/Airflow inspection: `vd:astro-airflow`
