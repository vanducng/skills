package source

import (
	"context"
	"errors"
	"fmt"
	"os/exec"
	"testing"
)

func TestRequireGit_available(t *testing.T) {
	if _, err := exec.LookPath("git"); err != nil {
		t.Skip("git not available")
	}
	ctx := context.Background()
	if err := RequireGit(ctx); err != nil {
		t.Errorf("RequireGit with git in PATH: unexpected error: %v", err)
	}
}

func TestErrGitMissing_sentinel(t *testing.T) {
	// Verify the sentinel wraps correctly with %w for errors.Is consumers.
	wrapped := fmt.Errorf("context: %w", ErrGitMissing)
	if !errors.Is(wrapped, ErrGitMissing) {
		t.Error("errors.Is should unwrap to ErrGitMissing")
	}
}
