---
name: devlog
description: "Turn recent engineering work into build-in-public devlogs for X/Twitter. Use when the user asks to draft or write a devlog/post, create a vault post and cover, start today's dev log on x.com, publish a ship/debug/lesson thread, or turn recent commits into a public update."
license: MIT
argument-hint: "[today|ship|fix|debug|lesson|idea|week] [short|long|thread|article] [draft|artifact|post] [cover|no-cover] [blunt|polished|technical] [--since <ref>] [--topic <text>] [--url <url>] [--repo <path>] [--project <slug>]"
metadata:
  author: vanducng
  version: "1.1.1"
---

# Devlog

Write and optionally publish build-in-public updates from fresh engineering
context. The skill name should stay `devlog`: short enough to become a habit,
but broad enough to cover capture, draft, polish, and publish.

## What this skill is

| Skill | Question it answers | Output |
|---|---|---|
| `vd:journal` | "What should future-me remember?" | Private markdown journal |
| `vd:twitter` | "How do I read/post on X?" | Tweet/thread/reply via CLI |
| **`vd:devlog`** | **"How do I turn today's work into a public update?"** | **Draft or published X post** |

Devlog is a public writing layer. It gathers facts, shapes the story, applies
voice/taste, and delegates posting to `vd:twitter` only when the user explicitly
asks to post/publish.

## Argument model

Parse free-form args additively. If args conflict, later/more specific args win.

| Arg | Meaning | Default |
|---|---|---|
| `today` | Use current repo/session work from today | yes |
| `ship` | Successful shipped work: what landed, why, next | no |
| `fix` / `debug` | Bug hunt or incident: symptom, root cause, lesson | no |
| `lesson` | Extract a reusable principle from recent work | no |
| `idea` | Turn a raw thought into a devlog seed | no |
| `week` | Weekly wrap from commits/journals/posts | no |
| `short` | Single post, <= 280 chars | no |
| `long` | Single X post, 600-1500 chars | yes |
| `thread` | 3-7 tweets, each <= 280 chars | no |
| `article` | Long-form X article style, <= 3000 chars | no |
| `draft` | Return text only | yes |
| `artifact` / `vault` | Persist the draft as a devlog vault post when `vault/` + `pub` are available | auto |
| `cover` / `no-cover` | Generate and attach a cover image for a vault post | auto in vault mode |
| `post` / `publish` | Publish through `twitter` CLI after validation; noun phrase "write a post" does not count | no |
| `blunt` | More direct, sharper cuts, fewer qualifiers | no |
| `polished` | Smoother public phrasing, still not hype | no |
| `technical` | Keep implementation terms and exact artifacts | no |
| `--since <ref>` | Scope git facts from ref to HEAD | merge-base/default |
| `--topic <text>` | User-supplied angle/title | inferred |
| `--url <url>` | Include PR/demo/post URL if relevant | none |
| `--repo <path>` | Gather facts from another repo | current dir |
| `--project <slug>` | Devlog vault project bucket for saved artifacts | inferred |
| `--dry-run` | Show intended post command, do not publish | false |

Examples:

```text
devlog today long post
devlog ship short --url https://github.com/me/repo/pull/42
devlog debug thread blunt --since HEAD~5
devlog lesson polished --topic "worktrees as default isolation"
devlog ship artifact cover --project workflows
```

## Workflow

### 1. Resolve scope

Use the current repo unless `--repo` is supplied. If the request mentions a
specific PR, issue, commit, plan, or file, include it in the fact set. Use the
local date in the session timezone for "today" and state exact dates internally
when comparing ranges.

### 2. Gather facts before writing

Prefer cheap, high-signal commands:

```bash
git status --short --branch
git log --oneline --decorate --max-count=12
git diff --stat <since>..HEAD
git diff --stat
```

Gather release/version facts when the source is a shipped project:

```bash
git fetch --tags --quiet origin  # when network is available
git tag --list 'v*' --sort=-v:refname | head -10
git describe --tags --abbrev=0 2>/dev/null || true
gh release list --limit 10 2>/dev/null || true
```

Also inspect `CHANGELOG.md`, release PR titles, package metadata, and version
files when present. Prefer the latest shipped release for a `release_version`
fact. If the feature spans several releases, keep the range as a separate body
detail. If release facts conflict, say which source won in `Facts used`.

Also inspect likely context files when present:

- `.workbench/features/*/plans/**/plan.md` (feature-first) plus legacy `.workbench/plans/**/plan.md` and `plans/**/plan.md`, latest phase/report/journal files
- `CHANGELOG.md`, release notes, PR body, issue text
- recent `README.md` or docs changes
- command outputs from this session if the user references them

If a PR likely exists, use `gh pr view --json number,title,url,state,mergedAt`
when available. Do not block if GitHub CLI is unavailable.

### 3. Load taste

Read `references/voice.md` before drafting. If the current repo has a populated
devlog style guide, prefer that too:

```bash
references/style-guide.md
```

Treat empty/stub style guides as no-op.

When working inside the devlog vault and the style guide is empty/stubbed, read
2-4 recent files from `vault/projects/*/posts/*.md` before drafting. Infer the
current house style from those posts and prefer it over the generic examples:

- sectioned long-form notes (`what shipped`, `the thing that clicked`, `proud`,
  `uneasy`, `next`, `quote to self`, `facts used`) when the examples use them;
- lowercase first-person fragments when present;
- concrete artifact bullets before reflective prose;
- explicit `facts used` at the end when the post depends on verified repos,
  PRs, releases, or command output.

