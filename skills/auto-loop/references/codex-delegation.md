# Codex /goal delegation

`vd:auto-loop --codex` is an **opt-in escape hatch** that hands the goal to native
Codex `/goal` instead of running the in-house loop. Use it when (a) you have a
ChatGPT subscription with Codex access, (b) you trust Codex's structured-state
contract, and (c) you want Codex's pause/resume UX over the in-Claude-Code Stop-hook
host.

## When to delegate

| Use vd:auto-loop (in-house) | Use --codex |
|---|---|
| You're already in a Claude Code session | You're at a fresh shell |
| Goal needs Claude-Code MCP tools / skills | Pure shell-based goal |
| You don't have ChatGPT Pro | You have ChatGPT Pro and codex ≥ 0.128.0 |
| You want intra-session state visible via `--status` | You're fine with Codex's own /goal status |

## Requirements

- `codex --version` → ≥ `0.128.0` (refused otherwise).
- ChatGPT subscription with Codex enabled (auth probed lazily by codex on first command).
- A `goal.md` (or inline goal text) that codex can ingest.

## What the delegation does

1. Probes `codex --version`; refuses on missing or `<0.128.0`.
2. Refuses if a `vd:auto-loop` heartbeat is already live in the workspace.
3. Resolves the goal text (from `--goal-file` or positional `<goal>`).
4. `exec`s `codex --sandbox workspace-write`, leaving the user in the TUI.
5. The user types `/goal <text>` to start; manages `/goal status` / `pause` / `resume`
   / `clear` from inside the TUI.

## Sandbox modes

| Mode | When to use |
|---|---|
| `workspace-write` (default) | Edits inside repo allowed. **Default.** |
| `read-only` | Audit/observation only - pass `--codex --sandbox read-only` (Codex flag, not vd's). |
| `danger-full-access` | Network + arbitrary file access. **Never default.** Re-run `codex` manually with the flag if you really need it. |

## Limitations

- **Non-interactive support unclear.** As of codex 0.128.x, `/goal` is a TUI command;
  `codex exec` does not (yet) accept `/goal` as an argument. So delegation is
  inherently interactive - the user must be present in the codex TUI to type the
  initial command. Update this doc when codex supports headless `/goal`.
- **No state-bridge with vd:auto-loop.** Once delegated, codex owns the loop. There
  is no `.auto-loop/goal-state.json` while codex is driving - codex maintains its
  own state in its own directory.
- **No two-vote audit.** Codex `/goal` ships its own completion criteria; vd's
  audit-subagent gate does not run.

## Why we don't reimplement /goal

Codex got the structured-state contract right and ships the verifier-running primitive
out of the box. Reimplementing it inside Claude Code (which `vd:auto-loop` does for
the no-Codex case) is purely about removing the dependency on a paid Codex
subscription. When the user *has* Codex, native `/goal` is the better tool.

## Troubleshooting

- "codex CLI not installed" → install via `npm i -g @openai/codex` (or follow
  https://developers.openai.com/codex/quickstart).
- "codex /goal requires 0.128.0+" → upgrade with the same install command.
- Codex authenticates lazily; if `/goal` errors with auth message, run `codex login`.
- If codex misbehaves, run `--cancel` from a fresh shell to clean any leftover
  vd:auto-loop heartbeat (delegation is supposed to refuse on a live heartbeat,
  but a crash mid-handoff could leave one).
