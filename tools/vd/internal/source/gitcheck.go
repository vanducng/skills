package source

import (
	"context"
	"fmt"
	"os/exec"
	"strconv"
	"strings"
)

const minGitMajor = 2
const minGitMinor = 25

// RequireGit checks that git is in PATH and meets the minimum version requirement
// (≥2.25) needed for sparse-checkout support. Returns ErrGitMissing on failure.
func RequireGit(ctx context.Context) error {
	path, err := exec.LookPath("git")
	if err != nil {
		return fmt.Errorf("%w: vd requires git in PATH; install: https://git-scm.com/downloads", ErrGitMissing)
	}

	out, err := exec.CommandContext(ctx, path, "--version").Output()
	if err != nil {
		return fmt.Errorf("%w: git --version failed: %v", ErrGitMissing, err)
	}

	// Output format: "git version 2.39.1" (or "git version 2.39.1.windows.1")
	parts := strings.Fields(strings.TrimSpace(string(out)))
	if len(parts) < 3 {
		return fmt.Errorf("%w: unexpected git --version output: %q", ErrGitMissing, string(out))
	}

	vparts := strings.SplitN(parts[2], ".", 3)
	if len(vparts) < 2 {
		return fmt.Errorf("%w: cannot parse git version %q", ErrGitMissing, parts[2])
	}

	major, err := strconv.Atoi(vparts[0])
	if err != nil {
		return fmt.Errorf("%w: cannot parse git major version %q", ErrGitMissing, vparts[0])
	}
	minor, err := strconv.Atoi(vparts[1])
	if err != nil {
		return fmt.Errorf("%w: cannot parse git minor version %q", ErrGitMissing, vparts[1])
	}

	if major < minGitMajor || (major == minGitMajor && minor < minGitMinor) {
		return fmt.Errorf("%w: git %d.%d+ required for sparse-checkout, found %s",
			ErrGitMissing, minGitMajor, minGitMinor, parts[2])
	}
	return nil
}
