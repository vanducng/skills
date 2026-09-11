# External Scouting - Gemini / OpenCode CLI

Use external CLIs for **large-context** scouts (1M+ token windows). Faster than Explore subagents when SCALE is small (1-5) and the target dirs are large.

## Tool selection

```
SCALE 1-3   → gemini CLI
SCALE 4-5   → opencode CLI
SCALE ≥ 6   → fall back to internal scouting (references/internal-scouting.md)
```

## Configuration

Read from env (no per-user config files):

```bash
GEMINI_MODEL=${GEMINI_MODEL:-gemini-3-flash-preview}
OPENCODE_MODEL=${OPENCODE_MODEL:-opencode/grok-code}
```

## Timeout wrapper

Resolve once per session - stock macOS has no `timeout`; Homebrew coreutils ships it as `gtimeout`:

```bash
TO=$(command -v gtimeout || command -v timeout)   # empty on a box with neither
```

When `TO` is empty, run the call bare and rely on the agent-level 3-minute timeout.

## Install check

```bash
which gemini    # gemini CLI
which opencode  # opencode CLI
```

If missing:
1. Ask the user whether to install (manual auth may be needed for gemini), OR
2. Fall back to **internal scouting** without asking when the user clearly wants results now

## Gemini (SCALE 1-3)

The query is positional - `--prompt` is deprecated and will be removed upstream.

```bash
"$TO" 120 gemini -y -m "${GEMINI_MODEL:-gemini-3-flash-preview}" \
  "[scout prompt]" 2>&1
```

Example:

```bash
"$TO" 120 gemini -y -m gemini-3-flash-preview \
  "Search src/ for authentication-related files. List paths with one-line descriptions." 2>&1
```

## OpenCode (SCALE 4-5)

```bash
opencode run "[scout-prompt]" --model "${OPENCODE_MODEL:-opencode/grok-code}"
```

Example:

```bash
opencode run "Find all payment-related files in lib/ and api/" --model opencode/grok-code
```

## Spawning parallel Bash agents

Use `Task` tool with `subagent_type: "Bash"` - spawn all in **one** message:

```
Task 1: subagent_type="Bash",
  prompt="$TO 120 gemini -y -m ${GEMINI_MODEL:-gemini-3-flash-preview} 'Scout dags/ for DAGs touching payments_raw' 2>&1"

Task 2: subagent_type="Bash",
  prompt="$TO 120 gemini -y -m ${GEMINI_MODEL:-gemini-3-flash-preview} 'Scout models/ for dbt sources/exposures referencing payments_raw' 2>&1"

Task 3: subagent_type="Bash",
  prompt="$TO 120 gemini -y -m ${GEMINI_MODEL:-gemini-3-flash-preview} 'Scout lightdash/, dashboards/ for charts using payments' 2>&1"
```

## Prompt guidelines

- Name the dir scope explicitly - don't say "search the codebase"
- Ask for **paths + one-line descriptions** - not file contents
- State the search target precisely (file pattern, function name, env var, dbt model name)
- Ask for patterns/relationships only when relevant (e.g. "report which DAG triggers which model")

## Domain examples

### Data engineering

```bash
"$TO" 120 gemini -y -m gemini-3-flash-preview \
  "Scout dbt project. List: (1) sources defined in schema.yml referencing 'payments', (2) staging/intermediate/marts models that depend on those sources, (3) tests covering them, (4) exposures pointing to BI. Path + one-liner per item." 2>&1
```

### DevOps / multi-env

```bash
"$TO" 120 gemini -y -m gemini-3-flash-preview \
  "Scout infra repo. Find every place 'DATABASE_URL' is set or referenced: terraform/ outputs, k8s/ manifests + ConfigMaps + Secrets, helm/ values per environment, .github/workflows/ env injection, .sops.yaml encrypted entries. Path + line + which env (dev/staging/prod)." 2>&1
```

### Analytics

```bash
opencode run "Scout this repo for the metric 'monthly_active_users'. List: dbt model that defines it, schema.yml exposure, Lightdash YAML referencing it, dashboards that chart it, scheduled exports that include it. Path + brief context per item." --model opencode/grok-code
```

## Error handling

Wrap every gemini call with the resolved timeout wrapper (`"$TO" 120 ... 2>&1`; bare when `TO` is empty) and check:

- **Exit code ≠ 0** → failure
- **Output contains** `GaxiosError`, `RESOURCE_EXHAUSTED`, `MODEL_CAPACITY_EXHAUSTED`, `PERMISSION_DENIED`, `UNAUTHENTICATED` → failure
- On failure: skip that agent's result. **Do not retry** the same call.
- On 2+ agent failures: fall back to internal scouting.
- On 429 with `gemini-3-flash-preview`: try `gemini-2.5-flash` once before giving up.

## Reading file content (when needed after scouting)

Same chunking rules as internal scouting - see `references/internal-scouting.md` § "Reading file content".
