package sync

import (
	"os"
	"path/filepath"
	"testing"
)

func TestTreeHash_EmptyDir(t *testing.T) {
	dir := t.TempDir()
	h, err := TreeHash(dir)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	// Empty input → SHA-256 of "" is deterministic.
	if h == "" {
		t.Fatal("expected non-empty hash for empty dir")
	}
}

func TestTreeHash_SingleFile(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "SKILL.md"), []byte("hello"), 0o644); err != nil {
		t.Fatal(err)
	}

	h1, err := TreeHash(dir)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Same content → same hash (determinism).
	h2, err := TreeHash(dir)
	if err != nil {
		t.Fatalf("unexpected error on second call: %v", err)
	}
	if h1 != h2 {
		t.Errorf("non-deterministic: %s != %s", h1, h2)
	}

	// Different content → different hash.
	if err := os.WriteFile(filepath.Join(dir, "SKILL.md"), []byte("world"), 0o644); err != nil {
		t.Fatal(err)
	}
	h3, err := TreeHash(dir)
	if err != nil {
		t.Fatal(err)
	}
	if h3 == h1 {
		t.Error("different content produced same hash")
	}
}

func TestTreeHash_ExecBitChangesHash(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "run.sh")
	if err := os.WriteFile(path, []byte("#!/bin/sh"), 0o644); err != nil {
		t.Fatal(err)
	}

	hNoExec, err := TreeHash(dir)
	if err != nil {
		t.Fatal(err)
	}

	if err := os.Chmod(path, 0o755); err != nil {
		t.Fatal(err)
	}

	hExec, err := TreeHash(dir)
	if err != nil {
		t.Fatal(err)
	}

	if hNoExec == hExec {
		t.Error("exec bit change should produce different hash")
	}
}

func TestTreeHash_IgnoredFiles(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "SKILL.md"), []byte("content"), 0o644); err != nil {
		t.Fatal(err)
	}

	hBefore, err := TreeHash(dir)
	if err != nil {
		t.Fatal(err)
	}

	// Writing an ignored file must not change the hash.
	if err := os.WriteFile(filepath.Join(dir, ".DS_Store"), []byte("mac junk"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "Thumbs.db"), []byte("win junk"), 0o644); err != nil {
		t.Fatal(err)
	}

	hAfter, err := TreeHash(dir)
	if err != nil {
		t.Fatal(err)
	}

	if hBefore != hAfter {
		t.Errorf("ignored files changed hash: before=%s after=%s", hBefore, hAfter)
	}
}

func TestTreeHash_NestedFiles(t *testing.T) {
	dir := t.TempDir()
	subdir := filepath.Join(dir, "assets", "fonts")
	if err := os.MkdirAll(subdir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(subdir, "mono.ttf"), []byte("font"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "SKILL.md"), []byte("top"), 0o644); err != nil {
		t.Fatal(err)
	}

	h1, err := TreeHash(dir)
	if err != nil {
		t.Fatal(err)
	}

	// Verify determinism on a second call.
	h2, err := TreeHash(dir)
	if err != nil {
		t.Fatal(err)
	}

	if h1 != h2 {
		t.Errorf("non-deterministic across nested calls: %s != %s", h1, h2)
	}
}

func TestTreeHash_GitDirIgnored(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "README.md"), []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}

	hBefore, err := TreeHash(dir)
	if err != nil {
		t.Fatal(err)
	}

	// Simulate a .git dir with files — must be skipped.
	gitDir := filepath.Join(dir, ".git")
	if err := os.MkdirAll(gitDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(gitDir, "HEAD"), []byte("ref: refs/heads/main"), 0o644); err != nil {
		t.Fatal(err)
	}

	hAfter, err := TreeHash(dir)
	if err != nil {
		t.Fatal(err)
	}

	if hBefore != hAfter {
		t.Errorf(".git dir changed hash: before=%s after=%s", hBefore, hAfter)
	}
}
