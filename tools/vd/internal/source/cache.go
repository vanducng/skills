package source

import (
	"fmt"
	"os"
	"path/filepath"
	"time"
)

// DefaultTTL is the maximum age of a cache entry before it is considered stale.
const DefaultTTL = 24 * time.Hour

// CacheRoot returns the absolute path to the vd cache directory for the given repo root.
func CacheRoot(repoRoot string) string {
	return filepath.Join(repoRoot, ".vd-cache")
}

// Stale reports whether the directory at dir was last modified more than ttl ago.
// Returns true if the directory does not exist or cannot be stat'd.
func Stale(dir string, ttl time.Duration) bool {
	info, err := os.Stat(dir)
	if err != nil {
		return true
	}
	return time.Since(info.ModTime()) > ttl
}

// Clean removes the entire .vd-cache directory under repoRoot.
// Returns nil if the directory does not exist.
func Clean(repoRoot string) error {
	dir := CacheRoot(repoRoot)
	if err := os.RemoveAll(dir); err != nil {
		return fmt.Errorf("remove cache %s: %w", dir, err)
	}
	return nil
}
