---
title: "Install"
---

This page covers two layers:

- Install the standalone `vd` CLI, which manages skills across agent hosts.
- Install this skill catalog into Claude Code or Codex.

Current verified CLI release: `vd-cli` `v3.13.7`, published from `vanducng/vd-cli` on 2026-08-10.

Sources: `README.md`, `skills.toml`, `vd install --help`, `gh release view v3.13.7 --repo vanducng/vd-cli`.

## Install The `vd` CLI

### macOS

Homebrew is the recommended path:

```sh
brew install vanducng/tap/vd
vd --version
```

Apple Silicon and Intel tarballs are also published as `vd_darwin_arm64.tar.gz` and `vd_darwin_x86_64.tar.gz`.

### Linux

Use Homebrew on Linux, Go, or a release tarball:

```sh
brew install vanducng/tap/vd
```

```sh
go install github.com/vanducng/vd-cli/v2/cmd/vd@latest
```

Release tarballs are published as `vd_linux_x86_64.tar.gz` and `vd_linux_arm64.tar.gz`.

### Windows

Windows x86_64 has a prebuilt zip:

```powershell
$version = "v3.13.7"
$asset = "vd_windows_x86_64.zip"
Invoke-WebRequest "https://github.com/vanducng/vd-cli/releases/download/$version/$asset" -OutFile $asset
Expand-Archive $asset -DestinationPath ".\vd" -Force
.\vd\vd.exe --version
```

Windows ARM64 also has a prebuilt zip:

```powershell
$version = "v3.13.7"
$asset = "vd_windows_arm64.zip"
Invoke-WebRequest "https://github.com/vanducng/vd-cli/releases/download/$version/$asset" -OutFile $asset
Expand-Archive $asset -DestinationPath ".\vd" -Force
.\vd\vd.exe --version
```

## Install The Skill Catalog

### Claude Code: Plugin Mode

Inside Claude Code:

```text
/plugin marketplace add vanducng/skills
/plugin install vd@vd-skills
```

Update later:

```text
/plugin marketplace update vd-skills
/plugin install vd@vd-skills
```

The CLI can print and run the same flow:

```sh
vd install claude --dry-run
vd install claude
```

### Claude Code: Dev Symlinks

Use this when you are editing a skill and want Claude Code to read the working tree directly:

```sh
vd install claude --dev --dry-run
vd install claude --dev
```

This links each local skill into `$HOME/.claude/skills`.

### Codex: User Scope

User-scope Codex install links every local skill into `$HOME/.agents/skills`:

```sh
vd install codex --dry-run
vd install codex
```

### Codex: Repo Scope

Repo-scope Codex install links into `.agents/skills` inside this repo:

```sh
vd install codex --scope repo --dry-run
vd install codex --scope repo
```

:::tip
Use repo scope when a project should carry the same skill set for every Codex session opened from that checkout.
:::

## Invocation Names

:::note
Documentation uses canonical IDs such as `vd:research`, `vd:plan`, and `vd:ship`. Claude Code and Codex expose different invocation prefixes in their UIs, but the skill identity is the same catalog namespace: Claude Code invokes `/vd:research`, Codex invokes `$vd:research` (or activates the skill implicitly when your prompt matches its description).
:::

## Verify The Install

```sh
vd --version
vd list
vd doctor
bash scripts/validate.sh
```
