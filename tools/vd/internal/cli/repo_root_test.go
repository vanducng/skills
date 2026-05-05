package cli

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// makeTempRepoDir creates a temp dir with a .git/ marker so FindRepoRoot
// would stop there. Returns the absolute path of the temp dir.
func makeTempRepoDir(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	if err := os.MkdirAll(filepath.Join(dir, ".git"), 0o755); err != nil {
		t.Fatalf("mkdir .git: %v", err)
	}
	return dir
}

func TestResolveRepoRoot_FlagWinsOverEnv(t *testing.T) {
	flagDir := makeTempRepoDir(t)
	envDir := makeTempRepoDir(t)
	t.Setenv(rootEnvVar, envDir)

	got, err := resolveRepoRoot(flagDir)
	if err != nil {
		t.Fatalf("resolveRepoRoot: %v", err)
	}
	if got != filepath.Clean(flagDir) {
		t.Errorf("got %q, want %q (flag should win over env)", got, flagDir)
	}
}

func TestResolveRepoRoot_EnvUsedWhenFlagEmpty(t *testing.T) {
	envDir := makeTempRepoDir(t)
	t.Setenv(rootEnvVar, envDir)

	got, err := resolveRepoRoot("")
	if err != nil {
		t.Fatalf("resolveRepoRoot: %v", err)
	}
	if got != filepath.Clean(envDir) {
		t.Errorf("got %q, want %q", got, envDir)
	}
}

func TestResolveRepoRoot_EnvMissingDirErrors(t *testing.T) {
	t.Setenv(rootEnvVar, "/definitely/does/not/exist/vd-test")

	_, err := resolveRepoRoot("")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !strings.Contains(err.Error(), rootEnvVar) {
		t.Errorf("error %q should mention %s", err.Error(), rootEnvVar)
	}
}

func TestResolveRepoRoot_EnvFileNotDirErrors(t *testing.T) {
	tmp := t.TempDir()
	filePath := filepath.Join(tmp, "not-a-dir")
	if err := os.WriteFile(filePath, []byte("x"), 0o644); err != nil {
		t.Fatalf("write file: %v", err)
	}
	t.Setenv(rootEnvVar, filePath)

	_, err := resolveRepoRoot("")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !strings.Contains(err.Error(), "not a directory") {
		t.Errorf("error %q should mention 'not a directory'", err.Error())
	}
	if !strings.Contains(err.Error(), rootEnvVar) {
		t.Errorf("error %q should mention %s", err.Error(), rootEnvVar)
	}
}

func TestResolveRepoRoot_FallsThroughToFindRepoRoot(t *testing.T) {
	// Clear env explicitly so the user's shell setting can't leak in.
	t.Setenv(rootEnvVar, "")

	repo := makeTempRepoDir(t)

	// Move CWD into a subdir of the temp repo and let FindRepoRoot walk up.
	sub := filepath.Join(repo, "nested")
	if err := os.MkdirAll(sub, 0o755); err != nil {
		t.Fatalf("mkdir nested: %v", err)
	}
	origCwd, err := os.Getwd()
	if err != nil {
		t.Fatalf("getwd: %v", err)
	}
	t.Cleanup(func() { _ = os.Chdir(origCwd) })
	if err := os.Chdir(sub); err != nil {
		t.Fatalf("chdir: %v", err)
	}

	got, err := resolveRepoRoot("")
	if err != nil {
		t.Fatalf("resolveRepoRoot: %v", err)
	}

	// On macOS, t.TempDir() returns paths under /var/folders that resolve
	// through /private; FindRepoRoot returns the resolved form. Compare via
	// EvalSymlinks for stability.
	wantResolved, _ := filepath.EvalSymlinks(repo)
	gotResolved, _ := filepath.EvalSymlinks(got)
	if gotResolved != wantResolved {
		t.Errorf("got %q (resolved %q), want %q (resolved %q)", got, gotResolved, repo, wantResolved)
	}
}

func TestResolveRepoRoot_FlagInvalidErrors(t *testing.T) {
	_, err := resolveRepoRoot("/definitely/does/not/exist/vd-test")
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !strings.Contains(err.Error(), "--root") {
		t.Errorf("error %q should mention --root", err.Error())
	}
}
