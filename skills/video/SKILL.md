---
name: video
description: "Make, edit, or render videos with HyperFrames (HTML to deterministic MP4), tuned to this toolchain: PR and release videos after ship, product promos from a URL or show-off page, concept explainers, and short motion graphics for X devlog posts. Front door for HyperFrames - read this before the hyperframes skill: it bootstraps the upstream skills, pre-selects the workflow, sets media and output defaults without a HeyGen account, and hands the MP4 to devlog/twitter. Use when the user asks to make, create, or render a video, PR or changelog video, release reel, launch promo, demo clip, motion graphic, or explainer, or mentions hyperframes. Not for AI-generated footage or text-to-video clips (vd:omnimedia), slide decks (vd:opendesign), recording a browser session (vd:agent-browser), still images (vd:marketing-design), or a video the user wants built in Remotion (porting Remotion source to HyperFrames is in scope)."
license: MIT
argument-hint: "[pr|release|promo|explain|motion|edit|render] [<PR ref|tag|URL|path|topic>] [x|wide|vertical] [--auto] [--storyboard]"
metadata:
  author: vanducng
  version: "1.0.0"
---

# Video

HyperFrames renders HTML compositions to MP4. The upstream skills own the craft
(composition contract, animation, CLI, media). This skill owns only the
personal layer: setup, routing from daily work, media providers, where files
land, and delivery. Never restate upstream rules from memory - load the
upstream skill that owns them.

## 1. Setup (once per session)

```bash
node -v   # >= 22
npx -y hyperframes@latest skills check || npx -y hyperframes@latest skills update
```

`skills update` installs the core set (`hyperframes`, `hyperframes-*`,
`media-use`) into `~/.claude/skills` and `~/.agents/skills`; creation workflows
install on demand at routing time. A failed install is a visible failure -
surface it, never continue from remembered upstream content. On a new machine
run `npx hyperframes doctor` once (FFmpeg required; headless Chrome self-installs).

Never name a local skill `hyperframes-*` - the upstream installer claims that prefix.

## 2. Route

Pre-select from the table, then read the `hyperframes` skill and follow its state table
(resume, edit, and render-only rows still win). The route file
(`references/routes/<workflow>.md`) still has the final say.

| Ask | Workflow | Defaults |
|---|---|---|
| `pr` - "video for this PR", after `vd:ship` | `pr-to-video` | 16:9, developers. Angle from the PR title's conventional-commit type: `feat` → feature-reveal, `fix` → fix-explainer, `refactor`/`perf` → refactor-walkthrough, else changelog |
| `release` - a tag or "this release" | `faceless-explainer`, input = `gh release view <tag> --json body -q .body` | square, 45-60s. One scene per theme, never one per bullet - visualize, don't list |
| `promo` - product, docs site, or `vd:show-off` page URL | `product-launch-video` | 16:9 master |
| `explain` - concept, lesson, devlog idea | `faceless-explainer` | square |
| `motion` - stat hit, logo sting, headline, under 10s | `motion-graphics` | square, unnarrated |
| captions, talking-head overlays, music video, Remotion port, Figma input | let `hyperframes` route | - |
| anything else, or "build it with me" | `general-video` | - |

Destination shorthand: `x` → `x-feed` (1080x1080), `wide` → 1920x1080,
`vertical` → 1080x1920.

Elsewhere: AI-generated footage (text-to-video) → `vd:omnimedia`; generated
clips can come back as footage. Slide decks → `vd:opendesign`. Recording a real browser flow →
`vd:agent-browser`; its recording can come back as footage for `general-video`.
A still promo image → `vd:marketing-design`.

## 3. Intent layer, compressed

Run upstream's intent layer (`hyperframes` → `references/intent-interview.md`)
with these overrides:

- `--auto` or "just build it" is upstream's lock signal: `flow: automation`,
  `storyboard: no`, every unanswered field becomes a defaulted decision listed
  in the heads-up.
- `--storyboard` locks `storyboard: yes`.
- Otherwise ask the route's open must-haves in ONE round - one question per
  field, recommended option first - not one message per field. Values the
  table above or the input already settles are recommendations with receipts.
- Pitch round only for a truly unformed request. A PR, tag, or URL plus an
  angle is formed.

## 4. Where the project lives

Scaffold under the hook-injected `Visuals:` path: run the workflow's own
`hyperframes init <slug> ...` command from that directory, adding
`--non-interactive`. No `Visuals:` path injected → ask once where to put it.
Never scaffold inside a repo's tracked tree.

## 5. Media without HeyGen

No `heygen` CLI here, so upstream's free catalog path (bgm, image search, TTS)
is off, and its local Kokoro voice is not installed. Do not suggest installing
either. Use:

| Need | Source |
|---|---|
| image | `npx hyperframes media-use resolve --type image --provider codex --intent "<what>" --project .` (ChatGPT sub, ~60s each) |
| logo | upstream default (theSVG → GitHub avatar → favicon), free |
| sfx | `resolve --type sfx --intent "<what>"` - bundled offline set |
| voiceover | `vd:omnimedia` MiniMax speech (`speech-2.8-hd`) |
| music bed | `vd:omnimedia` Lyria (instrumental only) - or no music. Not MiniMax music: it sings |

Register every file generated outside media-use with its real type
(`--adopt` labels all audio as bgm):

```bash
npx hyperframes media-use resolve --type voice --from <file> --intent "<scene/line>" --project .
```

MiniMax calls cost money: confirm before an agent-initiated call; a
user-requested one just runs.

## 6. Finish

- `npx hyperframes check --snapshots` passes, and look at the PNGs it saves
  under `.hyperframes/artifacts/snapshots/` before calling it done. Upstream examples can fail their own check, so never
  trust a template blindly.
- Skip the HyperFrames desktop app / Framey lines the CLI prints. Mention the
  app only if asked how to keep editing; the Studio preview is enough.
- Report the absolute MP4 path plus duration, resolution, and size from `ffprobe`.
- Hand off:
  - X: `vd:devlog ... no-cover` drafts the post around the MP4 (the video is
    the visual), `vd:twitter` posts it. Keep
    it under 2:20 (X cap for non-Premium accounts).
  - PR: `gh` cannot upload video. Attach it to a release
    (`gh release upload <tag> <mp4>`) or drag it into a PR comment via
    `vd:agent-browser`.
- When the user likes a result, accept upstream's recipe-freeze offer with a
  stable name (`pr-clip`, `release-reel`, `launch-promo`) so the next run of
  that format adopts it in one question.
