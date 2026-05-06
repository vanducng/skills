package target

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"

	"github.com/vanducng/skills/tools/vd/internal/config"
)

func makeTestSkillDir(t *testing.T, root, name string) {
	t.Helper()
	d := filepath.Join(root, "skills", name)
	if err := os.MkdirAll(d, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(d, "SKILL.md"), []byte("---\nname: "+name+"\n---\n"), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestAgentsEmitter_CreatesSymlinks(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("symlink test skipped on Windows")
	}

	tmp := t.TempDir()
	makeTestSkillDir(t, tmp, "alpha")
	makeTestSkillDir(t, tmp, "beta")
	makeTestSkillDir(t, tmp, "gamma")

	ctx := Context{
		Manifest: &config.Manifest{},
		Lock:     &config.Lockfile{Skills: map[string]config.LockEntry{}},
		RepoRoot: tmp,
	}

	if err := (&agentsEmitter{}).Emit(ctx); err != nil {
		t.Fatalf("emit: %v", err)
	}

	agentsDir := filepath.Join(tmp, ".agents", "skills")
	for _, name := range []string{"alpha", "beta", "gamma"} {
		linkPath := filepath.Join(agentsDir, name)
		target, err := os.Readlink(linkPath)
		if err != nil {
			t.Errorf("%s: expected symlink, got error: %v", name, err)
			continue
		}
		// Should be a relative symlink pointing to ../../skills/<name>.
		wantTarget := filepath.Join("..", "..", "skills", name)
		if target != wantTarget {
			t.Errorf("%s: symlink target = %q, want %q", name, target, wantTarget)
		}
	}
}

func TestAgentsEmitter_RemovesStaleEntries(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("symlink test skipped on Windows")
	}

	tmp := t.TempDir()
	makeTestSkillDir(t, tmp, "keep")

	// Pre-create a stale .agents/skills/stale entry (a dir, not a skill).
	agentsDir := filepath.Join(tmp, ".agents", "skills")
	if err := os.MkdirAll(filepath.Join(agentsDir, "stale"), 0o755); err != nil {
		t.Fatal(err)
	}

	ctx := Context{
		Manifest: &config.Manifest{},
		Lock:     &config.Lockfile{Skills: map[string]config.LockEntry{}},
		RepoRoot: tmp,
	}

	if err := (&agentsEmitter{}).Emit(ctx); err != nil {
		t.Fatalf("emit: %v", err)
	}

	// "stale" should be gone.
	if _, err := os.Lstat(filepath.Join(agentsDir, "stale")); !os.IsNotExist(err) {
		t.Error("stale entry should have been removed")
	}

	// "keep" symlink should exist.
	if _, err := os.Lstat(filepath.Join(agentsDir, "keep")); err != nil {
		t.Errorf("keep symlink missing: %v", err)
	}
}

func TestAgentsEmitter_Idempotent(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("symlink test skipped on Windows")
	}

	tmp := t.TempDir()
	makeTestSkillDir(t, tmp, "foo")
	makeTestSkillDir(t, tmp, "bar")

	ctx := Context{
		Manifest: &config.Manifest{},
		Lock:     &config.Lockfile{Skills: map[string]config.LockEntry{}},
		RepoRoot: tmp,
	}

	e := &agentsEmitter{}
	// Run twice — must not error on second run.
	for i := 0; i < 2; i++ {
		if err := e.Emit(ctx); err != nil {
			t.Fatalf("emit run %d: %v", i+1, err)
		}
	}

	// Verify symlinks are still correct after second run.
	agentsDir := filepath.Join(tmp, ".agents", "skills")
	for _, name := range []string{"foo", "bar"} {
		target, err := os.Readlink(filepath.Join(agentsDir, name))
		if err != nil {
			t.Errorf("%s: readlink: %v", name, err)
		}
		want := filepath.Join("..", "..", "skills", name)
		if target != want {
			t.Errorf("%s: target = %q, want %q", name, target, want)
		}
	}
}

func TestAgentsEmitter_NoSkillsDir(t *testing.T) {
	tmp := t.TempDir()
	// No skills/ directory at all — should succeed silently.
	ctx := Context{
		Manifest: &config.Manifest{},
		Lock:     &config.Lockfile{Skills: map[string]config.LockEntry{}},
		RepoRoot: tmp,
	}
	if err := (&agentsEmitter{}).Emit(ctx); err != nil {
		t.Errorf("expected no error with missing skills dir, got: %v", err)
	}
}
