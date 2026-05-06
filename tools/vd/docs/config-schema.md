# skills.toml — Configuration Schema Reference

`skills.toml` lives at the repo root and is created by `vd init`. It is the single source of truth for which skills are tracked, where they come from, and how the Claude Code plugin is emitted.

---

## [meta]

Top-level metadata for the manifest and the generated marketplace entry.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `version` | int | yes | `1` | Schema version. Currently only `1` is valid. |
| `name` | string | no | seeded from `marketplace.json` | Marketplace registry name (e.g. `vanducng-skills`). |
| `description` | string | no | seeded from `marketplace.json` | Top-level marketplace description. |
| `owner_name` | string | no | seeded from `marketplace.json` | Owner display name. |
| `owner_url` | string | no | seeded from `marketplace.json` | Owner URL (GitHub profile, etc.). |
| `homepage` | string | no | falls back to `owner_url` | Fallback homepage for plugins that don't set one. |

**Example:**
```toml
[meta]
  version     = 1
  name        = "vanducng-skills"
  description = "Personal Claude Code skill library"
  owner_name  = "Duc Nguyen"
  owner_url   = "https://github.com/vanducng"
```

---

## [sources.\<name\>]

Declares a remote skill source. One block per upstream repository. The `<name>` key is referenced from `[skills.*]` entries.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `type` | string | yes | — | `"git"` is the only supported value. `"local"` is reserved. |
| `url` | string | yes | — | Full HTTPS URL of the upstream Git repo. |
| `ref` | string | no | `"main"` | Branch, tag, or full commit SHA to fetch. |

**Example:**
```toml
[sources.browserbase]
  type = "git"
  url  = "https://github.com/browserbase/skills"
  ref  = "main"
```

**Auto-registration:** when `vd add owner/repo/path` is used and `owner` is not declared in `[sources]`, `vd` auto-registers a GitHub source as `https://github.com/owner/repo`. The `[sources.*]` block is written to `skills.toml` automatically.

---

## [skills.\<name\>]

Declares one tracked skill. The `<name>` key becomes the local directory name under `skills/`.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `source` | string | conditional | — | Must match a `[sources.*]` key. Required unless `mode = "detached"`. |
| `path` | string | conditional | — | Sub-path inside the upstream repo (e.g. `skills/browser`). Required unless `mode = "detached"`. |
| `mode` | string | yes | `"tracked"` | Tracking mode: `"tracked"`, `"pinned"`, or `"detached"`. |
| `pin` | string | conditional | — | Full or short commit SHA. Required when `mode = "pinned"`. |

### Mode values

| Mode | Behavior |
|------|----------|
| `tracked` | `vd sync` / `vd update` will fetch upstream HEAD. Dirty-check still applies. |
| `pinned` | `vd sync` checks out the exact SHA in `pin`. `vd update` skips this skill. |
| `detached` | `vd sync` skips entirely. The `skills/<name>/` directory is managed manually. |

**Examples:**
```toml
[skills.browser]
  source = "browserbase"
  path   = "skills/browser"
  mode   = "tracked"

[skills.old-version]
  source = "browserbase"
  path   = "skills/browser"
  mode   = "pinned"
  pin    = "abc1234f"

[skills.my-local-skill]
  mode = "detached"
```

---

## [targets.claude]

Controls how `vd build` emits the Claude Code plugin files (`.claude-plugin/marketplace.json` and `.claude-plugin/plugin.json`).

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `mode` | string | no | `"bundle"` | `"bundle"` (one plugin wrapping all skills) or `"per-skill"` (one plugin entry per skill). |

**Note:** `"bundle"` is the safe default. It preserves byte-equal output on first run when seeded from a live `marketplace.json`. Do not change to `"per-skill"` on `main` — it will alter all existing plugin install paths.

---

## [targets.claude.bundle]

Only honored when `[targets.claude].mode = "bundle"`. Controls the metadata for the single emitted plugin.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | no | seeded from `marketplace.json` | Plugin name (e.g. `"vd"`). |
| `version` | string | no | seeded from `marketplace.json` | Plugin version string. |
| `description` | string | no | seeded from `marketplace.json` | Plugin description shown in marketplace. |
| `plugin_description` | string | no | falls back to `description` | Description used in `plugin.json` (often differs). |
| `source` | string | no | `"./"` | Relative or absolute source path in the marketplace entry. |
| `category` | string | no | `"utilities"` | Marketplace category. |
| `homepage` | string | no | `meta.owner_url` | Plugin homepage URL. |
| `license` | string | no | `"MIT"` | SPDX license identifier. |
| `version_strategy` | string | no | `"manual"` | `"manual"` (use `version` field) or `"lock-sha"` (use short SHA from lock). |

**Example:**
```toml
[targets.claude.bundle]
  name               = "vd"
  version            = "0.5.1"
  description        = "Personal Claude Code skill library"
  plugin_description = "Duc's skill library: research, planning, coding, and more."
  source             = "./"
  category           = "utilities"
  homepage           = "https://github.com/vanducng/skills"
  license            = "MIT"
  version_strategy   = "manual"
```

---

## [targets.agents]

Reserved for future agent-specific emission. Currently a no-op placeholder. The `.agents/skills/` symlink directory is always emitted by `vd build` regardless of this section.

---

## [plugin.\<name\>]

Per-skill metadata overrides applied during `vd build`. The `<name>` must match a key in `[skills.*]`. Overrides take highest priority — they override both `SKILL.md` frontmatter and lock-derived defaults.

Used primarily in `"per-skill"` mode to customize individual plugin entries. Also effective in `"bundle"` mode for `plugin.<bundle-name>`.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `description` | string | no | — | Override the plugin description. |
| `version` | string | no | — | Override version (takes priority over lock SHA short). |
| `category` | string | no | — | Override marketplace category. |
| `homepage` | string | no | — | Override homepage URL. |

**Example:**
```toml
[plugin.browser]
  description = "Stagehand-powered browser automation via Browserbase."
  category    = "automation"
  homepage    = "https://github.com/browserbase/skills"
```

---

## Precedence rules

For plugin metadata resolution (highest → lowest):

1. `[plugin.<name>]` overrides
2. `SKILL.md` YAML frontmatter (`name`, `description`)
3. Lock-derived defaults (SHA, mtime)
4. `[targets.claude.bundle]` defaults (for bundle mode)
5. Hard-coded fallbacks (`version = "0.0.0"`, `category = "utilities"`)

---

## Complete example

```toml
# skills.toml — vd manifest

[meta]
  version     = 1
  name        = "vanducng-skills"
  description = "Duc's personal Claude Code skill library"
  owner_name  = "Duc Nguyen"
  owner_url   = "https://github.com/vanducng"

[sources.browserbase]
  type = "git"
  url  = "https://github.com/browserbase/skills"
  ref  = "main"

[skills.browser]
  source = "browserbase"
  path   = "skills/browser"
  mode   = "tracked"

[skills.browser-trace]
  source = "browserbase"
  path   = "skills/browser-trace"
  mode   = "pinned"
  pin    = "2a3bbb3b"

[skills.research]
  mode = "detached"

[targets.claude]
  mode = "bundle"

[targets.claude.bundle]
  name             = "vd"
  version          = "0.5.1"
  description      = "Personal Claude Code skill library"
  source           = "./"
  category         = "utilities"
  homepage         = "https://github.com/vanducng/skills"
  license          = "MIT"
  version_strategy = "manual"

[plugin.browser]
  description = "Stagehand-powered browser automation."
  category    = "automation"
```
