# Codex Image Generation (`--provider codex`)

Generate images via the OpenAI Codex CLI's built-in `$imagegen` skill, billed against your **ChatGPT subscription quota** instead of an OpenAI API key. The `/vd:omnimedia` skill ships `scripts/codex_imagegen.py` as a standalone wrapper and exposes the same path through the unified `--provider codex` switch in `gemini_batch_process.py`.

## Setup

```bash
# Install Codex CLI
brew install codex
# or follow https://developers.openai.com/codex/cli

# Authenticate via your ChatGPT account (Plus/Pro/Business/Enterprise/Edu)
codex login

# Verify
codex login status   # expects: "Logged in using ChatGPT"
codex --version      # tested on codex-cli 0.128.0
```

No `OPENAI_API_KEY` is read or used by this provider — it strictly uses the subscription auth from `~/.codex/auth.json`.

## Invocation

### Standalone

```bash
python scripts/codex_imagegen.py \
  --prompt "A red cube on a white background, photorealistic" \
  --out /tmp/cube.png
```

### Through the unified provider switch

```bash
python scripts/gemini_batch_process.py --task generate --provider codex \
  --prompt "abstract waves" --output /tmp/waves.png
```

### Auto cascade

```bash
python scripts/gemini_batch_process.py --task generate --provider auto \
  --prompt "..." --output /tmp/x.png
```

`--provider auto` now tries **codex → google → openrouter → minimax** for image generation. The active provider is logged to stderr (`[auto] using codex`).

## Models

The wrapper's `--model` flag forwards to `codex exec -m`, which selects the **Codex base model** (e.g. `gpt-5.5`, `o3`, `o4-mini`). It does **not** select an image-generation model — the image model (informally `gpt-image-2` / `gpt-image-1.5` / `gpt-image-1` / `gpt-image-1-mini`) is chosen internally by the `$imagegen` skill and isn't directly addressable from this wrapper. Common pitfall: passing `--model gpt-image-2` will fail because `codex exec -m` only accepts Codex base models.

If `--model` is omitted (or auto-detected to a non-Codex model like `gemini-3.1-flash-image-preview`), the wrapper drops the flag and lets Codex pick its default base model.

## Quota math

OpenAI doesn't publish per-image token math. The only public guidance is that image-generation turns burn **3–5× the per-turn budget** of text-only turns. Recent ChatGPT Plus/Pro changes raised the rate-limit ceiling, but exhaustion still happens on heavy days; on quota the wrapper raises `CodexQuotaExceeded`, which the `auto` cascade catches and falls through.

## Latency

Expect **5–30 seconds per image**. Codex runs the full agent loop, not a thin API call. For tight inner loops (batch generation, design iteration) prefer `--provider gemini` (Imagen 4 Flash) or `--provider minimax` (image-01 batch).

Codex is **one image per turn** — no batch mode.

## Cascade behavior

| Codex outcome | Auto cascade action |
|---|---|
| Success | Use result; print `[auto] using codex` |
| `CodexNotAvailable` (CLI missing or not logged in) | Silent fall-through to Google |
| `CodexQuotaExceeded` (rate-limit / 429) | `[auto] codex codex_quota, falling through to next provider`; advance to Google |
| `CodexError` (any other failure) | `[auto] codex codex_error, falling through to next provider`; advance to Google |

Explicit `--provider codex` does **not** fall through — you get the error directly so you can handle it.

## Output capture

The wrapper does not parse Codex stdout. It uses two layers:

1. **Filesystem glob (primary)** — runs `codex exec -C <tmpdir>` and looks for `<tmpdir>/*.png`, taking the newest mtime.
2. **Last-message file (secondary)** — `codex exec -o <tmpdir>/last.txt` captures the agent's final message; if no PNG was found in the tmpdir, the wrapper parses `last.txt` and copies the path on its last line.

This avoids brittleness when Codex output formats drift between minor versions.

## Limits and known issues

- **Image-to-image edits via Codex `-i/--image`** are deferred to v2. Codex CLI supports `--image FILE...` for input attachments, but `$imagegen`-style edits aren't wired through this wrapper yet.
- **No batch mode**. One image per `codex exec` turn. Cascading to MiniMax (`image-01`, 1–9 batch) is the path for batch generation.
- **No streaming progress**. The wrapper blocks until Codex finishes (typical 5–30s).
- **Sandbox**: runs with `--sandbox workspace-write` inside a tmpdir; no host filesystem writes outside the wrapper's `--out` target.

## Testing

```bash
# Unit + mocked tests (default — fast)
pytest scripts/tests/test_codex_imagegen.py

# Provider-routing cascade tests
pytest scripts/tests/test_provider_routing.py

# Live smoke (one real PNG generation against subscription quota)
OMNIMEDIA_SMOKE_CODEX=1 pytest scripts/tests/test_codex_imagegen.py::test_live_codex_generation -v
```

## Resources

- [Codex CLI features](https://developers.openai.com/codex/cli/features)
- [OpenAI image-generation tool docs](https://developers.openai.com/api/docs/guides/tools-image-generation)
- [ChatGPT plans + quotas](https://openai.com/chatgpt/pricing/)
