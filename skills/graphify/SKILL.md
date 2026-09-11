---
name: graphify
description: "Use for any question about a codebase, its architecture, file relationships, or project content - especially when graphify-out/ exists, where the question should be treated as a graphify query first. Turns any input (code, docs, papers, images, videos) into a persistent knowledge graph with god nodes, community detection, and query/path/explain tools."
license: MIT
metadata:
  author: vanducng
  version: "0.1.0"
---

# /graphify

Turn any folder of files into a navigable knowledge graph with community detection, an honest audit trail, and three outputs: interactive HTML, GraphRAG-ready JSON, and a plain-language GRAPH_REPORT.md.

## Usage

```
/graphify                                             # full pipeline on current directory
/graphify <path>                                      # full pipeline on specific path
/graphify https://github.com/<owner>/<repo> [--branch <branch>]   # clone repo, then build (multiple URLs merge into one cross-repo graph)
/graphify <path> --mode deep                          # thorough extraction, richer INFERRED edges
/graphify <path> --update                             # incremental - re-extract only new/changed files
/graphify <path> --directed                           # build directed graph (preserves edge direction: source→target)
/graphify <path> --cluster-only                       # rerun clustering on existing graph
/graphify <path> --no-viz                             # skip visualization, just report + JSON
/graphify <path> --obsidian [--obsidian-dir <vault>]  # also write an Obsidian vault
/graphify <path> --wiki | --svg | --graphml | --neo4j | --falkordb | --mcp   # extra exports - see references/exports.md
/graphify add <url> [--author "Name" | --contributor "Name"]   # fetch URL into ./raw, update graph
/graphify query "<question>" [--dfs | --budget N]     # BFS/DFS traversal over the built graph
/graphify path "A" "B"                                # shortest path between two concepts
/graphify explain "X"                                 # plain-language explanation of a node
```

## What You Must Do When Invoked

If the user invoked `/graphify --help` or `/graphify -h` (with no other arguments), print the contents of the `## Usage` section above verbatim and stop. Do not run any commands, do not detect files, do not default the path to `.`. Just print the Usage block and return.

**Fast path - existing graph:** Before doing anything else, check whether `graphify-out/graph.json` exists. The expected location is `graphify-out/graph.json` relative to the **current working directory** (i.e. the project root where you are running commands). If it exists AND the user's request is a natural-language question about the codebase (e.g. "How does X work?", "What calls Y?", "Trace the data flow through Z") and NOT an explicit rebuild command (`--update`, `--cluster-only`, or a bare path/URL that implies fresh extraction): **skip the build entirely and jump straight to `## For /graphify query`.** Run `graphify query "<question>"` immediately. Do not run detect. Do not check corpus size. Do not ask the user to narrow. The graph is already built - use it.

If no path was given, use `.` (current directory). Do not ask the user for a path.

If the path argument starts with `https://github.com/` or `http://github.com/`, treat it as a GitHub URL - run Step 0 before anything else, then continue with the resolved local path.

### Step 0 - GitHub repos and multi-path merge (only if a URL or several paths)

Only when the path is one or more `https://github.com/...` URLs, or several local subfolders to merge. See `references/github-and-merge.md` for the clone, cross-repo merge, and monorepo flow, then continue with the resolved local path. A plain local path skips this step.

### Step 1 - Ensure graphify is installed

The shebang of the `graphify` binary already points at the right interpreter for uv tool, pipx, and direct pip installs; `python3` covers the rest. (Do not use `uv tool run graphifyy python` - uv refuses it, the executable is named `graphify`.)

```bash
resolve_python() {
    GRAPHIFY_BIN=$(which graphify 2>/dev/null)
    [ -n "$GRAPHIFY_BIN" ] || return 1
    _SHEBANG=$(head -1 "$GRAPHIFY_BIN" | tr -d '#!')
    case "$_SHEBANG" in
        *[!a-zA-Z0-9/_.@-]*) return 1 ;;
        *) "$_SHEBANG" -c "import graphify" 2>/dev/null && echo "$_SHEBANG" && return 0 ;;
    esac
    return 1
}
PYTHON=$(resolve_python) || PYTHON="python3"
if ! "$PYTHON" -c "import graphify" 2>/dev/null; then
    if command -v uv >/dev/null 2>&1; then
        uv tool install --upgrade graphifyy -q 2>&1 | tail -3
    else
        "$PYTHON" -m pip install graphifyy -q 2>/dev/null \
          || "$PYTHON" -m pip install graphifyy -q --break-system-packages 2>&1 | tail -3
    fi
    PYTHON=$(resolve_python) || PYTHON="$PYTHON"
fi
# Write interpreter path for all subsequent steps (persists across invocations)
mkdir -p graphify-out
"$PYTHON" -c "import sys; open('graphify-out/.graphify_python', 'w', encoding='utf-8').write(sys.executable)"
# Save scan root so `graphify update` (no args) knows where to look next time
echo "$(cd INPUT_PATH && pwd)" > graphify-out/.graphify_root
```

