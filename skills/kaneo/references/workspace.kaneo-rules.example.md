---
alias: <alias>
base_url: https://kaneo.example.com
token_env: <token-env-name>
env_file: $HOME/.config/<env-file>
workspace_id: <workspace-id>
workspace_slug: <workspace-slug>
me_user_id: <user-id>
ops_project_slug: <project-slug>
ops_project_id: <project-id>
---

# Kaneo rules: <alias>

Copy this file to `$HOME/.config/vd/kaneo-rules/<alias>.kaneo-rules.md`.
Keep the local copy outside Git - it holds the Kaneo host, workspace id,
and project ids for a real instance.

## Frontmatter

| Key | Meaning |
|---|---|
| `alias` | Flag value for `--workspace` |
| `base_url` | Origin only. No `/api` suffix |
| `token_env` | Env var name holding the API key. **Name only** |
| `env_file` | File to source before reads |
| `workspace_id` | Kaneo organization id from `GET /api/auth/organization/list` |
| `workspace_slug` | Org slug, used in task URLs |
| `me_user_id` | Assignee id for "me" |
| `ops_project_slug` | Ops board slug (task keys become `<PROJECT>-N`) |
| `ops_project_id` | Ops board id from `GET /api/project?workspaceId=` |

## Ticket defaults

- New ops log: status `to-do`, priority `medium`, assignee me.
- Invoice logs stay `to-do` until paid, then `done`.
