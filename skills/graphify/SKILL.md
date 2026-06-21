---
name: graphify
description: "Build queryable knowledge graphs from code, docs, papers, and images. Use for codebase understanding, architecture analysis, cross-file relationship discovery, and token-efficient navigation. Triggers: 'graphify', 'build a knowledge graph', 'map this codebase', 'find god nodes', 'understand the architecture'."
license: MIT
argument-hint: "[path] [--mcp|--report|--watch]"
metadata:
  author: vanducng
  version: "1.0.0"
---

# Graphify — Knowledge Graph Builder

Turn any folder of code, docs, papers, or images into a queryable knowledge graph. Uses tree-sitter AST for code (20 languages), Whisper for audio/video, and LLM subagents for documents. Drives the `graphifyy` CLI under the hood.

## When to Use

- Understanding an unfamiliar codebase's architecture before planning
- Discovering cross-file relationships and dependency chains
- Finding "god nodes" (most-connected concepts) in large projects
- Navigating by structure instead of grepping every file
- Preparing a context-efficient codebase representation (far fewer tokens than raw files)

Reach for `vd:scout` instead for a quick file search, and `vd:repomix` for a full raw-context dump. Graphify sits between them: a structured, queryable map.

## Installation

**Note:** The PyPI package is `graphifyy` (double-y). Other `graphify*` packages on PyPI are unaffiliated. `graphify install` downloads tree-sitter grammars for AST parsing.

```bash
# Core install
pip install graphifyy
graphify install

# With MCP server support
pip install 'graphifyy[mcp]'

# Full install (MCP + PDF + video + office + Leiden community detection)
pip install 'graphifyy[all]'
```

**Requirements:** Python 3.10+

## Quick Start

```bash
graphify .                  # build graph from current directory
graphify /path/to/project   # build from a specific path
graphify . --watch          # auto-rebuild on file changes
```

## Output Artifacts

| File | Purpose |
|------|---------|
| `graphify-out/graph.html` | Interactive visualization with search + community filtering |
| `graphify-out/GRAPH_REPORT.md` | God nodes, surprising connections, suggested questions |
| `graphify-out/graph.json` | Persistent graph for queries across sessions |
| `graphify-out/cache/` | SHA256-based incremental updates (only reprocesses changed files) |

## MCP Server Mode

Expose the graph as an MCP server for the agent to query directly:

```bash
python -m graphify.serve graphify-out/graph.json
```

### MCP Tools Available

| Tool | Purpose |
|------|---------|
| `query_graph` | Search for concepts and relationships |
| `get_node` | Get details of a specific node |
| `get_neighbors` | Find related concepts |
| `shortest_path` | Find connection path between two concepts |

### MCP Setup

Add to `$HOME/.claude/.mcp.json`:
```json
{
  "mcpServers": {
    "graphify": {
      "command": "python",
      "args": ["-m", "graphify.serve", "graphify-out/graph.json"]
    }
  }
}
```

## Three-Pass Architecture

1. **AST extraction (local, no API)** — tree-sitter parses code in 20 languages deterministically
2. **Audio/video transcription (local)** — Whisper runs on-device for media files
3. **Semantic extraction (API)** — LLM subagents process docs, papers, images in parallel

### Supported Languages (tree-sitter)

Python, JavaScript, TypeScript, Go, Rust, Java, C, C++, Ruby, C#, Kotlin, Scala, PHP, Swift, Lua, Zig, PowerShell, Elixir, Objective-C, Julia

## Confidence Tagging

Relationships in the graph are tagged by provenance:

| Tag | Meaning |
|-----|---------|
| `EXTRACTED` | Directly from AST (imports, function calls, class inheritance) |
| `INFERRED` | LLM-derived with confidence score |
| `AMBIGUOUS` | Uncertain — needs human verification |

## Workflow Integration

### Before Planning

```bash
graphify .   # then read GRAPH_REPORT.md → understand architecture → better vd:plan
```

### With Scout

```bash
graphify .                 # graph for high-level structure
# vd:scout "auth module"   # then drill to specific files
```

### Incremental Updates

Graph rebuilds are incremental — only changed files get reprocessed. Cache at `graphify-out/cache/` tracks file hashes.

## Privacy

- **Code:** Processed locally via tree-sitter AST. No file contents leave your machine.
- **Audio/Video:** Transcribed locally via Whisper.
- **Docs/Images:** Sent to your configured model provider for semantic extraction.

## Limitations

- First build on large codebases can be slow (AST parsing + LLM calls)
- Semantic extraction quality depends on the underlying model
- Neo4j integration requires separate setup (`pip install 'graphifyy[neo4j]'`)
- Leiden community detection requires `pip install 'graphifyy[leiden]'`

## Workflow Position

**Typically precedes:** `vd:plan` (understand architecture before planning)
**Related:** `vd:scout` (quick file search), `vd:repomix` (full context dump), `vd:gkg` (semantic symbol navigation)
