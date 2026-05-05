package source

import (
	"path/filepath"
	"testing"
)

func TestWalkRaw_validFixture(t *testing.T) {
	fixtureDir := filepath.Join("..", "..", "testdata", "upstream-raw")

	cat, err := walkRaw(fixtureDir)
	if err != nil {
		t.Fatalf("walkRaw: %v", err)
	}

	if len(cat.Skills) != 1 {
		t.Fatalf("expected 1 entry, got %d", len(cat.Skills))
	}

	e := cat.Skills[0]
	if e.Name != "baz" {
		t.Errorf("Name = %q, want %q", e.Name, "baz")
	}
	if e.Path != "skills/baz" {
		t.Errorf("Path = %q, want %q", e.Path, "skills/baz")
	}
	if e.Source != "raw" {
		t.Errorf("Source = %q, want %q", e.Source, "raw")
	}
}

func TestWalkRaw_noSkillsDir(t *testing.T) {
	_, err := walkRaw(t.TempDir())
	if err == nil {
		t.Error("expected error when skills/ is absent, got nil")
	}
}

func TestParseFrontmatter_valid(t *testing.T) {
	fixtureFile := filepath.Join("..", "..", "testdata", "upstream-raw", "skills", "baz", "SKILL.md")

	fm, err := parseFrontmatter(fixtureFile)
	if err != nil {
		t.Fatalf("parseFrontmatter: %v", err)
	}
	if fm.Name != "baz" {
		t.Errorf("Name = %q, want %q", fm.Name, "baz")
	}
	if fm.Description == "" {
		t.Error("Description should not be empty")
	}
}