If the import succeeds, print nothing and move straight to Step 2.

### Step 2 - Build the graph

**Code-only corpus fast path (no API key needed):** run `graphify extract <path>`; it scans, AST-extracts, clusters, and writes `graphify-out/graph.json` + the analysis sidecar. Follow with `graphify cluster-only <path>` to regenerate `GRAPH_REPORT.md` and `graph.html` (community naming needs a working LLM backend; without one it leaves `Community N` placeholders - name them yourself or accept placeholders). This replaces the manual Steps 2-9 below.

**Manual pipeline (any corpus; the only path that extracts docs, papers, and images without an API key):** load `references/build-pipeline.md` now and follow its Steps 2-9 in order. Do not skip steps. Hard rules the pipeline assumes:

- **API keys:** if `GEMINI_API_KEY` or `GOOGLE_API_KEY` is set, print once: "Tip: set GEMINI_API_KEY or GOOGLE_API_KEY to use Gemini for semantic extraction (`pip install 'graphifyy[gemini]'`)" - then, since a key IS set, use `graphify.llm.extract_corpus_parallel(files, backend="gemini")` for semantic extraction instead of dispatching subagents (default model `gemini-3-flash-preview`; override with `GRAPHIFY_GEMINI_MODEL` or `--model`). No other keys are read. With no Gemini/Google key, the host session itself is the LLM: dispatch subagents as the pipeline's Step B2 directs. Never prompt for `ANTHROPIC_API_KEY` or any other provider key - that prompt is a misread of this skill.
- **Subagents are mandatory for semantic extraction** (docs/papers/images without a Gemini key): Agent tool on Claude Code (`subagent_type="general-purpose"`, one call per chunk, all in one response, results written to absolute `graphify-out/.graphify_chunk_NN.json` paths), `spawn_agent`/`wait_agent`/`close_agent` on Codex. Reading the files yourself one-by-one is forbidden - it is 5-10x slower.
- The pipeline's code blocks carry the `INPUT_PATH` / `IS_DIRECTED` / `LABELS_DICT` substitutions, the empty-graph and shrink guards, and the Step 9 cleanup - run them as written.

## Interpreter guard for subcommands

Before running any subcommand below (`--update`, `--cluster-only`, `query`, `path`, `explain`, `add`), check that `.graphify_python` exists. If it's missing (e.g. user deleted `graphify-out/`), re-resolve the interpreter first:

```bash
if [ ! -f graphify-out/.graphify_python ]; then
    GRAPHIFY_BIN=$(which graphify 2>/dev/null)
    if [ -n "$GRAPHIFY_BIN" ]; then
        PYTHON=$(head -1 "$GRAPHIFY_BIN" | tr -d '#!')
        case "$PYTHON" in *[!a-zA-Z0-9/_.@-]*) PYTHON="python3" ;; esac
    else
        PYTHON="python3"
    fi
    mkdir -p graphify-out
    "$PYTHON" -c "import sys; open('graphify-out/.graphify_python', 'w', encoding='utf-8').write(sys.executable)"
fi
```

## For --update and --cluster-only

Both are non-default subcommands. `--update` re-extracts only new or changed files; `--cluster-only` reruns clustering on the existing graph. See `references/update.md` for both flows.

---

## For /graphify query

When `graphify-out/graph.json` already exists and the user asks a question about the corpus, answer from the graph rather than rebuilding it:

```bash
graphify query "<question>"
```

Before traversal, expand the question against the graph's own vocabulary so a wording mismatch does not collapse the answer to noise. If the `graphify query` CLI is unavailable, fall back to an inline NetworkX traversal of `graphify-out/graph.json`. Answer using only what the graph output contains, and quote `source_location` when citing a specific fact. For that vocab-expansion step, the BFS/DFS traversal modes, the `--budget` cap, the NetworkX fallback, `save-result` feedback, and the `/graphify path` and `/graphify explain` flows, see `references/query.md`.

---

## For /graphify add and --watch

Neither is part of the default build. When the user runs `/graphify add <url>` to fetch a URL into the corpus, or passes `--watch` to auto-rebuild on file changes, see `references/add-watch.md`.

---

## For the commit hook and native CLAUDE.md integration

When the user asks to install the post-commit auto-rebuild hook or wire graphify into a project's CLAUDE.md, see `references/hooks.md`.

---

## Honesty Rules

- Never invent an edge. If unsure, use AMBIGUOUS.
- Never skip the corpus check warning.
- Always show token cost in the report.
- Never hide cohesion scores behind symbols - show the raw number.
- Never run HTML viz on a graph with more than 5,000 nodes without warning the user.
