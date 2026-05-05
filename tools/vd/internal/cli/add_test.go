package cli

import (
	"bytes"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	"github.com/vanducng/skills/tools/vd/internal/config"
	"github.com/vanducng/skills/tools/vd/internal/testutil"
)

func skipIfNoGit(t *testing.T) {
	t.Helper()
	if _, err := exec.LookPath("git"); err != nil {
		t.Skip("git not available")
	}
}

// makeRepoWithSkillsToml creates a temp dir with a .git dir and a minimal
// skills.toml so resolveRepoRoot and config.Load both succeed.
func makeRepoWithSkillsToml(t *testing.T) string {
	t.Helper()
	skipIfNoGit(t)

	dir := t.TempDir()

	// Minimal .git directory so FindRepoRoot stops here.
	if err := os.MkdirAll(filepath.Join(dir, ".git"), 0o755); err != nil {
		t.Fatalf("mkdir .git: %v", err)
	}

	// Write a minimal skills.toml.
	toml := "[meta]\n  version = 1\n"
	if err := os.WriteFile(filepath.Join(dir, "skills.toml"), []byte(toml), 0o644); err != nil {
		t.Fatalf("write skills.toml: %v", err)
	}
	return dir
}

// loadFixtureContents reads a plain-file fixture directory into a content map.
func loadFixtureContents(t *testing.T, fixtureDir string) map[string]string {
	t.Helper()
	contents := map[string]string{}
	err := filepath.WalkDir(fixtureDir, func(path string, d os.DirEntry, err error) error {
		if err != nil || d.IsDir() {
			return err
		}
		rel, _ := filepath.Rel(fixtureDir, path)
		data, readErr := os.ReadFile(path)
		if readErr != nil {
			return readErr
		}
		contents[rel] = string(data)
		return nil
	})
	if err != nil {
		t.Fatalf("walk fixture: %v", err)
	}
	return contents
}

func TestRunAdd_marketplaceFixture(t *testing.T) {
	skipIfNoGit(t)

	repoRoot := makeRepoWithSkillsToml(t)

	// Build a git repo from the marketplace fixture.
	fixtureDir := filepath.Join("..", "..", "testdata", "upstream-marketplace")
	upstreamURL := testutil.MakeGitRepo(t, loadFixtureContents(t, fixtureDir))

	// Override flagRoot so resolveRepoRoot returns our temp dir.
	origRoot := flagRoot
	flagRoot = repoRoot
	defer func() { flagRoot = origRoot }()

	cmd := NewRootCmd()
	var out bytes.Buffer
	cmd.SetOut(&out)

	// Synthesize the argument: use upstream URL directly as a pre-declared source.
	// We pre-register the source in skills.toml to avoid GitHub URL parsing.
	manifest, _ := config.Load(filepath.Join(repoRoot, "skills.toml"))
	manifest.Sources["upstream"] = config.SourceConfig{
		Type: "git",
		URL:  upstreamURL,
		Ref:  "main",
	}
	_ = config.Save(filepath.Join(repoRoot, "skills.toml"), manifest)

	cmd.SetArgs([]string{"--root", repoRoot, "add", "upstream/skills/foo", "--as", "myfoo"})
	if err := cmd.Execute(); err != nil {
		t.Fatalf("vd add: %v", err)
	}

	// Verify skills.toml was mutated.
	updated, err := config.Load(filepath.Join(repoRoot, "skills.toml"))
	if err != nil {
		t.Fatalf("reload skills.toml: %v", err)
	}

	skill, ok := updated.Skills["myfoo"]
	if !ok {
		t.Fatalf("skill 'myfoo' not found in skills.toml; skills = %v", updated.Skills)
	}
	if skill.Source != "upstream" {
		t.Errorf("Source = %q, want %q", skill.Source, "upstream")
	}
	if skill.Path != "skills/foo" {
		t.Errorf("Path = %q, want %q", skill.Path, "skills/foo")
	}
	if skill.Mode != "tracked" {
		t.Errorf("Mode = %q, want %q", skill.Mode, "tracked")
	}

	output := out.String()
	if !strings.Contains(output, "added skill myfoo") {
		t.Errorf("expected 'added skill myfoo' in output, got: %q", output)
	}
}

func TestRunAdd_idempotent(t *testing.T) {
	skipIfNoGit(t)

	repoRoot := makeRepoWithSkillsToml(t)
	fixtureDir := filepath.Join("..", "..", "testdata", "upstream-marketplace")
	upstreamURL := testutil.MakeGitRepo(t, loadFixtureContents(t, fixtureDir))

	manifest, _ := config.Load(filepath.Join(repoRoot, "skills.toml"))
	manifest.Sources["upstream"] = config.SourceConfig{Type: "git", URL: upstreamURL, Ref: "main"}
	_ = config.Save(filepath.Join(repoRoot, "skills.toml"), manifest)

	runCmd := func() string {
		cmd := NewRootCmd()
		var out bytes.Buffer
		cmd.SetOut(&out)
		cmd.SetArgs([]string{"--root", repoRoot, "add", "upstream/skills/foo", "--as", "myfoo"})
		if err := cmd.Execute(); err != nil {
			t.Fatalf("vd add: %v", err)
		}
		return out.String()
	}

	first := runCmd()
	if !strings.Contains(first, "added skill myfoo") {
		t.Errorf("first run: expected 'added skill myfoo', got %q", first)
	}

	second := runCmd()
	if !strings.Contains(second, "already tracked") {
		t.Errorf("second run (idempotent): expected 'already tracked', got %q", second)
	}
}

func TestRunAdd_missingSlash(t *testing.T) {
	cmd := NewRootCmd()
	var errOut bytes.Buffer
	cmd.SetErr(&errOut)
	cmd.SetArgs([]string{"add", "bogus"})
	err := cmd.Execute()
	if err == nil {
		t.Error("expected error for argument without slash, got nil")
	}
}

func TestRunAdd_pinnedMode(t *testing.T) {
	skipIfNoGit(t)

	repoRoot := makeRepoWithSkillsToml(t)
	fixtureDir := filepath.Join("..", "..", "testdata", "upstream-marketplace")
	upstreamURL := testutil.MakeGitRepo(t, loadFixtureContents(t, fixtureDir))

	manifest, _ := config.Load(filepath.Join(repoRoot, "skills.toml"))
	manifest.Sources["upstream"] = config.SourceConfig{Type: "git", URL: upstreamURL, Ref: "main"}
	_ = config.Save(filepath.Join(repoRoot, "skills.toml"), manifest)

	cmd := NewRootCmd()
	cmd.SetArgs([]string{"--root", repoRoot, "add", "upstream/skills/bar", "--as", "mybar", "--mode", "pinned"})
	if err := cmd.Execute(); err != nil {
		t.Fatalf("vd add --mode pinned: %v", err)
	}

	updated, _ := config.Load(filepath.Join(repoRoot, "skills.toml"))
	skill := updated.Skills["mybar"]
	if skill.Mode != "pinned" {
		t.Errorf("Mode = %q, want pinned", skill.Mode)
	}
	if skill.Pin == "" {
		t.Error("Pin SHA should not be empty for pinned mode")
	}
}
