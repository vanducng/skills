# RPass UI map (read 2026-11)

`scripts/rpass.py` depends on these. When one stops matching after an RPass update, fix the script, not the agent's habits.

## Extension

| What | How to reach it |
|---|---|
| Vault home | `chrome-extension://<ext-id>/index.html`; redirects to `/vault/<vault-id>/folder/root`. The public extension id is the script's default (`--ext-id` overrides). |
| Deep links to an item | Fail with `ERR_FILE_NOT_FOUND`. Search, then click the name. |
| Search | the only `input` on the home page (placeholder "Search all items") |
| Add | button "Add" → menu "Login", "Note", "Folder" |
| Note form | placeholders "Name this note", "Type your note here", "Search vaults" (vault picker, shows the chosen vault name), "Enter tags"; buttons "Create" (new) or "Save" (edit), "Cancel" |
| Item menu | the `[data-testid=test_button]` on the same row as `[data-testid=item-header-back-button]`, rightmost → "Share", "Edit", "Remove" |
| Share | opens a Rippling tab: `https://app.rippling.com/rpass/share/vault/<vault-id>/item/<item-id>?rpassId=<ext-id>`; the item URL carries both ids |

## Share page (app.rippling.com)

| What | Selector |
|---|---|
| Add people or groups | placeholder "Search for people or groups"; results are `li` (groups read "Teams → Org > Team") |
| Rows | `tr` / `[role=row]` under "People with access" |
| Access level | `[role=combobox]` in the row → options "Use but not view", "Use and view", "Manage" |
| Remove a row | `[data-testid=remove-recipient-icon]` in the row |
| Who it resolves to | button "Preview people" → dialog table: name, title, level |
| Save | `[data-testid=share-modal-share-button]` → page text "Sharing settings updated" |

## Aside repl limits

- `fs` reaches only the session and project roots (`Path escapes Project and session roots`), so the script puts values into the generated script itself, mode 600, deleted after the run.
- `pwd` is a value, not a function. `fs.resolvePath('<name>')` gives a session path; session files do not outlive the run.
