package cli

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/vanducng/skills/tools/vd/internal/config"
	vdsync "github.com/vanducng/skills/tools/vd/internal/sync"
)

func TestDoctorReportsDrift(t *testing.T) {
	root := t.TempDir()
	skillsDir := filepath.Join(root, "skills")
	if err := os.MkdirAll(skillsDir, 0o755); err != nil {
		t.Fatal(err)
	}

	// Write a skill directory with known content.
	skillDir := filepath.Join(skillsDir, "myskill")
	if err := os.MkdirAll(skillDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(skillDir, "SKILL.md"), []byte("original"), 0o644); err != nil {
		t.Fatal(err)
	}

	// Compute the real hash so the lock starts clean.
	cleanHash, err := vdsync.TreeHash(skillDir)
	if err != nil {
		t.Fatal(err)
	}

	// Write lock with the clean hash (TreeHash used for dirty detection).
	lock := &config.Lockfile{
		Skills: map[string]config.LockEntry{
			"myskill": {SHA: "abc123", TreeHash: cleanHash, Source: "https://example.com", Path: "skills/myskill"},
		},
	}
	if err := config.SaveLock(filepath.Join(root, "skills.lock"), lock); err != nil {
		t.Fatal(err)
	}

	// Verify doctor reports "none" drift initially.
	out, err := execCmd(t, root, NewRootCmd, "doctor")
	if err != nil {
		t.Fatalf("doctor failed: %v\noutput: %s", err, out)
	}
	if !strings.Contains(out, "none") {
		t.Errorf("expected 'none' drift status, got:\n%s", out)
	}

	// Now introduce drift by modifying the skill file.
	if err := os.WriteFile(filepath.Join(skillDir, "SKILL.md"), []byte("modified"), 0o644); err != nil {
		t.Fatal(err)
	}

	out2, err := execCmd(t, root, NewRootCmd, "doctor")
	if err != nil {
		t.Fatalf("doctor failed after drift: %v\noutput: %s", err, out2)
	}
	if !strings.Contains(out2, "local") {
		t.Errorf("expected 'local' drift status, got:\n%s", out2)
	}
}

func TestDoctorReportsMissing(t *testing.T) {
	root := t.TempDir()
	skillsDir := filepath.Join(root, "skills")
	if err := os.MkdirAll(skillsDir, 0o755); err != nil {
		t.Fatal(err)
	}

	// Lock entry exists but no FS directory.
	lock := &config.Lockfile{
		Skills: map[string]config.LockEntry{
			"gone": {SHA: "abc123", Source: "https://example.com", Path: "skills/gone"},
		},
	}
	if err := config.SaveLock(filepath.Join(root, "skills.lock"), lock); err != nil {
		t.Fatal(err)
	}

	out, err := execCmd(t, root, NewRootCmd, "doctor")
	if err != nil {
		t.Fatalf("doctor failed: %v\noutput: %s", err, out)
	}
	if !strings.Contains(out, "missing") {
		t.Errorf("expected 'missing' in doctor output, got:\n%s", out)
	}
}

func TestDoctorReportsUntracked(t *testing.T) {
	root := t.TempDir()
	skillsDir := filepath.Join(root, "skills")

	// FS dir exists but is NOT in the lock (hand-authored skill).
	handDir := filepath.Join(skillsDir, "handmade")
	if err := os.MkdirAll(handDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(handDir, "SKILL.md"), []byte("hand"), 0o644); err != nil {
		t.Fatal(err)
	}

	// Empty lock.
	lock := &config.Lockfile{Skills: map[string]config.LockEntry{}}
	if err := config.SaveLock(filepath.Join(root, "skills.lock"), lock); err != nil {
		t.Fatal(err)
	}

	out, err := execCmd(t, root, NewRootCmd, "doctor")
	if err != nil {
		t.Fatalf("doctor failed: %v\noutput: %s", err, out)
	}
	if !strings.Contains(out, "untracked") {
		t.Errorf("expected 'untracked' for hand-authored skill, got:\n%s", out)
	}
}
