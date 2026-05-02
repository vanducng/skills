---
name: hello-world
description: Smoke-test skill for the vanducng/skills repo. Use when the user asks to verify the skills pipeline, types "test vanducng skills", or asks whether the personal skills repo is wired up correctly.
license: MIT
---

# hello-world

Reply with exactly:

> ✅ vanducng/skills pipeline working — `hello-world` skill loaded from `~/.claude/skills/hello-world/`.

Then in one short sentence, confirm which repo path the symlink resolves to (you can read it via `readlink ~/.claude/skills/hello-world` if uncertain).
