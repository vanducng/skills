package target

import (
	"fmt"
	"os"
	"path/filepath"
	"testing"

	"github.com/vanducng/skills/tools/vd/internal/config"
)

const snapshotDir = "testdata/bundle-snapshot"

// TestBundleSnapshot is the CRITICAL gate: bundle emitter must produce
// byte-equal output to the live .claude-plugin/{marketplace,plugin}.json files.
func TestBundleSnapshot(t *testing.T) {
	// Load fixture manifest.
	manifestPath := filepath.Join(snapshotDir, "skills.toml")
	manifest, err := config.Load(manifestPath)
	if err != nil {
		t.Fatalf("load fixture manifest: %v", err)
	}

	// Emit into a temp directory (never touch live files in tests).
	tmp := t.TempDir()
	pluginDir := filepath.Join(tmp, ".claude-plugin")
	if err := os.MkdirAll(pluginDir, 0o755); err != nil {
		t.Fatalf("create plugin dir: %v", err)
	}

	// Copy LICENSE into temp root so license detection works.
	licenseData, err := os.ReadFile(filepath.Join(snapshotDir, "LICENSE"))
	if err != nil {
		t.Fatalf("read LICENSE fixture: %v", err)
	}
	if err := os.WriteFile(filepath.Join(tmp, "LICENSE"), licenseData, 0o644); err != nil {
		t.Fatalf("write LICENSE: %v", err)
	}

	ctx := Context{
		Manifest: manifest,
		Lock:     &config.Lockfile{Skills: map[string]config.LockEntry{}},
		RepoRoot: tmp,
	}

	emitter := &bundleEmitter{}
	if err := emitter.emit(ctx); err != nil {
		t.Fatalf("emit: %v", err)
	}

	// Compare marketplace.json.
	assertBytesEqual(t,
		filepath.Join(pluginDir, "marketplace.json"),
		filepath.Join(snapshotDir, "marketplace.json.golden"),
		"marketplace.json",
	)

	// Compare plugin.json.
	assertBytesEqual(t,
		filepath.Join(pluginDir, "plugin.json"),
		filepath.Join(snapshotDir, "plugin.json.golden"),
		"plugin.json",
	)
}

func assertBytesEqual(t *testing.T, gotPath, wantPath, label string) {
	t.Helper()
	got, err := os.ReadFile(gotPath)
	if err != nil {
		t.Fatalf("%s: read got file: %v", label, err)
	}
	want, err := os.ReadFile(wantPath)
	if err != nil {
		t.Fatalf("%s: read want file: %v", label, err)
	}
	if string(got) != string(want) {
		t.Errorf("%s: output does not match golden file\n--- want ---\n%s\n--- got ---\n%s\n--- diff (line-by-line) ---\n%s",
			label, want, got, unifiedDiff(string(want), string(got)))
	}
}

// unifiedDiff produces a simple line-level diff for test output readability.
func unifiedDiff(want, got string) string {
	wantLines := splitLines(want)
	gotLines := splitLines(got)

	max := len(wantLines)
	if len(gotLines) > max {
		max = len(gotLines)
	}

	var out string
	for i := 0; i < max; i++ {
		w := lineAt(wantLines, i)
		g := lineAt(gotLines, i)
		if w == g {
			out += fmt.Sprintf("  %s\n", w)
		} else {
			out += fmt.Sprintf("- %s\n", w)
			out += fmt.Sprintf("+ %s\n", g)
		}
	}
	return out
}

func splitLines(s string) []string {
	var lines []string
	start := 0
	for i := 0; i < len(s); i++ {
		if s[i] == '\n' {
			lines = append(lines, s[start:i])
			start = i + 1
		}
	}
	if start < len(s) {
		lines = append(lines, s[start:])
	}
	return lines
}

func lineAt(lines []string, i int) string {
	if i < len(lines) {
		return lines[i]
	}
	return "<missing>"
}

// TestBundleLicenseDetection verifies SPDX detection from LICENSE file content.
func TestBundleLicenseDetection(t *testing.T) {
	cases := []struct {
		content  string
		fallback string
		want     string
	}{
		{"MIT License\n\nCopyright...", "unknown", "MIT"},
		{"Apache License, Version 2.0", "unknown", "Apache-2.0"},
		{"GNU General Public License\nVersion 3", "unknown", "GPL-3.0"},
		{"BSD 3-Clause License", "unknown", "BSD-3-Clause"},
		{"ISC License", "unknown", "ISC"},
		{"Mozilla Public License 2.0", "unknown", "MPL-2.0"},
		{"", "MIT", "MIT"},                    // empty file → fallback
		{"Custom license blah", "MIT", "MIT"}, // unrecognized → fallback
	}

	for _, tc := range cases {
		t.Run(tc.want+"_"+tc.fallback, func(t *testing.T) {
			tmp := t.TempDir()
			if tc.content != "" {
				if err := os.WriteFile(filepath.Join(tmp, "LICENSE"), []byte(tc.content), 0o644); err != nil {
					t.Fatal(err)
				}
			}
			got := DetectLicense(tmp, tc.fallback)
			if got != tc.want {
				t.Errorf("DetectLicense: got %q want %q (content: %q)", got, tc.want, tc.content)
			}
		})
	}
}

// TestBundleOverridePrecedence verifies that [plugin.<name>] overrides take
// priority over bundle defaults.
func TestBundleOverridePrecedence(t *testing.T) {
	tmp := t.TempDir()
	if err := os.MkdirAll(filepath.Join(tmp, ".claude-plugin"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(tmp, "LICENSE"), []byte("MIT License"), 0o644); err != nil {
		t.Fatal(err)
	}

	manifest := &config.Manifest{
		Meta: config.MetaConfig{
			Name:        "test-marketplace",
			Description: "Test marketplace",
			OwnerName:   "testuser",
			OwnerURL:    "https://github.com/testuser",
		},
		Targets: config.TargetsConfig{
			Claude: config.ClaudeTarget{
				Mode: "bundle",
				Bundle: config.ClaudeBundleConfig{
					Name:        "vd",
					Version:     "1.0.0",
					Description: "Original description",
					Source:      "./",
					Category:    "utilities",
					Homepage:    "https://github.com/testuser/skills",
					License:     "MIT",
				},
			},
		},
		Plugin: map[string]config.PluginOverride{
			"vd": {
				Description: "Overridden description",
				Version:     "2.0.0",
				Category:    "dev-tools",
			},
		},
	}

	ctx := Context{
		Manifest: manifest,
		Lock:     &config.Lockfile{Skills: map[string]config.LockEntry{}},
		RepoRoot: tmp,
	}

	if err := (&bundleEmitter{}).emit(ctx); err != nil {
		t.Fatalf("emit: %v", err)
	}

	data, err := os.ReadFile(filepath.Join(tmp, ".claude-plugin", "marketplace.json"))
	if err != nil {
		t.Fatal(err)
	}
	content := string(data)

	if !contains(content, `"Overridden description"`) {
		t.Error("expected overridden description in marketplace.json")
	}
	if !contains(content, `"2.0.0"`) {
		t.Error("expected overridden version in marketplace.json")
	}
	if !contains(content, `"dev-tools"`) {
		t.Error("expected overridden category in marketplace.json")
	}
}

func contains(s, sub string) bool {
	return len(s) >= len(sub) && (s == sub || len(s) > 0 && containsStr(s, sub))
}

func containsStr(s, sub string) bool {
	for i := 0; i <= len(s)-len(sub); i++ {
		if s[i:i+len(sub)] == sub {
			return true
		}
	}
	return false
}
