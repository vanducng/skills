package target

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/vanducng/skills/tools/vd/internal/config"
)

// marketplaceDoc is the top-level structure of .claude-plugin/marketplace.json.
// Field order matches the live file exactly (Go encodes struct fields in declaration order).
type marketplaceDoc struct {
	Schema      string              `json:"$schema"`
	Name        string              `json:"name"`
	Description string              `json:"description"`
	Owner       ownerInfo           `json:"owner"`
	Plugins     []marketplacePlugin `json:"plugins"`
}

type ownerInfo struct {
	Name string `json:"name"`
	URL  string `json:"url"`
}

// marketplacePlugin is one entry in the plugins array.
// Field order must match live marketplace.json exactly.
type marketplacePlugin struct {
	Name        string    `json:"name"`
	Description string    `json:"description"`
	Version     string    `json:"version"`
	Author      ownerInfo `json:"author"`
	Source      string    `json:"source"`
	Category    string    `json:"category"`
	Homepage    string    `json:"homepage"`
}

// pluginDoc is the structure of .claude-plugin/plugin.json.
// Field order matches the live file exactly.
type pluginDoc struct {
	Name        string    `json:"name"`
	Version     string    `json:"version"`
	Description string    `json:"description"`
	Author      ownerInfo `json:"author"`
	Homepage    string    `json:"homepage"`
	License     string    `json:"license"`
}

type bundleEmitter struct{}

func (e *bundleEmitter) emit(ctx Context) error {
	b := ctx.Manifest.Targets.Claude.Bundle
	meta := ctx.Manifest.Meta

	author := ownerInfo{
		Name: meta.OwnerName,
		URL:  meta.OwnerURL,
	}
	if author.Name == "" {
		author.Name = b.Name
	}

	// Resolve per-field with [plugin.<bundle-name>] override having highest priority.
	ov := pluginOverride(ctx.Manifest, b.Name)

	pluginDesc := b.Description
	if ov.Description != "" {
		pluginDesc = ov.Description
	}

	version := b.Version
	if ov.Version != "" {
		version = ov.Version
	}

	category := b.Category
	if ov.Category != "" {
		category = ov.Category
	}

	homepage := b.Homepage
	if ov.Homepage != "" {
		homepage = ov.Homepage
	}
	if homepage == "" {
		homepage = meta.Homepage
	}

	plugin := marketplacePlugin{
		Name:        b.Name,
		Description: pluginDesc,
		Version:     version,
		Author:      author,
		Source:      b.Source,
		Category:    category,
		Homepage:    homepage,
	}

	doc := marketplaceDoc{
		Schema:      "https://anthropic.com/claude-code/marketplace.schema.json",
		Name:        meta.Name,
		Description: meta.Description,
		Owner:       author,
		Plugins:     []marketplacePlugin{plugin},
	}

	outDir := filepath.Join(ctx.RepoRoot, ".claude-plugin")
	if err := os.MkdirAll(outDir, 0o755); err != nil {
		return fmt.Errorf("bundle emitter: ensure .claude-plugin dir: %w", err)
	}

	if err := writeJSON(filepath.Join(outDir, "marketplace.json"), doc); err != nil {
		return fmt.Errorf("bundle emitter: write marketplace.json: %w", err)
	}

	// plugin.json uses PluginDescription (separate from the marketplace plugin description).
	// Falls back to the marketplace description when PluginDescription is unset.
	pluginJSONDesc := b.PluginDescription
	if pluginJSONDesc == "" {
		pluginJSONDesc = pluginDesc
	}

	license := DetectLicense(ctx.RepoRoot, b.License)
	if license == "" {
		license = "MIT"
	}

	pdoc := pluginDoc{
		Name:        b.Name,
		Version:     version,
		Description: pluginJSONDesc,
		Author:      author,
		Homepage:    homepage,
		License:     license,
	}

	if err := writeJSON(filepath.Join(outDir, "plugin.json"), pdoc); err != nil {
		return fmt.Errorf("bundle emitter: write plugin.json: %w", err)
	}

	return nil
}

// pluginOverride extracts [plugin.<name>] fields from the manifest as a value type.
func pluginOverride(m *config.Manifest, name string) config.PluginOverride {
	if m.Plugin == nil {
		return config.PluginOverride{}
	}
	return m.Plugin[name]
}

// writeJSON marshals v with 2-space indent and a trailing newline, then atomically
// writes it to path.
func writeJSON(path string, v interface{}) error {
	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal JSON: %w", err)
	}
	data = append(data, '\n')
	return atomicWriteFile(path, data)
}

// atomicWriteFile writes data to path via temp file + rename.
func atomicWriteFile(path string, data []byte) error {
	dir := filepath.Dir(path)
	tmp, err := os.CreateTemp(dir, ".vd-tmp-*")
	if err != nil {
		return fmt.Errorf("create temp file: %w", err)
	}
	tmpPath := tmp.Name()

	ok := false
	defer func() {
		if !ok {
			_ = os.Remove(tmpPath)
		}
	}()

	if _, err := tmp.Write(data); err != nil {
		_ = tmp.Close()
		return fmt.Errorf("write temp: %w", err)
	}
	if err := tmp.Close(); err != nil {
		return fmt.Errorf("close temp: %w", err)
	}
	if err := os.Rename(tmpPath, path); err != nil {
		return fmt.Errorf("rename to %s: %w", path, err)
	}
	ok = true
	return nil
}
