---
name: omnimedia
description: Multimodal AI - Gemini for analysis (vision/transcribe/OCR/extract); image generation via Codex (ChatGPT subscription), Gemini/Imagen, OpenRouter, MiniMax; video, speech, music via Gemini + MiniMax.
license: MIT
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
argument-hint: "[file-path] [prompt]"
---

# Omnimedia

Process audio, images, videos, documents using Gemini. Generate images via **Codex (ChatGPT subscription)**, Google/Imagen, OpenRouter, or MiniMax. Generate videos, speech, music via Gemini + MiniMax.

## Setup

```bash
# Google Gemini (analysis + image/video gen)
export GEMINI_API_KEY="your-key"  # https://aistudio.google.com/apikey
# OpenRouter (optional image-generation router / non-Google models)
export OPENROUTER_API_KEY="your-key"  # https://openrouter.ai/settings/keys
# MiniMax (image/video/speech/music gen)
export MINIMAX_API_KEY="your-key"  # https://platform.minimax.io/user-center/basic-information/interface-key
pip install google-genai python-dotenv pillow requests

# Codex CLI (subscription image gen - no API key required)
brew install codex                 # or per https://developers.openai.com/codex/cli
codex login                        # ChatGPT Plus/Pro/Business/Enterprise/Edu
codex login status                 # expects: "Logged in using ChatGPT"
```

### API Key Rotation (Optional)

For high-volume Gemini usage, configure multiple keys:

```bash
export GEMINI_API_KEY="key1"
export GEMINI_API_KEY_2="key2"  # auto-rotates on rate limit
```

## Quick Start

**Verify setup**: `python scripts/check_setup.py`
**Analyze media**: `python scripts/gemini_batch_process.py --files <file> --task <analyze|transcribe|extract>`
**Generate (Codex subscription)**: `python scripts/gemini_batch_process.py --task generate --provider codex --prompt "desc"`
**Generate (Google)**: `python scripts/gemini_batch_process.py --task <generate|generate-video> --prompt "desc"`
**Generate (OpenRouter)**: `python scripts/gemini_batch_process.py --task generate --provider openrouter --model google/gemini-3.1-flash-image-preview --prompt "desc"`
**Generate (MiniMax via provider routing)**: `python scripts/gemini_batch_process.py --task generate --provider minimax --model image-01 --prompt "desc"`
**Generate (MiniMax CLI)**: `python scripts/minimax_cli.py --task <generate|generate-video|generate-speech|generate-music> --prompt "desc"`
**Generate (Codex standalone)**: `python scripts/codex_imagegen.py --prompt "desc" --out out.png`

`--provider auto` cascades **Codex → Google → OpenRouter → MiniMax** for image generation. Codex (ChatGPT subscription) goes first since it doesn't burn paid API quota; on `CodexQuotaExceeded` or `CodexNotAvailable` it falls through to Google, which itself falls back to the OpenRouter equivalent for Gemini image models when Google image generation fails because billing/free-tier access is unavailable.

> Google AI Studio still works for general API usage, but current Gemini/Imagen image models do not have a free tier. If users say "Gemini free", they usually mean AI Studio keys; those keys no longer give free image generation on current models.

> **Stdin support**: Pipe files via stdin for Gemini analysis (auto-detects PNG/JPG/PDF/WAV/MP3).

## Output Handoff

When an omnimedia workflow creates or exports a file, the final response must give the user an openable target:
- Clickable absolute file link: `[out.png](/absolute/path/to/out.png)`
- Plain browser URI when helpful: `file:///absolute/path/to/out.png`
- Repo-relative path only as secondary context: `./docs/assets/out.png`

Do not hand off only `out.png`, `results.json`, or another basename. For multi-file jobs, list each finalized output and any companion artifacts such as transcripts, manifests, thumbnails, or optimized derivatives.

## Models

### Google Gemini / Imagen
- **Image gen**: `gemini-3.1-flash-image-preview` (Nano Banana 2 - DEFAULT), `gemini-2.5-flash-image` (Flash), `gemini-3-pro-image-preview` (Pro 4K), `imagen-4.0-generate-001` (standard), `imagen-4.0-ultra-generate-001` (quality), `imagen-4.0-fast-generate-001` (speed)
- **Video gen**: `veo-3.1-generate-preview` (8s clips with audio)
- **Analysis**: `gemini-2.5-flash` (recommended), `gemini-2.5-pro` (advanced)

### OpenRouter
- **Image gen routing**: use provider-qualified model ids such as `google/gemini-3.1-flash-image-preview`
- **Non-Google alternatives**: e.g. `black-forest-labs/flux.2-flex`
- **Fallbacks**: configure `OPENROUTER_FALLBACK_MODELS=model-a,model-b` to let OpenRouter retry alternative image models

### MiniMax
- **Image gen**: `image-01` (standard), `image-01-live` (enhanced) - $0.03/image, 1-9 batch
- **Video gen (Hailuo)**: `MiniMax-Hailuo-2.3` (1080p), `MiniMax-Hailuo-2.3-Fast` (50% cheaper), `MiniMax-Hailuo-02` (first+last frame), `S2V-01` (subject ref)
- **Speech/TTS**: `speech-2.8-hd` (best), `speech-2.8-turbo` (fast) - 300+ voices, 40+ languages, emotion control
- **Music**: `music-2.5` - 4-minute songs with vocals, synchronized lyrics

