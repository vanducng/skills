package source

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestCacheRoot(t *testing.T) {
	got := CacheRoot("/some/repo")
	want := "/some/repo/.vd-cache"
	if got != want {
		t.Errorf("CacheRoot = %q, want %q", got, want)
	}
}

func TestStale_missingDir(t *testing.T) {
	if !Stale("/nonexistent/path/xyz", time.Hour) {
		t.Error("Stale should return true for a nonexistent directory")
	}
}

func TestStale_freshDir(t *testing.T) {
	dir := t.TempDir()
	// A freshly created dir should not be stale with a 1-hour TTL.
	if Stale(dir, time.Hour) {
		t.Error("Stale should return false for a freshly created directory")
	}
}

func TestStale_oldDir(t *testing.T) {
	dir := t.TempDir()
	// Back-date the mtime by 48 hours.
	past := time.Now().Add(-48 * time.Hour)
	if err := os.Chtimes(dir, past, past); err != nil {
		t.Fatalf("chtimes: %v", err)
	}
	if !Stale(dir, time.Hour) {
		t.Error("Stale should return true for a directory older than TTL")
	}
}

func TestClean_removesCache(t *testing.T) {
	repoRoot := t.TempDir()
	cacheDir := filepath.Join(repoRoot, ".vd-cache")
	if err := os.MkdirAll(filepath.Join(cacheDir, "sub"), 0o755); err != nil {
		t.Fatalf("mkdir: %v", err)
	}

	if err := Clean(repoRoot); err != nil {
		t.Fatalf("Clean: %v", err)
	}

	if _, err := os.Stat(cacheDir); !os.IsNotExist(err) {
		t.Error("cache dir should be removed after Clean")
	}
}

func TestClean_noopWhenMissing(t *testing.T) {
	repoRoot := t.TempDir()
	// No .vd-cache exists — should not error.
	if err := Clean(repoRoot); err != nil {
		t.Fatalf("Clean on empty repo: %v", err)
	}
}
