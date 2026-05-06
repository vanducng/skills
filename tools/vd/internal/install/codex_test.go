package install

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

func writeSkill(t *testing.T, root, name string) {
	t.Helper()
	dir := filepath.Join(root, "skills", name)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	content := "---\nname: " + name + "\ndescription: test skill\n---\n"
	if err := os.WriteFile(filepath.Join(dir, "SKILL.md"), []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestCodex_InstallsRequestedSkillToDest(t *testing.T) {
	repo := t.TempDir()
	dest := filepath.Join(t.TempDir(), "skills")
	writeSkill(t, repo, "foo")
	writeSkill(t, repo, "bar")

	results, err := Codex(repo, CodexOptions{
		Dest:   dest,
		Skills: []string{"foo"},
	})
	if err != nil {
		t.Fatalf("Codex: %v", err)
	}
	if len(results) != 1 || results[0].Name != "foo" {
		t.Fatalf("results = %#v, want only foo", results)
	}

	installed := filepath.Join(dest, "foo", "SKILL.md")
	if _, err := os.Stat(installed); err != nil {
		t.Fatalf("installed SKILL.md missing: %v", err)
	}

	if runtime.GOOS != "windows" {
		if _, err := os.Readlink(filepath.Join(dest, "foo")); err != nil {
			t.Fatalf("expected symlink install: %v", err)
		}
	}
	if _, err := os.Stat(filepath.Join(dest, "bar")); !os.IsNotExist(err) {
		t.Fatalf("bar should not be installed, stat err = %v", err)
	}
}

func TestCodex_ForceReplacesExistingDestination(t *testing.T) {
	repo := t.TempDir()
	dest := filepath.Join(t.TempDir(), "skills")
	writeSkill(t, repo, "foo")

	existing := filepath.Join(dest, "foo")
	if err := os.MkdirAll(existing, 0o755); err != nil {
		t.Fatal(err)
	}
	if _, err := Codex(repo, CodexOptions{Dest: dest, Skills: []string{"foo"}}); err == nil {
		t.Fatal("expected existing destination error")
	}

	if _, err := Codex(repo, CodexOptions{Dest: dest, Skills: []string{"foo"}, Force: true}); err != nil {
		t.Fatalf("Codex force: %v", err)
	}
	if _, err := os.Stat(filepath.Join(existing, "SKILL.md")); err != nil {
		t.Fatalf("force install missing SKILL.md: %v", err)
	}
}

func TestCodex_RepoScopeUsesAgentsSkills(t *testing.T) {
	repo := t.TempDir()
	writeSkill(t, repo, "foo")

	results, err := Codex(repo, CodexOptions{Scope: "repo", DryRun: true})
	if err != nil {
		t.Fatalf("Codex dry-run: %v", err)
	}
	want := filepath.Join(repo, ".agents", "skills", "foo")
	if len(results) != 1 || results[0].Dest != want || results[0].Action != "would symlink" {
		t.Fatalf("results = %#v, want dry-run dest %s", results, want)
	}
}

func TestCodex_RejectsInvalidScopeWithDestOverride(t *testing.T) {
	repo := t.TempDir()
	writeSkill(t, repo, "foo")

	_, err := Codex(repo, CodexOptions{
		Scope:  "project",
		Dest:   filepath.Join(t.TempDir(), "skills"),
		DryRun: true,
	})
	if err == nil {
		t.Fatal("expected invalid scope error")
	}
}
