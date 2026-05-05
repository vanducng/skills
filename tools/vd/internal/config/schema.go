// Package config handles skills.toml loading, saving, validation, and defaults.
package config

// Manifest is the parsed contents of skills.toml.
type Manifest struct {
	Meta    MetaConfig                `toml:"meta"`
	Sources map[string]SourceConfig   `toml:"sources"`
	Skills  map[string]SkillConfig    `toml:"skills"`
	Targets TargetsConfig             `toml:"targets"`
	Plugin  map[string]PluginOverride `toml:"plugin"`
}

// MetaConfig holds the [meta] block.
type MetaConfig struct {
	Version     int    `toml:"version"`
	Name        string `toml:"name"`        // marketplace name (e.g. "vanducng-skills")
	Description string `toml:"description"` // marketplace top-level description
	OwnerName   string `toml:"owner_name"`  // owner.name in marketplace.json
	OwnerURL    string `toml:"owner_url"`   // owner.url in marketplace.json
	Homepage    string `toml:"homepage"`    // fallback homepage for plugins
}

// SourceConfig holds one [sources.<name>] block.
type SourceConfig struct {
	Type string `toml:"type"` // "git" | "local"
	URL  string `toml:"url"`
	Ref  string `toml:"ref"` // branch/tag/sha; optional
}

// SkillConfig holds one [skills.<name>] block.
type SkillConfig struct {
	Source string `toml:"source"` // source name key; "" if detached
	Path   string `toml:"path"`   // upstream sub-path
	Mode   string `toml:"mode"`   // "tracked" | "pinned" | "detached"
	Pin    string `toml:"pin"`    // git SHA; required if mode==pinned
}

// TargetsConfig holds the [targets] block.
type TargetsConfig struct {
	Claude ClaudeTarget `toml:"claude"`
	Agents AgentsTarget `toml:"agents"`
}

// ClaudeTarget configures Claude Code plugin emission (phase 05).
type ClaudeTarget struct {
	Mode   string             `toml:"mode"`   // "bundle" (default) | "per-skill"
	Bundle ClaudeBundleConfig `toml:"bundle"` // honored when Mode == "bundle"
}

// ClaudeBundleConfig holds marketplace.json fields for the emitted bundle.
// Description is the marketplace plugins[] entry description.
// PluginDescription is the plugin.json top-level description (often differs from Description).
// If PluginDescription is empty, Description is used as fallback.
type ClaudeBundleConfig struct {
	Name              string `toml:"name"`
	Version           string `toml:"version"`
	Description       string `toml:"description"`        // marketplace plugin description
	PluginDescription string `toml:"plugin_description"` // plugin.json description (distinct)
	Source            string `toml:"source"`
	Category          string `toml:"category"`
	Homepage          string `toml:"homepage"`
	License           string `toml:"license"`
	VersionStrategy   string `toml:"version_strategy"` // "manual" | "lock-sha"
}

// AgentsTarget is a placeholder for future agent-specific emission (phase 05).
type AgentsTarget struct{}

// PluginOverride holds [plugin.<name>] overrides applied during emission (phase 05).
type PluginOverride struct {
	Description string `toml:"description"`
	Version     string `toml:"version"` // overrides lock SHA short if set
	Category    string `toml:"category"`
	Homepage    string `toml:"homepage"`
}
