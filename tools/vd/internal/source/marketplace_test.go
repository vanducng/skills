package source

import (
	"os"
	"path/filepath"
	"testing"
)

func TestParseMarketplace_validFixture(t *testing.T) {
	// Point at the checked-in testdata fixture (plain files, no .git).
	fixtureDir := filepath.Join("..", "..", "testdata", "upstream-marketplace")

	cat, err := parseMarketplace(fixtureDir)
	if err != nil {
		t.Fatalf("parseMarketplace: %v", err)
	}

	if len(cat.Skills) != 2 {
		t.Fatalf("expected 2 entries, got %d", len(cat.Skills))
	}

	names := map[string]bool{}
	for _, e := range cat.Skills {
		names[e.Name] = true
		if e.Source != "marketplace" {
			t.Errorf("entry %q: Source = %q, want %q", e.Name, e.Source, "marketplace")
		}
		if e.Path == "" {
			t.Errorf("entry %q: Path is empty", e.Name)
		}
	}

	for _, want := range []string{"foo", "bar"} {
		if !names[want] {
			t.Errorf("expected entry %q not found", want)
		}
	}
}

func TestParseMarketplace_missing(t *testing.T) {
	_, err := parseMarketplace(t.TempDir())
	if !os.IsNotExist(err) {
		t.Errorf("expected os.ErrNotExist, got %v", err)
	}
}

func TestParseMarketplace_invalid(t *testing.T) {
	dir := t.TempDir()
	pluginDir := filepath.Join(dir, ".claude-plugin")
	if err := os.MkdirAll(pluginDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(pluginDir, "marketplace.json"), []byte("not json"), 0o644); err != nil {
		t.Fatal(err)
	}

	_, err := parseMarketplace(dir)
	if err == nil {
		t.Error("expected error parsing invalid JSON, got nil")
	}
}
