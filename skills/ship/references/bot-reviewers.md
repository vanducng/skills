# Bot reviewers - inline replies + re-review triggers

How to respond to each automated PR reviewer (Step 13 / 15b). Two classes:

- **GitHub PR bots** - review *as a PR/CI job*, post inline review threads. You reply on the thread with the fix/false-positive rationale, resolve it (GraphQL), and **re-trigger a fresh review with a PR comment command**.
- **Local CLI reviewers** - run on your machine, not GitHub. There is no PR comment to trigger them; **re-run the CLI** (via its skill) to re-review.

## GitHub PR bots

| Bot | Comment author (login) | Re-review trigger (post as PR comment) | Resolve threads |
|---|---|---|---|
| **CodeRabbit** | `coderabbitai` | `@coderabbitai review` (incremental) · `@coderabbitai full review` | `@coderabbitai resolve` (resolves all its threads) · or GraphQL |
| **Gemini Code Assist** | `gemini-code-assist` | `/gemini review` (also `/gemini summary`) | no resolve command → GraphQL `resolveReviewThread` |
| **Codex** | `chatgpt-codex-connector` | `@codex review` | no resolve command → GraphQL `resolveReviewThread` |

- These triggers are **PR-level comments** (`gh pr comment <n> --body "<trigger>"`), not thread replies.
- Do not use `@coderabbitai resolve` or GraphQL `resolveReviewThread` until every addressed thread has an inline reply explaining the outcome.
- If a thread is already resolved but lacks an explanatory inline reply, post the missing rationale before treating it as clear.
- **You can resolve any thread, including a bot's.** `resolveReviewThread` needs write access on the repo, not authorship of the comment - being the PR author is enough. Never leave a thread open on the belief that only its author can close it; try the mutation.
- After pushing fixes, the bot auto-marks its old threads **outdated** when the cited lines change. Outdated is **not** resolved: those threads still render as open review conversations to a human. Reply and resolve them too - "the code moved" is itself a valid resolution note.
- **Finish the job**: replying is not resolving. Every thread you fixed, or explained as a deliberate non-fix, gets resolved in the same pass. Leaving replied-but-open threads pushes the cleanup onto the reviewer.
- Severity tags to triage by: CodeRabbit uses prose + `🛠️ Refactor/⚠️ Potential issue`; Gemini uses `high/medium/low`; Codex uses `P1/P2/P3` badges. Treat P1/high/⚠️ as blocking.

## Local CLI reviewers

| Tool | How to run | Re-review |
|---|---|---|
| **miu-cr** (`miucr`) | `miucr` skill / CLI | re-run the CLI (no PR trigger) |

These post line-level findings locally (and can apply fixes); they don't watch the PR, so iterate by re-running.

## The loop (per iteration)

1. **Fetch** all review threads, then classify: unresolved actionable (`isResolved==false && isOutdated==false`), unresolved-but-outdated (`isOutdated==true` - still needs a reply + resolve, just no code work), and resolved threads missing a rationale reply.
2. **Triage** each - validate against codebase contracts/types/tests, not just the suggested patch. Apply the *root-cause* fix even if it differs from the suggestion.
3. **Reply inline** on each thread with the resolution (what changed + why, or why it's a deliberate non-fix).
4. **Resolve** only after the reply is posted and the thread is still the intended one. For already-resolved threads without a reply, add the retrospective inline reply and re-fetch.
5. **Re-trigger** every GH bot with its command above; **re-run** local CLIs.
6. **Re-fetch** after the bots finish (async, ~1-5 min). Repeat until **zero unresolved threads of any kind, zero silent resolves, AND green CI**.

Exit check - `unresolved` must be `0`, not just "no actionable ones left":

```bash
gh api graphql -f query='{repository(owner:"OWNER",name:"REPO"){pullRequest(number:NUM){
  reviewThreads(first:100){nodes{isResolved}}}}}' \
 --jq '.data.repository.pullRequest.reviewThreads.nodes
       | "resolved: \([.[]|select(.isResolved)]|length) · unresolved: \([.[]|select(.isResolved==false)]|length)"'
```

Watch for the **self-introduced regression**: a re-review often flags a flaw in *your fix* (e.g. an over-aggressive fast-fail). Treat those like any new finding - don't dismiss because "I just fixed that area."

## gh snippets

```bash
R=owner/repo; PR=123
# fetch review threads (triage unresolved items and resolved items missing a reply)
gh api graphql -f query='query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){pullRequest(number:$n){
  reviewThreads(first:100){nodes{id isResolved isOutdated comments(first:1){nodes{databaseId author{login} path line body}}}}}}}' \
  -F o=${R%/*} -F r=${R#*/} -F n=$PR \
  --jq '.data.repository.pullRequest.reviewThreads.nodes[]
        |"\(.id) | resolved=\(.isResolved) | outdated=\(.isOutdated) | \(.comments.nodes[0].author.login) | \(.comments.nodes[0].path):\(.comments.nodes[0].line)"'

# reply on a thread (REST, by first comment's databaseId)
gh api -X POST "repos/$R/pulls/$PR/comments/<COMMENT_DB_ID>/replies" -f body="Fixed in <sha> - <what+why>."

# resolve a thread (GraphQL, by thread node id)
gh api graphql -f query='mutation($id:ID!){resolveReviewThread(input:{threadId:$id}){thread{isResolved}}}' -F id=<THREAD_ID>

# re-trigger
gh pr comment $PR --repo "$R" --body "@codex review"        # or @coderabbitai review, or /gemini review
```
