package target

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/vanducng/skills/tools/vd/internal/config"
)

func makeFixtureSkill(t *testing.T, dir, name, description string) {
	t.Helper()
	skillDir := filepath.Join(dir, name)
	if err := os.MkdirAll(skillDir, 0o755); err != nil {
		t.Fatal(err)
	}
	frontmatter := "---\nname: " + name + "\ndescription: " + description + "\n---\n"
	if err := os.WriteFile(filepath.Join(skillDir, "SKILL.md"), []byte(frontmatter), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestPerSkillEmitter_Sorted(t *testing.T) {
	tmp := t.TempDir()
	skillsDir := filepath.Join(tmp, "skills")

	// Create skills in non-alphabetical order to test sort.
	makeFixtureSkill(t, skillsDir, "zebra", "Zebra skill")
	makeFixtureSkill(t, skillsDir, "alpha", "Alpha skill")
	makeFixtureSkill(t, skillsDir, "middle", "Middle skill")

	manifest := &config.Manifest{
		Meta: config.MetaConfig{
			Name:        "test-market",
			Description: "Test",
			OwnerName:   "tester",
			OwnerURL:    "https://example.com",
		},
		Targets: config.TargetsConfig{
			Claude: config.ClaudeTarget{Mode: "per-skill"},
		},
		Plugin: map[string]config.PluginOverride{},
	}

	ctx := Context{
		Manifest: manifest,
		Lock:     &config.Lockfile{Skills: map[string]config.LockEntry{}},
		RepoRoot: tmp,
	}

	if err := (&perSkillEmitter{}).emit(ctx); err != nil {
		t.Fatalf("emit: %v", err)
	}

	outPath := filepath.Join(tmp, ".claude-plugin", "marketplace.json")
	data, err := os.ReadFile(outPath)
	if err != nil {
		t.Fatalf("read output: %v", err)
	}

	var doc struct {
		Plugins []struct {
			Name string `json:"name"`
		} `json:"plugins"`
	}
	if err := json.Unmarshal(data, &doc); err != nil {
		t.Fatalf("parse output: %v", err)
	}

	if len(doc.Plugins) != 3 {
		t.Fatalf("expected 3 plugins, got %d", len(doc.Plugins))
	}

	// Verify alphabetical order.
	order := []string{"alpha", "middle", "zebra"}
	for i, want := range order {
		if doc.Plugins[i].Name != want {
			t.Errorf("plugins[%d]: got %q want %q", i, doc.Plugins[i].Name, want)
		}
	}

	// plugin.json must NOT be written in per-skill mode.
	if _, err := os.Stat(filepath.Join(tmp, ".claude-plugin", "plugin.json")); !os.IsNotExist(err) {
		t.Error("plugin.json must not be written in per-skill mode")
	}
}

func TestPerSkillEmitter_OverridePrecedence(t *testing.T) {
	tmp := t.TempDir()
	skillsDir := filepath.Join(tmp, "skills")
	makeFixtureSkill(t, skillsDir, "myskill", "Frontmatter description")

	manifest := &config.Manifest{
		Meta: config.MetaConfig{
			OwnerName: "tester",
			OwnerURL:  "https://example.com",
		},
		Targets: config.TargetsConfig{
			Claude: config.ClaudeTarget{Mode: "per-skill"},
		},
		Plugin: map[string]config.PluginOverride{
			"myskill": {
				Description: "Override description",
				Version:     "9.9.9",
				Category:    "custom",
			},
		},
	}

	ctx := Context{
		Manifest: manifest,
		Lock:     &config.Lockfile{Skills: map[string]config.LockEntry{}},
		RepoRoot: tmp,
	}

	if err := (&perSkillEmitter{}).emit(ctx); err != nil {
		t.Fatalf("emit: %v", err)
	}

	data, err := os.ReadFile(filepath.Join(tmp, ".claude-plugin", "marketplace.json"))
	if err != nil {
		t.Fatal(err)
	}

	var doc struct {
		Plugins []struct {
			Name        string `json:"name"`
			Description string `json:"description"`
			Version     string `json:"version"`
			Category    string `json:"category"`
		} `json:"plugins"`
	}
	if err := json.Unmarshal(data, &doc); err != nil {
		t.Fatalf("parse: %v", err)
	}
	if len(doc.Plugins) != 1 {
		t.Fatalf("expected 1 plugin, got %d", len(doc.Plugins))
	}
	p := doc.Plugins[0]
	if p.Description != "Override description" {
		t.Errorf("description: got %q want override", p.Description)
	}
	if p.Version != "9.9.9" {
		t.Errorf("version: got %q want 9.9.9", p.Version)
	}
	if p.Category != "custom" {
		t.Errorf("category: got %q want custom", p.Category)
	}
}

func TestPerSkillEmitter_FrontmatterFallback(t *testing.T) {
	tmp := t.TempDir()
	skillsDir := filepath.Join(tmp, "skills")
	makeFixtureSkill(t, skillsDir, "fmskill", "From frontmatter")

	manifest := &config.Manifest{
		Meta:    config.MetaConfig{OwnerName: "tester"},
		Targets: config.TargetsConfig{Claude: config.ClaudeTarget{Mode: "per-skill"}},
		Plugin:  map[string]config.PluginOverride{},
	}

	ctx := Context{
		Manifest: manifest,
		Lock:     &config.Lockfile{Skills: map[string]config.LockEntry{}},
		RepoRoot: tmp,
	}

	if err := (&perSkillEmitter{}).emit(ctx); err != nil {
		t.Fatalf("emit: %v", err)
	}

	data, err := os.ReadFile(filepath.Join(tmp, ".claude-plugin", "marketplace.json"))
	if err != nil {
		t.Fatal(err)
	}

	if !containsStr(string(data), "From frontmatter") {
		t.Error("expected frontmatter description in output")
	}
}
