package config

import (
	"encoding/json"
	"os"
	"path/filepath"
)

// hardcoded fallbacks when marketplace.json is absent or lacks the vd plugin entry.
const (
	defaultBundleName            = "vd"
	defaultBundleVersion         = "0.5.1"
	defaultBundleSource          = "./"
	defaultBundleCategory        = "utilities"
	defaultBundleLicense         = "MIT"
	defaultBundleVersionStrategy = "manual"
	defaultClaudeMode            = "bundle"
)

// marketplaceTopLevel mirrors the top-level shape of .claude-plugin/marketplace.json.
type marketplaceTopLevel struct {
	Name        string              `json:"name"`
	Description string              `json:"description"`
	Owner       marketplaceOwner    `json:"owner"`
	Plugins     []marketplacePlugin `json:"plugins"`
}

type marketplaceOwner struct {
	Name string `json:"name"`
	URL  string `json:"url"`
}

type marketplacePlugin struct {
	Name        string `json:"name"`
	Description string `json:"description"`
	Version     string `json:"version"`
	Source      string `json:"source"`
	Category    string `json:"category"`
	Homepage    string `json:"homepage"`
}

// pluginDoc mirrors .claude-plugin/plugin.json.
type pluginDoc struct {
	Name        string `json:"name"`
	Description string `json:"description"`
}

// ApplyDefaults seeds [meta] and [targets.claude.bundle] defaults in m.
// marketplaceJSONPath and pluginJSONPath point to .claude-plugin/{marketplace,plugin}.json.
// When both files exist their values are used so 'vd build' re-emits byte-equal output.
// Falls back to hard-coded defaults when files are absent or unparseable.
func ApplyDefaults(m *Manifest, marketplaceJSONPath string) {
	pluginJSONPath := ""
	if marketplaceJSONPath != "" {
		pluginJSONPath = filepath.Join(filepath.Dir(marketplaceJSONPath), "plugin.json")
	}
	applyDefaultsFull(m, marketplaceJSONPath, pluginJSONPath)
}

// ApplyDefaultsFull accepts explicit paths to both JSON files. Used in tests.
func ApplyDefaultsFull(m *Manifest, marketplacePath, pluginPath string) {
	applyDefaultsFull(m, marketplacePath, pluginPath)
}

func applyDefaultsFull(m *Manifest, marketplacePath, pluginPath string) {
	if m.Targets.Claude.Mode == "" {
		m.Targets.Claude.Mode = defaultClaudeMode
	}

	top := readMarketplaceTop(marketplacePath)
	plugin := findPlugin(top.Plugins, "vd")
	pdoc := readPluginDoc(pluginPath)

	// Seed [meta] from top-level marketplace fields.
	if m.Meta.Name == "" {
		m.Meta.Name = top.Name
	}
	if m.Meta.Description == "" {
		m.Meta.Description = top.Description
	}
	if m.Meta.OwnerName == "" {
		m.Meta.OwnerName = top.Owner.Name
	}
	if m.Meta.OwnerURL == "" {
		m.Meta.OwnerURL = top.Owner.URL
	}

	b := &m.Targets.Claude.Bundle
	if b.Name == "" {
		b.Name = stringOr(plugin.Name, defaultBundleName)
	}
	if b.Version == "" {
		b.Version = stringOr(plugin.Version, defaultBundleVersion)
	}
	if b.Description == "" {
		b.Description = plugin.Description // marketplace plugin description
	}
	if b.PluginDescription == "" {
		b.PluginDescription = pdoc.Description // plugin.json description
	}
	if b.Source == "" {
		b.Source = stringOr(plugin.Source, defaultBundleSource)
	}
	if b.Category == "" {
		b.Category = stringOr(plugin.Category, defaultBundleCategory)
	}
	if b.Homepage == "" {
		b.Homepage = plugin.Homepage
		if b.Homepage == "" {
			b.Homepage = m.Meta.OwnerURL
		}
	}
	if m.Meta.Homepage == "" {
		m.Meta.Homepage = b.Homepage
	}
	if b.License == "" {
		b.License = defaultBundleLicense
	}
	if b.VersionStrategy == "" {
		b.VersionStrategy = defaultBundleVersionStrategy
	}
}

func readMarketplaceTop(path string) marketplaceTopLevel {
	if path == "" {
		return marketplaceTopLevel{}
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return marketplaceTopLevel{}
	}
	var doc marketplaceTopLevel
	if err := json.Unmarshal(data, &doc); err != nil {
		return marketplaceTopLevel{}
	}
	return doc
}

func findPlugin(plugins []marketplacePlugin, name string) marketplacePlugin {
	for _, p := range plugins {
		if p.Name == name {
			return p
		}
	}
	return marketplacePlugin{}
}

func readPluginDoc(path string) pluginDoc {
	if path == "" {
		return pluginDoc{}
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return pluginDoc{}
	}
	var doc pluginDoc
	if err := json.Unmarshal(data, &doc); err != nil {
		return pluginDoc{}
	}
	return doc
}

func stringOr(s, fallback string) string {
	if s != "" {
		return s
	}
	return fallback
}
