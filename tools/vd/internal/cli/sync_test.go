package cli

import (
	"bytes"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	"github.com/spf13/cobra"

	"github.com/vanducng/skills/tools/vd/internal/config"
	"github.com/vanducng/skills/tools/vd/internal/testutil"
)

// makeTestRepo creates a temp repo root with skills.toml initialized.
func makeTestRepo(t *testing.T) string {
	t.Helper()
	root := t.TempDir()
	// Initialize manifest and git repo.
	run := func(args ...string) {
		t.Helper()
		cmd := exec.Command("git", args...)
		cmd.Dir = root
		if out, err := cmd.CombinedOutput(); err != nil {
			t.Fatalf("git %v: %v\n%s", args, err, out)
		}
	}
	run("init", "--initial-branch=main")
	run("config", "user.email", "test@vd.local")
	run("config", "user.name", "vd test")

	// Write a minimal skills.toml.
	if err := os.WriteFile(filepath.Join(root, "skills.toml"), []byte("[meta]\nversion = 1\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(root, "skills"), 0o755); err != nil {
		t.Fatal(err)
	}
	return root
}

// execCmd runs a Cobra command with the given args against root, returning stdout+stderr.
// It injects --root so tests never walk up to the real repo root.
func execCmd(t *testing.T, root string, newCmd func() *cobra.Command, args ...string) (string, error) {
	t.Helper()

	cmd := newCmd()
	var buf bytes.Buffer
	cmd.SetOut(&buf)
	cmd.SetErr(&buf)
	// Prepend --root flag so resolveRepoRoot uses the temp dir.
	fullArgs := append([]string{"--root", root}, args...)
	cmd.SetArgs(fullArgs)
	err := cmd.Execute()
	return buf.String(), err
}

func TestSyncIntegration_FullCycle(t *testing.T) {
	if _, err := exec.LookPath("git"); err != nil {
		t.Skip("git not available")
	}

	// Build upstream git repo with a skill at skills/myskill/.
	upstream := testutil.MakeGitRepo(t, map[string]string{
		"skills/myskill/SKILL.md": "# MySkill\nThis is the skill.\n",
		"skills/myskill/tool.sh":  "#!/bin/sh\necho hello\n",
	})

	root := makeTestRepo(t)

	// Populate manifest to reference upstream.
	manifest, err := config.Load(filepath.Join(root, "skills.toml"))
	if err != nil {
		t.Fatal(err)
	}
	manifest.Sources["local"] = config.SourceConfig{
		Type: "git",
		URL:  upstream,
		Ref:  "main",
	}
	manifest.Skills["myskill"] = config.SkillConfig{
		Source: "local",
		Path:   "skills/myskill",
		Mode:   "tracked",
	}
	if err := config.Save(filepath.Join(root, "skills.toml"), manifest); err != nil {
		t.Fatal(err)
	}

	// --- vd sync: first run, should copy files ---
	out, err := execCmd(t, root, NewRootCmd, "sync")
	if err != nil {
		t.Fatalf("first sync failed: %v\noutput: %s", err, out)
	}
	if !strings.Contains(out, "synced") && !strings.Contains(out, "myskill") {
		t.Errorf("expected 'synced myskill' in output, got: %s", out)
	}

	// Verify files landed in skills/myskill/.
	skillDir := filepath.Join(root, "skills", "myskill")
	data, err := os.ReadFile(filepath.Join(skillDir, "SKILL.md"))
	if err != nil {
		t.Fatalf("skills/myskill/SKILL.md not found after sync: %v", err)
	}
	if !strings.Contains(string(data), "MySkill") {
		t.Errorf("unexpected SKILL.md content: %s", data)
	}

	// Verify lock was written.
	lock, err := config.LoadLock(filepath.Join(root, "skills.lock"))
	if err != nil {
		t.Fatal(err)
	}
	if _, ok := lock.Skills["myskill"]; !ok {
		t.Error("myskill not in skills.lock after sync")
	}

	// --- vd sync: second run should be idempotent ---
	out2, err := execCmd(t, root, NewRootCmd, "sync")
	if err != nil {
		t.Fatalf("second sync failed: %v\noutput: %s", err, out2)
	}
	if !strings.Contains(out2, "up to date") && !strings.Contains(out2, "skip") {
		t.Logf("second sync output: %s", out2)
	}

	// --- Modify a file locally → sync should refuse ---
	if err := os.WriteFile(filepath.Join(skillDir, "SKILL.md"), []byte("drift\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	out3, err := execCmd(t, root, NewRootCmd, "sync")
	if err == nil {
		t.Error("expected sync to fail on dirty skill, but it succeeded")
	}
	if !strings.Contains(out3, "REFUSED") && !strings.Contains(out3, "local edits") {
		t.Errorf("expected refuse message, got: %s", out3)
	}

	// --- vd detach → sync should skip ---
	out4, err := execCmd(t, root, NewRootCmd, "detach", "myskill")
	if err != nil {
		t.Fatalf("detach failed: %v\noutput: %s", err, out4)
	}

	out5, err := execCmd(t, root, NewRootCmd, "sync")
	if err != nil {
		t.Fatalf("sync after detach failed: %v\noutput: %s", err, out5)
	}
	// After detach, skill is skipped (detached mode).
	if strings.Contains(out5, "synced") {
		t.Errorf("expected no sync after detach, got: %s", out5)
	}

	// --- vd remove --keep-files → manifest empty, dir still there ---
	out6, err := execCmd(t, root, NewRootCmd, "remove", "--keep-files", "myskill")
	if err != nil {
		t.Fatalf("remove --keep-files failed: %v\noutput: %s", err, out6)
	}

	finalManifest, err := config.Load(filepath.Join(root, "skills.toml"))
	if err != nil {
		t.Fatal(err)
	}
	if _, ok := finalManifest.Skills["myskill"]; ok {
		t.Error("myskill should be gone from manifest after remove")
	}

	// Dir should still exist because we used --keep-files.
	if _, err := os.Stat(skillDir); err != nil {
		t.Errorf("skills/myskill/ should still exist after --keep-files: %v", err)
	}
}

func TestSyncIntegration_ForceOverwritesDirty(t *testing.T) {
	if _, err := exec.LookPath("git"); err != nil {
		t.Skip("git not available")
	}

	upstream := testutil.MakeGitRepo(t, map[string]string{
		"skills/myskill/SKILL.md": "upstream content\n",
	})

	root := makeTestRepo(t)

	manifest, err := config.Load(filepath.Join(root, "skills.toml"))
	if err != nil {
		t.Fatal(err)
	}
	manifest.Sources["local"] = config.SourceConfig{Type: "git", URL: upstream, Ref: "main"}
	manifest.Skills["myskill"] = config.SkillConfig{Source: "local", Path: "skills/myskill", Mode: "tracked"}
	if err := config.Save(filepath.Join(root, "skills.toml"), manifest); err != nil {
		t.Fatal(err)
	}

	// Initial sync.
	if _, err := execCmd(t, root, NewRootCmd, "sync"); err != nil {
		t.Fatalf("initial sync: %v", err)
	}

	// Introduce drift.
	skillDir := filepath.Join(root, "skills", "myskill")
	if err := os.WriteFile(filepath.Join(skillDir, "SKILL.md"), []byte("local change\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	// sync --force should overwrite.
	_, err = execCmd(t, root, NewRootCmd, "sync", "--force")
	if err != nil {
		t.Fatalf("sync --force should succeed on dirty skill, got: %v", err)
	}

	data, _ := os.ReadFile(filepath.Join(skillDir, "SKILL.md"))
	if !strings.Contains(string(data), "upstream content") {
		t.Errorf("expected upstream content after --force, got: %s", data)
	}
}
