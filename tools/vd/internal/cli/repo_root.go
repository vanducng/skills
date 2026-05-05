package cli

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/vanducng/skills/tools/vd/internal/config"
)

// rootEnvVar is the environment variable name consulted by resolveRepoRoot
// when --root is not set.
const rootEnvVar = "VD_ROOT"

// resolveRepoRoot returns the repo root directory.
// Precedence (high → low): --root flag, VD_ROOT env var, .git walk-up from CWD.
// Both flag and env value are validated (must exist, must be a directory);
// invalid values error out rather than silently falling through.
func resolveRepoRoot(override string) (string, error) {
	if override != "" {
		return validateRootDir(override, "--root")
	}

	if env := os.Getenv(rootEnvVar); env != "" {
		return validateRootDir(env, rootEnvVar)
	}

	cwd, err := os.Getwd()
	if err != nil {
		return "", fmt.Errorf("cannot determine working directory: %w", err)
	}

	return config.FindRepoRoot(cwd)
}

// validateRootDir asserts that path exists and is a directory, returning a
// cleaned absolute-relative path. source is used in error messages so the
// caller can tell whether --root or VD_ROOT was bad.
func validateRootDir(path, source string) (string, error) {
	info, err := os.Stat(path)
	if err != nil {
		return "", fmt.Errorf("%s %q: %w", source, path, err)
	}
	if !info.IsDir() {
		return "", fmt.Errorf("%s %q is not a directory", source, path)
	}
	return filepath.Clean(path), nil
}
