---
title: "Install"
---

This page covers two layers:

- Install the standalone `vd` CLI, which manages skills across agent hosts.
- Install this skill catalog into Claude Code, Codex, or Factory Droid.

Install the latest `vd-cli` release. Factory Droid support requires `vd-cli` v3.13.0 or newer.

## Install The `vd` CLI

### macOS

Homebrew is the recommended path:

```sh
brew install vanducng/tap/vd
vd --version
```

Apple Silicon and Intel tarballs are also published as `vd_darwin_arm64.tar.gz` and `vd_darwin_x86_64.tar.gz`.

### Linux

Use Homebrew on Linux, the install script, or a release tarball:

```sh
brew install vanducng/tap/vd
```

```sh
curl -fsSL https://raw.githubusercontent.com/vanducng/vd-cli/main/install.sh | sh
```

Release tarballs are published as `vd_linux_x86_64.tar.gz` and `vd_linux_arm64.tar.gz`.

### Windows

Windows x86_64 has a prebuilt zip:

```powershell
$version = (Invoke-RestMethod "https://api.github.com/repos/vanducng/vd-cli/releases/latest").tag_name
$asset = "vd_windows_x86_64.zip"
Invoke-WebRequest "https://github.com/vanducng/vd-cli/releases/download/$version/$asset" -OutFile $asset
Expand-Archive $asset -DestinationPath ".\vd" -Force
.\vd\vd.exe --version
```

For Windows ARM64, use the same commands with `$asset = "vd_windows_arm64.zip"`.

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

### Factory Droid: User Scope

User scope installs the catalog into `$HOME/.factory/skills`:

```sh
vd install droid --dry-run
vd install droid
```

### Factory Droid: Repo Scope

Repo scope installs the catalog into `.factory/skills` inside the current repo:

```sh
vd install droid --scope repo --dry-run
vd install droid --scope repo
```

On Unix, vd uses relative symlinks by default. On Windows, it creates copies; rerun with `--force` to refresh an existing destination. Restart Droid and run `/skills` to verify discovery.

## Invocation Names

:::note
Documentation uses canonical IDs such as `vd:research`, `vd:plan`, and `vd:ship`. Agent UIs expose different invocation forms, but the catalog identity stays the same: Claude Code invokes `/vd:research`, Codex invokes `$vd:research`, and Droid invokes the installed folder as `/research`. Codex and Droid can also activate a skill implicitly when the prompt matches its description.
:::

## Verify The Install

```sh
vd --version
vd list
vd doctor
bash scripts/validate.sh
```
