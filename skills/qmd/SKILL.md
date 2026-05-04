---
name: qmd
description: "Local hybrid search (BM25 + optional vector + LLM rerank) for any Markdown corpus — personal notes, design-system catalogs, doc trees, meeting transcripts. Use this skill whenever the user wants to search/find/retrieve content from a Markdown collection, asks 'where did I write about X', references a knowledge base, or needs to feed grounded snippets to an agent. Wraps the upstream `qmd` CLI (github.com/tobi/qmd) with sensible defaults: prefer fast `qmd search` (instant, no model load), avoid `qmd query`/`qmd vsearch` unless explicitly asked (multi-GB model downloads + slow cold starts)."
license: MIT
argument-hint: "<query> [-c <collection>] [-n <count>]"
metadata:
  author: vanducng
  version: "1.0.0"
  upstream: "https://github.com/tobi/qmd"
  acknowledgments: "Approach guidance inspired by https://github.com/levineam/qmd-skill"
---

# qmd

Local Markdown search engine: BM25 + vector + optional LLM reranking, all running on-device. This skill teaches Claude how to use it well — what mode to pick, what flags matter, what to avoid.

## Scope

**Handles:** searching indexed Markdown collections, retrieving documents by path/docid/glob, registering new collections, refreshing the index.

**Does NOT handle:** code search (use `grep`/`rg`), web search, structured DB queries, vector embeddings of non-Markdown formats.

## Install (one-time)

```bash
# Bun (recommended by upstream)
bun install -g https://github.com/tobi/qmd

# OR npm
npm install -g @tobilu/qmd
```

Verify: `qmd --version`. Requires `bun` (or Node ≥18) and `sqlite` (preinstalled on macOS).

## Mode selection — pick the cheapest mode that works

| Mode | Speed | Model load? | Use for |
|---|---|---|---|
| `qmd search` | instant | none | **default** — keyword/BM25 lookup |
| `qmd vsearch` | ~1 min cold | ~334MB embedding model | semantic similarity when keywords fail |
| `qmd query` | slowest | +1.28GB rerank LLM | hybrid — only if user explicitly demands "best quality" and accepts wait |

**Heuristic:** start with `qmd search`. If results are empty or noisy, escalate to `qmd vsearch`. Never start with `qmd query` — its multi-GB downloads surprise users on first run, and BM25 is sufficient for most collections under ~10k docs.

## Setup a new collection

```bash
qmd collection add /path/to/markdown/tree --name <my-coll> --mask "**/*.md"
qmd collection list                             # verify
qmd embed                                       # one-time, only if you need vsearch/query
```

Embedding is **opt-in** — don't run it unless the user wants semantic search. It downloads a ~334MB model and takes minutes on first run.

## Search recipes

### Default — fast keyword search

```bash
qmd search "<query>" -c <collection> -n 5
```

### Top-N file paths only (agent-friendly)

```bash
qmd search "<query>" -c <collection> --files -n 10
# Output rows: #color,score,qmd://collection/path/to/file.md
```

### JSON for structured downstream parsing

```bash
qmd search "<query>" -c <collection> --json -n 10
```

### Threshold-filtered "all relevant"

```bash
qmd search "<query>" -c <collection> --all --files --min-score 0.3
```

### Multi-token query — split if BM25 returns nothing

`qmd search` requires all tokens to co-occur in a chunk. With 4+ keywords this often returns zero. Workaround: issue per-token searches and aggregate by vote count. (See `vd:open-design`'s `qmd_vote_search` for a worked example.)

## Retrieval

```bash
qmd get "path/to/file.md"               # full text by path
qmd get "#abc123"                       # by docid (shown in search results)
qmd get "path/to/file.md" --full        # explicit full content
qmd multi-get "journals/2025-05*.md"    # glob batch
qmd multi-get "doc1.md, doc2.md, #abc"  # comma list
```

## Maintenance

```bash
qmd status            # collection health, doc counts, index freshness
qmd update            # re-index changed files (fast — for keyword search)
qmd embed             # refresh embeddings (slow — only if using vsearch/query)
```

For collections that change often, schedule `qmd update` hourly via cron. Reserve `qmd embed` for nightly or on-demand refreshes.

## Useful flags (quick reference)

- `-n <num>` — number of results
- `-c, --collection <name>` — restrict to one collection
- `--all --min-score <num>` — return everything above a threshold
- `--json` — structured output
- `--files` — file paths + scores only
- `--full` — full document content (with `get`/`multi-get`)

## Hard rules

- **Default to `qmd search`.** Only escalate to `vsearch`/`query` when the user accepts a slow cold start and (for `query`) a 1.28GB model download.
- **Never run `qmd embed` silently.** It's a long-running operation that downloads models. Tell the user before running it.
- **Always namespace collection names** with a project-specific prefix (e.g. `od-skills`, not just `skills`) to avoid colliding with the user's other collections.
- **Use `--files` or `--json`** when piping into other scripts; the default human-readable output has color codes and snippets that break parsing.

## Composes well with

- **`vd:open-design`** — auto-detects qmd and uses it for skill/design-system catalog search.
- Any other vd skill that needs to query a curated Markdown corpus — wrap `qmd search` with collection-specific defaults rather than re-implementing search.

## Security

This skill only invokes the upstream `qmd` CLI on local file paths. It does not send queries or content to any network service (qmd is fully on-device). Refuse to register a collection pointing at sensitive directories (e.g. `~/.ssh`, `~/Library/Keychains`) without explicit user confirmation. Do not echo `qmd get --full` output of files outside the user's working tree without their explicit ask.
