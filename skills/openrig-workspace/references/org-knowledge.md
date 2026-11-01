# Org knowledge: where the rules live

This page points. It restates nothing, so it cannot drift.

| You need | Go to |
|---|---|
| How an org's knowledge tree is laid out, what a page and a daily entry look like, anchors and citations, lifecycle, who may write what | the workspace `okf-v2` skill (the org contract) |
| Which PARA bucket a thing belongs in; the weekly and monthly reviews | the `para` skill |
| Setting up, running or auditing an org's watch rig | [org-watch-rig.md](org-watch-rig.md) |
| A seat's job | its role file, named by the rig template |

## What a seat reads first

`kb context <org>`, the workspace command. It is the only read path: the org's entry point, then `kb context <org> <page-id>` for one page, or `kb context <org> --day <YYYY-MM-DD>` for one closed day. Do not browse the tree.

## The commands, by name

| Command | For |
|---|---|
| `kb context`, `kb map` | reading |
| `kb append`, `kb idea` | a collector records one event, or the operator adds an idea |
| `kb due <org> <seat>` | what a seat does this tick |
| `kb cursor set` | a collector moves its cursor |
| `kb page write`, `kb day close`, `kb proposals add`, `kb log add`, `kb dream ...` | the dream's journaled writes |
| `kb lint`, `kb index`, `kb gate` | checks and generated files; the gate belongs to the sync job |
| `kb init` | a new org tree |

Run `kb <command> --help` for flags. A command that exits non-zero is a stop: do not edit a file by hand to get around it.
