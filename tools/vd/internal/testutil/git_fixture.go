// Package testutil provides test helpers for vd tests.
package testutil

import (
	"os"
	"os/exec"
	"path/filepath"
	"testing"
)

// MakeGitRepo creates a temporary git repository populated with the given
// contents map (relative path → file content). It commits everything as the
// initial commit and returns the absolute path to the repo directory, which
// can be used directly as a local git URL (file:///path or just /path).
//
// The repository uses a local git config for user.email/user.name so that
// commits succeed in CI environments without a global git config.
func MakeGitRepo(t *testing.T, contents map[string]string) string {
	t.Helper()

	if _, err := exec.LookPath("git"); err != nil {
		t.Skip("git not available")
	}

	dir := t.TempDir()

	run := func(args ...string) {
		t.Helper()
		cmd := exec.Command("git", args...)
		cmd.Dir = dir
		if out, err := cmd.CombinedOutput(); err != nil {
			t.Fatalf("git %v: %v\n%s", args, err, out)
		}
	}

	run("init", "--initial-branch=main")
	run("config", "user.email", "test@vd.local")
	run("config", "user.name", "vd test")

	for relPath, content := range contents {
		full := filepath.Join(dir, relPath)
		if err := os.MkdirAll(filepath.Dir(full), 0o755); err != nil {
			t.Fatalf("mkdir %s: %v", filepath.Dir(full), err)
		}
		if err := os.WriteFile(full, []byte(content), 0o644); err != nil {
			t.Fatalf("write %s: %v", full, err)
		}
	}

	run("add", ".")
	run("commit", "-m", "init")

	return dir
}