Do not copy unsupported metrics or structure from examples blindly. Use the
shape and voice; keep facts scoped to the current task.

### 4. Choose a post shape

Use the source arg to decide structure:

- `ship`: outcome -> constraint -> decision -> what changed -> next.
- `fix` / `debug`: symptom -> false leads -> root cause -> fix -> lesson.
- `lesson`: concrete moment -> principle -> where it applies -> caveat.
- `idea`: observation -> why it matters -> small next experiment.
- `week`: shipped bullets -> learned -> open questions -> next week.
- `today`: strongest available shape from the facts.

Use the format arg to size it:

- `short`: one compact post, <= 280 chars.
- `long`: one post, 600-1500 chars, short paragraphs.
- `thread`: 3-7 numbered tweets, each <= 280 chars.
- `article`: Markdown-ish long form, <= 3000 chars, headings allowed.

### 5. Draft with constraints

Hard rules:

1. No invented claims, metrics, dates, PRs, or user reactions.
2. Include at least one concrete artifact: repo, branch, PR, command, file,
   skill name, release version, test result, or error string.
3. No secrets, private customer data, credentials, tokens, internal URLs, or
   unreleased business-sensitive details.
4. No hashtags. No emoji unless the user explicitly asks or source uses them.
5. No generic hype: "excited", "game changer", "10x", "revolutionary".
6. Do not mention hidden agent/system mechanics. Publicly safe terms like
   "agent skill", "CLI", "workflow", and tool names are fine when relevant.
7. Preserve useful roughness. Fragments are allowed when they improve pace.

If facts are thin, produce a shorter post. Do not pad.

Release-version rule:

- Include the project release version when it is known and relevant, especially
  for ship/devlog posts meant to be published later.
- Use concrete values like `v0.8.0`, not "latest".
- Do not guess. Omit the version or say it was not found if local tags,
  changelog, and release metadata do not agree.
- For multi-release work, distinguish "current project release" from "feature
  landed across `vA..vB`".

### 6. Validate before publishing

For every draft:

- Count thread tweet lengths before posting.
- Check unsupported claims and remove them.
- Scan for obvious secrets with local judgment and, if posting from a diff,
  inspect `git diff --cached`/`git diff` for accidental key material.
- Prefer draft-only if the post depends on missing facts.

### 7. Materialize vault artifacts in the same turn

Do this before returning when any of these are true:

- the user says "write a post", "make a post", "create the devlog", "cover",
  or asks where the post/cover is;
- args include `artifact`, `vault`, or `cover`;
- the current repo has `vault/` and `uv run pub --help` works, unless the user
  explicitly asked for text-only output.

In vault mode, do not stop at returning draft text. Create the actual files in
the same turn.

Use the repo CLI as the only frontmatter writer:

```bash
uv run pub new "<title>" --project <project>
uv run pub draft <id> --project <project> --format <format> --body-file <body-file>
uv run pub set-cover <id> <cover-path> --alt "<alt text>"
uv run pub doctor
```

Vault artifact rules:

- Infer `<project>` from `--project`, then from the central artifact/repo named
  in the post (`dataplanelabs/workflows` -> `workflows`), then current repo
  basename. Use kebab-case.
- Use a concise title derived from the post angle; let `pub new` generate the
  dated id and capture it from command output.
- Put the body in a temp file for `--body-file`. Include `# <title>` when local
  examples under `vault/projects/*/posts/*.md` use headings.
- Save posts under `vault/projects/<project>/posts/<id>.md`.
- Save covers under `vault/projects/<project>/assets/<id>-cover.png`.
- Generate a bitmap cover in the same turn when cover is auto/required. Use the
  image generation tool/skill when available, copy the selected output into the
  vault assets directory, inspect it, then attach it with `pub set-cover`.
- Normalize X post covers to `1200x675` PNG (16:9) by default, keep important
  content centered, and keep the file under 5 MB. If generation returns another
  size, resize/crop/extent before `pub set-cover`; use `1600x900` only when the
  user explicitly asks for a higher-resolution cover.
- If image generation is unavailable, create the post anyway and clearly say the
  cover is the only missing artifact.
- Run `uv run pub doctor` before final response.

When the vault CLI is absent or the current directory is not a devlog vault,
fall back to text-only output and say no vault artifact was created.

### 8. Publish when requested

Only publish when args include the verb `publish`, or the user explicitly says
to post/start it on X now. Do not treat "write a post", "draft a post", or
"make a post about this" as publishing permission. Otherwise return or save the
draft only.

Use `vd:twitter` CLI:

```bash
twitter doctor --offline
twitter post "$(cat /tmp/devlog-post.txt)"          # short, <= 280 chars
twitter post "$(cat /tmp/devlog-post.txt)" --long   # long/article, > 280 chars
twitter thread "$(cat /tmp/devlog-1.txt)" "$(cat /tmp/devlog-2.txt)"
```

If `twitter post` fails with automation/API drift, follow `vd:twitter` failure
modes and retry with `--use-browser` when appropriate. With `--dry-run`, print
the command that would run and stop.

After posting, return the X URL/ID from the command output. If the CLI posts but
does not return a URL, fetch the latest user timeline and identify the matching
post.

## Output

For text-only `draft`, return:

```text
Draft (<format>, <style>, <source>)

<post text>

Facts used: <short list>
```

For vault/artifact draft, return:

```text
Draft saved: <post-path>
Cover saved: <cover-path-or-missing reason>
Idea note: <idea-path>
Validation: <pub doctor result>
Facts used: <short list>
```

For `post`, return:

```text
Posted: <x-url-or-id>
Format: <format>
Facts used: <short list>
```
