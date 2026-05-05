package sync

import (
	"os"
	"path/filepath"
	"testing"
)

func TestAtomicCopyDir_HappyPath(t *testing.T) {
	src := t.TempDir()
	if err := os.WriteFile(filepath.Join(src, "SKILL.md"), []byte("hello"), 0o644); err != nil {
		t.Fatal(err)
	}
	subDir := filepath.Join(src, "assets")
	if err := os.MkdirAll(subDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(subDir, "icon.png"), []byte("png"), 0o644); err != nil {
		t.Fatal(err)
	}

	parent := t.TempDir()
	dst := filepath.Join(parent, "myskill")

	if err := atomicCopyDir(src, dst, parent); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Verify files are present.
	data, err := os.ReadFile(filepath.Join(dst, "SKILL.md"))
	if err != nil || string(data) != "hello" {
		t.Errorf("SKILL.md: got %q err %v", data, err)
	}
	data2, err := os.ReadFile(filepath.Join(dst, "assets", "icon.png"))
	if err != nil || string(data2) != "png" {
		t.Errorf("assets/icon.png: got %q err %v", data2, err)
	}

	// Staging dir must not exist after success.
	stagingDir := filepath.Join(parent, "myskill.tmp")
	if _, err := os.Stat(stagingDir); !os.IsNotExist(err) {
		t.Errorf("staging dir %s should be gone after successful rename", stagingDir)
	}
}

func TestAtomicCopyDir_ExecBitPreserved(t *testing.T) {
	src := t.TempDir()
	script := filepath.Join(src, "run.sh")
	if err := os.WriteFile(script, []byte("#!/bin/sh"), 0o755); err != nil {
		t.Fatal(err)
	}

	parent := t.TempDir()
	dst := filepath.Join(parent, "myskill")

	if err := atomicCopyDir(src, dst, parent); err != nil {
		t.Fatal(err)
	}

	info, err := os.Stat(filepath.Join(dst, "run.sh"))
	if err != nil {
		t.Fatal(err)
	}
	if info.Mode()&0o111 == 0 {
		t.Error("exec bit not preserved on copied file")
	}
}

func TestAtomicCopyDir_SymlinkRejected(t *testing.T) {
	src := t.TempDir()
	target := filepath.Join(src, "real.txt")
	if err := os.WriteFile(target, []byte("real"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(target, filepath.Join(src, "link.txt")); err != nil {
		t.Skip("cannot create symlink:", err)
	}

	parent := t.TempDir()
	dst := filepath.Join(parent, "myskill")

	err := atomicCopyDir(src, dst, parent)
	if err == nil {
		t.Fatal("expected error for symlink, got nil")
	}

	// Staging dir must be cleaned up on error.
	stagingDir := filepath.Join(parent, "myskill.tmp")
	if _, statErr := os.Stat(stagingDir); !os.IsNotExist(statErr) {
		t.Errorf("staging dir %s should be cleaned up after error", stagingDir)
	}
}

func TestAtomicCopyDir_ReplacesExistingDst(t *testing.T) {
	src := t.TempDir()
	if err := os.WriteFile(filepath.Join(src, "SKILL.md"), []byte("new"), 0o644); err != nil {
		t.Fatal(err)
	}

	parent := t.TempDir()
	dst := filepath.Join(parent, "myskill")

	// Pre-create destination with old content.
	if err := os.MkdirAll(dst, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dst, "OLD.md"), []byte("old"), 0o644); err != nil {
		t.Fatal(err)
	}

	if err := atomicCopyDir(src, dst, parent); err != nil {
		t.Fatalf("unexpected error replacing existing dst: %v", err)
	}

	// Old file must be gone.
	if _, err := os.Stat(filepath.Join(dst, "OLD.md")); !os.IsNotExist(err) {
		t.Error("OLD.md should be gone after replace")
	}

	// New file must be present.
	data, err := os.ReadFile(filepath.Join(dst, "SKILL.md"))
	if err != nil || string(data) != "new" {
		t.Errorf("SKILL.md: got %q err %v", data, err)
	}
}
