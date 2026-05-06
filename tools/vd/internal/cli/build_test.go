package cli

import (
	"os"
	"os/exec"
	"path/filepath"
	"testing"

	"github.com/spf13/cobra"
)

// setupE2ERepo creates a minimal git repo with one skill and a skills.toml.
func setupE2ERepo(t *testing.T) string {
	t.Helper()
	tmp := t.TempDir()

	// Init git repo with local user config so commits work in CI without global git config.
	if out, err := exec.Command("git", "-C", tmp, "init").CombinedOutput(); err != nil {
		t.Fatalf("git init: %v\n%s", err, out)
	}
	if out, err := exec.Command("git", "-C", tmp, "config", "user.email", "test@vd.local").CombinedOutput(); err != nil {
		t.Fatalf("git config user.email: %v\n%s", err, out)
	}
	if out, err := exec.Command("git", "-C", tmp, "config", "user.name", "vd test").CombinedOutput(); err != nil {
		t.Fatalf("git config user.name: %v\n%s", err, out)
	}
	if out, err := exec.Command("git", "-C", tmp, "commit", "--allow-empty", "-m", "init").CombinedOutput(); err != nil {
		t.Fatalf("git commit: %v\n%s", err, out)
	}

	// Write a minimal skills.toml with required meta fields.
	toml := `[meta]
version = 1
name = "test-skills"
description = "Test marketplace"
owner_name = "tester"
owner_url = "https://example.com"
homepage = "https://example.com"

[targets.claude]
mode = "bundle"

[targets.claude.bundle]
name = "test-bundle"
version = "1.0.0"
description = "A test bundle"
plugin_description = "A test bundle plugin"
source = "./"
category = "utilities"
homepage = "https://example.com"
license = "MIT"
version_strategy = "manual"
`
	if err := os.WriteFile(filepath.Join(tmp, "skills.toml"), []byte(toml), 0o644); err != nil {
		t.Fatal(err)
	}

	// Write a LICENSE file.
	if err := os.WriteFile(filepath.Join(tmp, "LICENSE"), []byte("MIT License\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	// Create one skill.
	skillDir := filepath.Join(tmp, "skills", "foo")
	if err := os.MkdirAll(skillDir, 0o755); err != nil {
		t.Fatal(err)
	}
	skillMD := "---\nname: foo\ndescription: A foo skill\n---\n# Foo\n"
	if err := os.WriteFile(filepath.Join(skillDir, "SKILL.md"), []byte(skillMD), 0o644); err != nil {
		t.Fatal(err)
	}

	return tmp
}

func TestBuildCmd_WritesOutputFiles(t *testing.T) {
	root := setupE2ERepo(t)

	cmd := &cobra.Command{}
	if err := runBuild(cmd, root, nil); err != nil {
		t.Fatalf("runBuild: %v", err)
	}

	// marketplace.json must exist.
	mpPath := filepath.Join(root, ".claude-plugin", "marketplace.json")
	if _, err := os.Stat(mpPath); err != nil {
		t.Errorf("marketplace.json missing: %v", err)
	}

	// plugin.json must exist (bundle mode).
	pjPath := filepath.Join(root, ".claude-plugin", "plugin.json")
	if _, err := os.Stat(pjPath); err != nil {
		t.Errorf("plugin.json missing: %v", err)
	}

	// .agents/skills/foo symlink must exist.
	agentFoo := filepath.Join(root, ".agents", "skills", "foo")
	if _, err := os.Lstat(agentFoo); err != nil {
		t.Errorf(".agents/skills/foo missing: %v", err)
	}
}

func TestBuildCmd_ExplicitTarget(t *testing.T) {
	root := setupE2ERepo(t)

	cmd := &cobra.Command{}
	// Build only claude — agents must not be created.
	if err := runBuild(cmd, root, []string{"claude"}); err != nil {
		t.Fatalf("runBuild claude: %v", err)
	}

	if _, err := os.Stat(filepath.Join(root, ".claude-plugin", "marketplace.json")); err != nil {
		t.Error("marketplace.json missing after claude-only build")
	}
	if _, err := os.Lstat(filepath.Join(root, ".agents", "skills", "foo")); !os.IsNotExist(err) {
		t.Error(".agents/skills/foo should not exist after claude-only build")
	}
}

func TestBuildCmd_Idempotent(t *testing.T) {
	root := setupE2ERepo(t)
	cmd := &cobra.Command{}

	for i := 0; i < 2; i++ {
		if err := runBuild(cmd, root, nil); err != nil {
			t.Fatalf("runBuild run %d: %v", i+1, err)
		}
	}

	// Both output files must still be present.
	for _, name := range []string{".claude-plugin/marketplace.json", ".claude-plugin/plugin.json"} {
		if _, err := os.Stat(filepath.Join(root, name)); err != nil {
			t.Errorf("%s missing after idempotent run: %v", name, err)
		}
	}
}
