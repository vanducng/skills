package updatecheck

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

// cacheFile is the per-user filename used inside the resolved cache dir.
const cacheFile = "version-check.json"

// ResolveCachePath returns the absolute path of the version-check cache
// file. Honors XDG_CACHE_HOME first, then falls back to os.UserCacheDir.
// The directory is NOT created here — WriteCache MkdirAll's on demand.
func ResolveCachePath() (string, error) {
	if xdg := os.Getenv("XDG_CACHE_HOME"); xdg != "" {
		return filepath.Join(xdg, "vd", cacheFile), nil
	}
	dir, err := os.UserCacheDir()
	if err != nil {
		return "", fmt.Errorf("resolve user cache dir: %w", err)
	}
	return filepath.Join(dir, "vd", cacheFile), nil
}

// ReadCache loads a Result from disk. A missing file returns os.ErrNotExist
// (callers treat that as a normal cache-miss, not an error).
func ReadCache(path string) (Result, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return Result{}, err
	}
	var r Result
	if err := json.Unmarshal(data, &r); err != nil {
		return Result{}, fmt.Errorf("parse cache %s: %w", path, err)
	}
	return r, nil
}

// WriteCache persists r atomically: marshal → write tempfile → rename.
// Concurrent writes never observe a half-written file.
func WriteCache(path string, r Result) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return fmt.Errorf("mkdir cache: %w", err)
	}

	data, err := json.MarshalIndent(r, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal cache: %w", err)
	}

	tmp := path + ".tmp"
	if err := os.WriteFile(tmp, data, 0o644); err != nil {
		return fmt.Errorf("write cache tmp: %w", err)
	}
	if err := os.Rename(tmp, path); err != nil {
		_ = os.Remove(tmp)
		return fmt.Errorf("rename cache: %w", err)
	}
	return nil
}
