# Codex runtime support — v0.2 in progress

`vd:pursue` v0.2 ships **Claude Code + Codex TUI parity** via a Dual-SKILL.md architecture (`runtimes/claude-code.md` + `runtimes/codex.md`, top-level `SKILL.md` is a router).

**Current status:** v0.2 cook in progress. This file is a placeholder; Phase 4 of the v0.2 plan fills in the full v0.2-reality content (workarounds, comparison vs Claude Code, dogfood numbers, deferral list).

For implementation details: `~/skills/plans/260525-1501-pursue-v0.2-codex/plan.md`.

For prior research (May 25, 2026 baseline → 2-week-later snapshot showing Codex's surface convergence): `~/skills/plans/reports/researcher-260525-1446-pursue-v0.2-codex-adapter.md`.

## Quick reference (will be replaced by Phase 4)

- **Skill discovery:** Codex auto-discovers `~/.codex/skills/<name>/SKILL.md` (or `~/.agents/skills/` via `vd install codex`).
- **Loop primitive:** native Codex `/goal` (stable since April 2026) — pursue's cook+verify delegates here via `vd:auto-loop --codex`.
- **Skill-to-skill:** `codex exec resume --last "use vd:<skill> ..."` (auto-match on skill description).
- **Monitor analog:** PostToolUse hook + `additionalContext` injection — see `references/codex-gap-workarounds.md` (Phase 3).
- **Push notifications:** `scripts/notify.sh` — terminal-notifier / ntfy.sh / Slack webhook / log fallback (Phase 4).

## Deferred to v0.3

- Full `codex exec` (non-interactive) parity — `ask_user_question` is unavailable in exec mode; intake errors with an actionable message instead.
- Cross-runtime DAG / multi-goal concurrency.
- Automated CI cross-runtime test (v0.2 ships dogfood-validated only).
- Plugin marketplace vs `vd install` symlink conflict resolution.
