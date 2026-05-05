package config

import (
	"os"
	"path/filepath"
	"testing"
)

func TestApplyDefaultsFromMarketplace(t *testing.T) {
	m := &Manifest{}
	ApplyDefaults(m, filepath.Join("testdata", "marketplace.json"))

	b := m.Targets.Claude.Bundle
	if b.Name != "vd" {
		t.Errorf("Name: got %q want %q", b.Name, "vd")
	}
	if b.Version != "1.2.3" {
		t.Errorf("Version: got %q want %q", b.Version, "1.2.3")
	}
	if b.Description != "Test plugin description" {
		t.Errorf("Description: got %q want %q", b.Description, "Test plugin description")
	}
	if b.Source != "./" {
		t.Errorf("Source: got %q want %q", b.Source, "./")
	}
	if b.Category != "utilities" {
		t.Errorf("Category: got %q want %q", b.Category, "utilities")
	}
	if b.Homepage != "https://github.com/test/skills" {
		t.Errorf("Homepage: got %q want %q", b.Homepage, "https://github.com/test/skills")
	}
	if b.License != defaultBundleLicense {
		t.Errorf("License: got %q want %q", b.License, defaultBundleLicense)
	}
	if b.VersionStrategy != defaultBundleVersionStrategy {
		t.Errorf("VersionStrategy: got %q want %q", b.VersionStrategy, defaultBundleVersionStrategy)
	}
	if m.Targets.Claude.Mode != defaultClaudeMode {
		t.Errorf("Claude.Mode: got %q want %q", m.Targets.Claude.Mode, defaultClaudeMode)
	}
}

func TestApplyDefaultsFallback(t *testing.T) {
	// No marketplace.json — should use hard-coded fallbacks.
	m := &Manifest{}
	ApplyDefaults(m, "")

	b := m.Targets.Claude.Bundle
	if b.Name != defaultBundleName {
		t.Errorf("Name fallback: got %q want %q", b.Name, defaultBundleName)
	}
	if b.Version != defaultBundleVersion {
		t.Errorf("Version fallback: got %q want %q", b.Version, defaultBundleVersion)
	}
	if b.Source != defaultBundleSource {
		t.Errorf("Source fallback: got %q want %q", b.Source, defaultBundleSource)
	}
	if b.Category != defaultBundleCategory {
		t.Errorf("Category fallback: got %q want %q", b.Category, defaultBundleCategory)
	}
	if b.License != defaultBundleLicense {
		t.Errorf("License fallback: got %q want %q", b.License, defaultBundleLicense)
	}
	if b.VersionStrategy != defaultBundleVersionStrategy {
		t.Errorf("VersionStrategy fallback: got %q want %q", b.VersionStrategy, defaultBundleVersionStrategy)
	}
}

func TestApplyDefaultsNoOverrideExisting(t *testing.T) {
	// Pre-set fields must not be overwritten.
	m := &Manifest{}
	m.Targets.Claude.Mode = "per-skill"
	m.Targets.Claude.Bundle.Name = "my-bundle"
	m.Targets.Claude.Bundle.Version = "9.9.9"

	ApplyDefaults(m, filepath.Join("testdata", "marketplace.json"))

	if m.Targets.Claude.Mode != "per-skill" {
		t.Errorf("Mode should not be overwritten: got %q", m.Targets.Claude.Mode)
	}
	if m.Targets.Claude.Bundle.Name != "my-bundle" {
		t.Errorf("Name should not be overwritten: got %q", m.Targets.Claude.Bundle.Name)
	}
	if m.Targets.Claude.Bundle.Version != "9.9.9" {
		t.Errorf("Version should not be overwritten: got %q", m.Targets.Claude.Bundle.Version)
	}
}

func TestApplyDefaultsMissingMarketplaceFile(t *testing.T) {
	// Non-existent path → fall back to hard-coded defaults, no error.
	m := &Manifest{}
	ApplyDefaults(m, "/no/such/marketplace.json")

	if m.Targets.Claude.Bundle.Name != defaultBundleName {
		t.Errorf("Name: got %q want %q", m.Targets.Claude.Bundle.Name, defaultBundleName)
	}
}

func TestApplyDefaultsBadJSON(t *testing.T) {
	// Malformed JSON → silent fallback to hard-coded defaults.
	bad := filepath.Join(t.TempDir(), "bad.json")
	if err := os.WriteFile(bad, []byte("{{{bad json"), 0o644); err != nil {
		t.Fatal(err)
	}
	m := &Manifest{}
	ApplyDefaults(m, bad)
	if m.Targets.Claude.Bundle.Name != defaultBundleName {
		t.Errorf("Name fallback on bad JSON: got %q want %q", m.Targets.Claude.Bundle.Name, defaultBundleName)
	}
}

func TestApplyDefaultsNoVdPlugin(t *testing.T) {
	// Valid JSON but no "vd" plugin entry → falls back to hard-coded defaults.
	noVd := filepath.Join(t.TempDir(), "no-vd.json")
	content := `{"plugins": [{"name": "other", "version": "1.0"}]}`
	if err := os.WriteFile(noVd, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
	m := &Manifest{}
	ApplyDefaults(m, noVd)
	if m.Targets.Claude.Bundle.Name != defaultBundleName {
		t.Errorf("Name fallback when no vd entry: got %q want %q", m.Targets.Claude.Bundle.Name, defaultBundleName)
	}
}
