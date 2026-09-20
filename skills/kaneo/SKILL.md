---
name: kaneo
description: "Operate Kaneo project tracking over its REST API or built-in HTTP MCP - list workspaces, projects, tasks, comments, labels, and columns; create or update tasks and related records. Use when the user says kaneo, Kaneo ticket, log this in Kaneo, or asks to create or update a Kaneo task."
license: MIT
argument-hint: "[--workspace ALIAS] [list|view|create|update|comment] [task]"
metadata:
  author: vanducng
  version: "1.0.0"
  upstream: "https://github.com/usekaneo/kaneo"
---

# Kaneo

Self-hosted Kaneo (`usekaneo/kaneo`). Prefer REST with an API key. MCP is optional.

Instance values (URL, workspace id, project ids, token env) live in a private
rules file **outside this repo**. This skill ships no hostnames or ids.

```
$HOME/.config/vd/kaneo-rules/<alias>.kaneo-rules.md
```

Copy `references/workspace.kaneo-rules.example.md` to onboard an instance.
Read the whole rules file before any write.

Do not vendor `usekaneo/kaneo` `.agents/skills` - those are Kaneo-the-product
UI skills (animation, design), not tracker ops.

## Auth

1. Load `$HOME/.config/vd/kaneo-rules/<alias>.kaneo-rules.md`.
2. Source its environment file and export the named token env var. Never print it.
3. Send `Authorization: Bearer $TOKEN` on every call. Kaneo also accepts the
   same value as `x-api-key`. Create keys under Settings -> Account -> Developer.

Refuse when the rules file or token env is missing.

## REST (default)

Base is the rules `base_url` with no trailing slash. Paths are under `/api`.
Use the task UUID returned by the API for task routes, not the display key such
as `<PROJECT>-123`.

```bash
AUTH=(-H "Authorization: Bearer $TOKEN")

curl -fsS "${AUTH[@]}" "$BASE/api/auth/organization/list"
curl -fsS "${AUTH[@]}" "$BASE/api/project?workspaceId=$WS"
curl -fsS "${AUTH[@]}" "$BASE/api/column/$PROJECT_ID"
curl -fsS "${AUTH[@]}" "$BASE/api/task/tasks/$PROJECT_ID"
curl -fsS "${AUTH[@]}" "$BASE/api/task/$TASK_ID"
```

Common write routes:

| Action | Request |
|---|---|
| Create task | `POST /api/task/{projectId}` |
| Change status | `PUT /api/task/status/{taskId}` with `{"status":"<column-slug>"}` |
| Assign or unassign | `PUT /api/task/assignee/{taskId}` with `{"userId":"<user-id>"}` or `null` |
| Set or clear due date | `PUT /api/task/due-date/{taskId}` with `{"dueDate":"<ISO-date>"}` or `{}` |
| List or add comments | `GET` or `POST /api/comment/{taskId}`; create with `{"content":"<text>"}` |
| Edit comment | `PUT /api/comment/{commentId}` with `{"content":"<text>"}` |
| List workspace labels | `GET /api/label/workspace/{workspaceId}` |
| List task labels | `GET /api/label/task/{taskId}` |
| Create label | `POST /api/label` with name, color, workspaceId, and optional taskId |
| Update label | `PUT /api/label/{labelId}` with name and color |
| Attach label | `PUT /api/label/{labelId}/task` with `{"taskId":"<task-id>"}` |
| Create column | `POST /api/column/{projectId}` with name and optional icon, color, and isFinal |
| Update column | `PUT /api/column/{columnId}` with the fields to change |

Create tasks with a JSON file so shell quoting cannot change the body:

```json
{
  "title": "<title>",
  "description": "<description>",
  "priority": "medium",
  "status": "<column-slug>",
  "userId": "<assignee-id>",
  "dueDate": "<ISO-date>"
}
```

```bash
curl -fsS -X POST "${AUTH[@]}" -H "Content-Type: application/json" \
  "$BASE/api/task/$PROJECT_ID" --data-binary @/tmp/kaneo-task.json
```

Priority is `no-priority`, `low`, `medium`, `high`, or `urgent`. Get status
slugs from `GET /api/column/{projectId}`. Get assignee IDs from
`GET /api/workspace/{workspaceId}/members`.

Writes require a direct user request. Read the target first, show any missing
choice such as project, status, assignee, or due date, then write and read the
result back. Never delete a task, comment, label, column, or project without an
explicit delete request.

## MCP (optional)

Every instance exposes Streamable HTTP MCP at `$BASE/api/mcp`. Same tools as
`@kaneo/mcp`. API-key Bearer skips the OAuth device flow. Call
`list_project_columns` before setting status and `list_workspace_members`
before assigning. Prefer the narrow tools such as `update_task_status`,
`create_task_comment`, and `attach_label_to_task` over a full task update.

Do not use MCP OAuth in headless runs when an API key exists.

## Authenticated browser fallback

If the configured REST/MCP token returns an authentication error, stop retrying that token. When the user already has an authenticated Kaneo browser session and authorized the write, use `vd:ego-browser` as the fallback:

1. Open the project board and target a known task UUID with `?taskId=<task-uuid>`.
2. Read back the display key, title, description, and current status before editing.
3. Add evidence through the `Comment editor`. Use its hidden file input with `uploadFile(...)` before submitting when screenshots are required.
4. Change status through the task's status control using the actual column names shown by the UI.
5. Read the task again and verify the comment, attachments, and final status.

Do not treat a browser toast as proof of a write. Keep using UUIDs for direct task targeting; display keys remain communication labels only.

## Invoice / ops log

When logging a sent invoice, put it on the workspace's ops project (rules
`ops_project_slug`), status `to-do` until paid, due = Net 15 from issue date.
Title: `<client> invoice <INV-...> issued`. Description: period, hours, rate,
amount, sent-to, subject, PDF filename. Assignee: rules `me_user_id`.
