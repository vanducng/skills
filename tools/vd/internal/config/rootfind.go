package config

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
)

// FindRepoRoot walks up from start until it finds a directory containing .git/.
// Returns the absolute path of that directory, or an error if none found.
func FindRepoRoot(start string) (string, error) {
	dir, err := filepath.Abs(start)
	if err != nil {
		return "", fmt.Errorf("resolve start path: %w", err)
	}

	for {
		if _, err := os.Stat(filepath.Join(dir, ".git")); err == nil {
			return dir, nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}

	return "", errors.New("no .git found in ancestors; pass --root <path> explicitly")
}