### OpenAI Codex (subscription)
- **Image gen**: routed through `$imagegen` inside `codex exec`. Image-model selection is opaque (informally `gpt-image-2` family); not directly choosable.
- **`--model` semantics**: forwards to `codex exec -m` as the **Codex base model** (e.g. `gpt-5.5`, `o3`). NOT an image-model selector - see `references/codex-imagegen.md` for details.
- **Auth**: ChatGPT subscription via `codex login`; no `OPENAI_API_KEY` used.
- **Throughput**: one image per turn, **5–30s latency**; no batch mode. For batch generation, use `--provider minimax` (image-01 supports 1–9 batch).
- **Quota**: image-gen turns burn ~3–5× per-turn budget; on rate limit the auto cascade falls through to Google.

## Scripts

- **`gemini_batch_process.py`**: Multimodal CLI for `transcribe|analyze|extract|generate|generate-video`. Analysis stays on Gemini; image generation can route to Codex, Google, OpenRouter, or MiniMax.
- **`codex_imagegen.py`**: Standalone Codex image-gen wrapper (`codex exec "$imagegen ..."`). Captures PNGs via tmpdir glob; raises `CodexQuotaExceeded` / `CodexNotAvailable` for the unified cascade.
- **`openrouter_generate.py`**: OpenRouter image generation helper with optional fallback model chains.
- **`minimax_cli.py`**: MiniMax CLI for `generate|generate-video|generate-speech|generate-music`. Supports all MiniMax models.
- **`minimax_generate.py`**: MiniMax generation functions (image, video, speech, music). Library for programmatic use.
- **`minimax_api_client.py`**: MiniMax HTTP client, auth, async polling, file download utilities.
- **`media_optimizer.py`**: ffmpeg/Pillow preflight: compress/resize/convert media to stay within API limits.
- **`document_converter.py`**: Gemini-powered PDF/image/Office → markdown converter.
- **`check_setup.py`**: Setup checker for API keys and dependencies.

Use `--help` for options.

## References

Load for detailed guidance:

| Topic | File | Description |
|-------|------|-------------|
| Music | `references/music-generation.md` | Lyria RealTime API for background music generation, style prompts, real-time control, integration with video production. |
| Audio | `references/audio-processing.md` | Audio formats and limits, transcription (timestamps, speakers, segments), non-speech analysis, File API vs inline input, TTS models, best practices, cost and token math, and concrete meeting/podcast/interview recipes. |
| Images | `references/vision-understanding.md` | Vision capabilities overview, supported formats and models, captioning/classification/VQA, detection and segmentation, OCR and document reading, multi-image workflows, structured JSON output, token costs, best practices, and common product/screenshot/chart/scene use cases. |
| Image Gen | `references/image-generation.md` | Imagen 4 and Gemini image model overview, generate_images vs generate_content APIs, aspect ratios and costs, text/image/both modalities, editing and composition, style and quality control, safety settings, best practices, troubleshooting, and common marketing/concept-art/UI scenarios. |
| Video | `references/video-analysis.md` | Video analysis capabilities and supported formats, model/context choices, local/inline/YouTube inputs, clipping and FPS control, multi-video comparison, temporal Q&A and scene detection, transcription with visual context, token and cost guidance, and optimization/best-practice patterns. |
| Video Gen | `references/video-generation.md` | Veo model matrix, text-to-video and image-to-video quick start, multi-reference and extension flows, camera and timing control, configuration (resolution, aspect, audio, safety), prompt design patterns, performance tips, limitations, troubleshooting, and cost estimates. |
| MiniMax | `references/minimax-generation.md` | MiniMax image (image-01), video (Hailuo 2.3), speech (TTS 2.8), and music (2.5) generation APIs. Endpoints, models, parameters, async workflows, pricing, rate limits, voice library, and examples. |

| Codex | `references/codex-imagegen.md` | Codex CLI image generation via ChatGPT subscription quota. Setup, invocation, model semantics (`-m` is the Codex base model, not image), quota math, latency expectations, cascade behavior, limits, and live-smoke commands. |

## Limits

**Formats**: Audio (WAV/MP3/AAC, 9.5h), Images (PNG/JPEG/WEBP, 3.6k), Video (MP4/MOV, 6h), PDF (1k pages)
**Size**: 20MB inline, 2GB File API
**Important:**
- If you are going to generate a transcript of the audio, and the audio length is longer than 15 minutes, the transcript often gets truncated due to output token limits in the Gemini API response. To get the full transcript, you need to split the audio into smaller chunks (max 15 minutes per chunk) and transcribe each segment for a complete transcript.
- If you are going to generate a transcript of the video and the video length is longer than 15 minutes, use ffmpeg to extract the audio from the video, truncate the audio to 15 minutes, transcribe all audio segments, and then combine the transcripts into a single transcript.

**Transcription Output Requirements:**
- Format: Markdown
- Metadata: Duration, file size, generated date, description, file name, topics covered, etc.
- Parts: from-to (e.g., 00:00-00:15), audio chunk name, transcript, status, etc.
- Transcript format:
  ```
  [HH:MM:SS -> HH:MM:SS] transcript content
  [HH:MM:SS -> HH:MM:SS] transcript content
  ...
  ```

## Resources

- [Gemini API Docs](https://ai.google.dev/gemini-api/docs/)
- [Gemini Pricing](https://ai.google.dev/pricing)
- [OpenRouter Image Generation Docs](https://openrouter.ai/docs/guides/overview/multimodal/image-generation)
- [OpenRouter Provider Routing](https://openrouter.ai/docs/features/provider-routing)
- [MiniMax API Docs](https://platform.minimax.io/docs/api-reference/api-overview)
- [MiniMax Pricing](https://platform.minimax.io/pricing)
- [Codex CLI features](https://developers.openai.com/codex/cli/features)
