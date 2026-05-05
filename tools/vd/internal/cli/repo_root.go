package cli

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/vanducng/skills/tools/vd/internal/config"
)

// resolveRepoRoot returns the repo root directory.
// If override is non-empty it is validated and returned directly.
// Otherwise delegates to config.FindRepoRoot walking up from CWD.
func resolveRepoRoot(override string) (string, error) {
	if override != "" {
		info, err := os.Stat(override)
		if err != nil {
			return "", fmt.Errorf("--root %q: %w", override, err)
		}
		if !info.IsDir() {
			return "", fmt.Errorf("--root %q is not a directory", override)
		}
		return filepath.Clean(override), nil
	}

	cwd, err := os.Getwd()
	if err != nil {
		return "", fmt.Errorf("cannot determine working directory: %w", err)
	}

	return config.FindRepoRoot(cwd)
}
