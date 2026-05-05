package source

import (
	"path/filepath"
	"testing"
)

func TestDetectCatalog_marketplace(t *testing.T) {
	fixtureDir := filepath.Join("..", "..", "testdata", "upstream-marketplace")

	cat, err := DetectCatalog(fixtureDir)
	if err != nil {
		t.Fatalf("DetectCatalog (marketplace): %v", err)
	}
	if len(cat.Skills) == 0 {
		t.Error("expected at least one skill entry from marketplace fixture")
	}
	for _, e := range cat.Skills {
		if e.Source != "marketplace" {
			t.Errorf("entry %q: Source = %q, want marketplace", e.Name, e.Source)
		}
	}
}

func TestDetectCatalog_raw(t *testing.T) {
	fixtureDir := filepath.Join("..", "..", "testdata", "upstream-raw")

	cat, err := DetectCatalog(fixtureDir)
	if err != nil {
		t.Fatalf("DetectCatalog (raw): %v", err)
	}
	if len(cat.Skills) == 0 {
		t.Error("expected at least one skill entry from raw fixture")
	}
	for _, e := range cat.Skills {
		if e.Source != "raw" {
			t.Errorf("entry %q: Source = %q, want raw", e.Name, e.Source)
		}
	}
}

func TestDetectCatalog_empty(t *testing.T) {
	_, err := DetectCatalog(t.TempDir())
	if err == nil {
		t.Error("expected error for directory with no catalog, got nil")
	}
}
