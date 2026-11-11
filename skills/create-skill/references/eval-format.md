# Eval format

A skill's evals live in `<skill>/evals/<n>-<slug>/`, three or more of them.

| File | Purpose |
|---|---|
| `prompt.md` | The task, exactly as a user would give it. Put every instruction the run needs here: the harness loads no `AGENTS.md`, no extensions, no installed skills. |
| `fixture/` | Optional. Copied into a fresh temp directory; the run starts there. |
| `checks.sh` | Deterministic pass check, run in that directory after the agent finishes. Exit 0 = pass. No judge model. |
| `scenario.json` | Optional. `{"clean": true}` marks a case the skill must leave alone; `{"timeout": 600}` overrides the run limit; `{"needs_skills": ["other"]}` loads sibling skills by name (beside the skill under test; a path is refused) in every variant, so the baseline drops only the skill under test. |

`checks.sh` gets these environment variables:

- `EVAL_OUTPUT`: a file holding the agent's final text.
- `EVAL_ORIG`: a pristine copy of the fixture, to compare against (empty directory when there is no fixture).

Write checks that fail on the base model's usual behavior and pass only when the skill did its job: a file exists, a count is within a limit, a command exits 0, a tree is unchanged. A clean case asserts that nothing changed, or that the agent declined.

## Running

```bash
python3 scripts/run_evals.py <skill-dir> --model cpa/grok-4.7 --model cpa/claude-sonnet-5-5 --runs 3
python3 scripts/run_evals.py <skill-dir> --before <old-skill-dir> --after <new-skill-dir> --model <m> --runs 3
```

- Default variants are `with` (the skill loaded) and `without` (a baseline with no skill). A non-clean scenario that passes without the skill is flagged `too easy`.
- `--before/--after` runs two versions of a skill under random labels X and Y, scores them, then prints the key. The edit wins only when `after` gains at least `--margin` passes (default 2) and fails no clean case that `before` passed.
- `--runtime pi` is the only adapter so far (Claude Code and Codex adapters are a follow-up). Skills are loaded with `--skill`; installed skills, context files, extensions and MCP are switched off so a run sees only the skill under test.
- Run artifacts (agent output, check output, the results JSON) go to `--out-dir`; keep the JSON as the evidence and record its sha256. In before/after mode the JSON also holds the blind key, the seed, the margin, both paths and the verdict, so it resolves X and Y without stdout.

`checks.sh` is run, not sandboxed: it inherits only `PATH`, `HOME`, `TMPDIR`, `LANG` and `LC_ALL`, but it can still touch the filesystem. Run only evals from a repository you have reviewed, as you would a test suite.

Use the cheapest model first, one family per round, and small N (3). A run costs quota: do not rerun a green round.
