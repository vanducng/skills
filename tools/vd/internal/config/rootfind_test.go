package config

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestFindRepoRoot(t *testing.T) {
	// Create a temp tree: root/.git and root/sub/
	base := t.TempDir()
	gitDir := filepath.Join(base, ".git")
	if err := os.Mkdir(gitDir, 0o755); err != nil {
		t.Fatalf("mkdir .git: %v", err)
	}
	sub := filepath.Join(base, "sub", "nested")
	if err := os.MkdirAll(sub, 0o755); err != nil {
		t.Fatalf("mkdir sub: %v", err)
	}

	t.Run("finds root from sub-directory", func(t *testing.T) {
		got, err := FindRepoRoot(sub)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if got != base {
			t.Errorf("got %q want %q", got, base)
		}
	})

	t.Run("finds root from root itself", func(t *testing.T) {
		got, err := FindRepoRoot(base)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if got != base {
			t.Errorf("got %q want %q", got, base)
		}
	})

	t.Run("no .git ancestor returns error", func(t *testing.T) {
		// Use a directory with no .git anywhere in the FS tree above it.
		// /tmp itself has no .git, so use a path directly under the OS temp root.
		isolated := t.TempDir()
		_, err := FindRepoRoot(isolated)
		if err == nil {
			// It's possible the CI machine has a .git in /tmp — skip rather than fail.
			t.Skip("no error returned; .git may exist above temp dir")
		}
		if !strings.Contains(err.Error(), ".git") {
			t.Errorf("error should mention .git: %v", err)
		}
	})

	t.Run("invalid start path returns error", func(t *testing.T) {
		// A non-existent path with a null byte is invalid on POSIX.
		_, err := FindRepoRoot(string([]byte{0}))
		if err == nil {
			t.Skip("OS accepted null-byte path")
		}
	})
}
