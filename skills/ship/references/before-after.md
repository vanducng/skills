# Before / After Evidence (ship Step 12b)

Embed visual (or measured) proof in the PR and, when a ticket is linked, on the tracker. Inspired by `@vercel/before-and-after` / michaelshimeles `before-and-after`; upload path is ours - GitHub `user-attachments` for private-repo-safe PR embeds, Jira ADF for tickets. Never `0x0.st` for work that must stay private.

## When it runs

| Diff surface | Expectation |
|---|---|
| User-visible UI (layout, copy, control, empty/error state, guard) | **Expected.** Capture or reuse a before/after pair and embed it. |
| Bug fix with a visible failure mode | **Expected.** Before = reproduced break; after = same steps, fixed. |
| API / CLI / data / infra with no visible surface | Skip UI capture. Prefer a measured pair (latency, row count, exit code, output excerpt) in the verification block or as a short PR comment. |
| `--skip-screenshots` | Skip the whole step. Say so once in the ship summary. |

**Never blocks ship.** If URLs are unknown, the preview is down, or capture would cost more than the evidence is worth: leave `<!-- SCREENSHOTS -->` out (or replace with `_(no before/after - <one-line reason>)_`), note it in the verification block, and continue. Do not stall a PR hunting for a screenshot.

## Capture sources (pick the cheapest that works)

Prefer **reusing** pairs already taken during `vd:cook` / `vd:fix` / `vd:web-e2e`. Capture only when missing.

1. **Existing PNGs** - two local files (or two URLs already screenshotted).
2. **`@vercel/before-and-after`** - two URLs (prod vs preview, or `main` deploy vs PR preview):
   ```bash
   # Optional capture CLI - intentionally unpinned (unlike agent-browser@0.27.2).
   # Prefer npx so nothing is written to the global agent-browser pin.
   npx -y @vercel/before-and-after "$BEFORE_URL" "$AFTER_URL" -o /tmp/ship-ba
   # Optional: selector, --mobile / --tablet, --full only when asked
   # If Chrome fails with "No usable sandbox", check the installed CLI's docs for
   # the current sandbox workaround - do not invent env vars here.
   ```
3. **`vd:agent-browser` / `vd:web-e2e`** - drive the same page + viewport + scroll for both states; install only via that skill's pin (`agent-browser@0.27.2`), then `agent-browser screenshot /abs/path.png` (path is positional and absolute).
4. **Non-UI measured pair** - save `before.txt` / `after.txt` (or a one-line table) and paste into the PR body under the verification block. No image upload.

**Same page, viewport, and scroll in both shots.** A mismatched pair is worse than none.

| Change | Before | After |
|---|---|---|
| New/changed control | Current prod or `main` build | This PR's preview / local |
| New guard or validation | Action attempted, no guard | Guard firing (+ success path once satisfied) |
| Bug fix | Broken state reproduced | Same steps, correct behaviour |

Pair each shot with an observed value (row count, error text, ID) in the surrounding prose - image shows it happened, number makes it checkable.

## Upload (PR) - GitHub user-attachments only

Do **not** commit screenshots. Do **not** use public paste hosts for private work.

Recipe (upload helper + HTML table + `<!-- SCREENSHOTS -->` marker):

> `../git/references/gh-cli-guide.md` → *Attach screenshots (before/after evidence)*

Summary:

1. Draft the PR body in Step 12 with a lone `<!-- SCREENSHOTS -->` line after the verification block (UI-visible only).
2. `BEFORE=$(gh_upload_image before.png)` / `AFTER=$(gh_upload_image after.png)`.
3. Replace the marker with the `<table>…</table>` HTML pair (width ~480).
4. Verify: unauthenticated `curl` of the asset URL → 404 on a private repo; authenticated → 200. Broken embeds look fine in raw markdown - check rendered `naturalWidth`.

If Step 12 already opened the PR without the marker (non-UI guessed wrong), append the table via `gh pr edit` after a blank line under the verification block.

## Ticket system (Jira / tracker)

When Step 1b confirmed a ticket key **and** a before/after pair exists:

1. Activate `vd:jira` (or the repo's tracker skill).
2. **Show before execute** - display the target key, comment prose, and image paths; get approval (`AskUserQuestion` / plain-text). `--auto` does not suppress this prompt; if declined, skip the ticket post and continue the ship.
3. Post a short follow-up comment with the pair **inline** - not attachment-only.
   - Jira: readable ADF `mediaSingle` per [`../../jira/references/inline-images.md`](../../jira/references/inline-images.md) (file-relative from this reference; skill-root form is `../jira/references/inline-images.md`). Label before vs after in the comment text.
   - GitHub issue only: same HTML table as the PR, or markdown images from `user-attachments` URLs.
4. One line of result prose: what changed + PR URL. No second essay.

Skip silently when there is no confirmed ticket, the user declines the draft, the tracker skill is unavailable, or the change is non-visual.

## Guardrails

- No secrets, tokens, customer PII, or payment data in captures. Redact or skip.
- Confirm the "after" URL/process is **this** branch (right port, right preview, `git rev-parse --short HEAD` noted once in the ship summary).
- Run a `vd:unslop` pass on any new prose wrapped around the table.
- PolyForm Shield applies to the upstream `@vercel/before-and-after` CLI itself; this reference only documents calling it. Prefer `gh_upload_image` over the CLI's default `--markdown` upload host when the repo is private.
