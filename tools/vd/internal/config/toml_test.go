package config

import (
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

func TestRoundTrip(t *testing.T) {
	cases := []struct {
		name    string
		fixture string
	}{
		{"empty manifest", "empty.toml"},
		{"single tracked skill", "single-tracked.toml"},
		{"single pinned skill", "single-pinned.toml"},
		{"single detached skill", "single-detached.toml"},
		{"mixed manifest", "mixed.toml"},
	}

	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			fixturePath := filepath.Join("testdata", tc.fixture)

			// Load from fixture.
			m1, err := Load(fixturePath)
			if err != nil {
				t.Fatalf("Load(%q): %v", fixturePath, err)
			}

			// Save to temp file.
			tmp, err := os.CreateTemp(t.TempDir(), "round-trip-*.toml")
			if err != nil {
				t.Fatalf("create temp: %v", err)
			}
			tmpPath := tmp.Name()
			tmp.Close()

			if err := Save(tmpPath, m1); err != nil {
				t.Fatalf("Save: %v", err)
			}

			// Reload from temp file.
			m2, err := Load(tmpPath)
			if err != nil {
				t.Fatalf("Load(saved): %v", err)
			}

			// Structs must be DeepEqual after the round-trip.
			if !reflect.DeepEqual(m1, m2) {
				t.Errorf("round-trip mismatch:\n  original: %+v\n  reloaded: %+v", m1, m2)
			}
		})
	}
}

func TestLoadMissingFile(t *testing.T) {
	m, err := Load(filepath.Join(t.TempDir(), "does-not-exist.toml"))
	if err != nil {
		t.Fatalf("expected nil error for missing file, got: %v", err)
	}
	if m == nil {
		t.Fatal("expected non-nil manifest")
	}
	if len(m.Skills) != 0 {
		t.Errorf("expected empty skills map, got %d entries", len(m.Skills))
	}
}

func TestLoadInvalidTOML(t *testing.T) {
	dir := t.TempDir()
	bad := filepath.Join(dir, "bad.toml")
	if err := os.WriteFile(bad, []byte("[[[[invalid"), 0o644); err != nil {
		t.Fatal(err)
	}
	_, err := Load(bad)
	if err == nil {
		t.Fatal("expected error for invalid TOML, got nil")
	}
}

func TestSaveAtomicWrite(t *testing.T) {
	// Verify that saving to a read-only directory fails gracefully (not a panic).
	dir := t.TempDir()
	// Make dir read-only.
	if err := os.Chmod(dir, 0o555); err != nil {
		t.Skip("cannot chmod temp dir:", err)
	}
	t.Cleanup(func() { _ = os.Chmod(dir, 0o755) })

	dest := filepath.Join(dir, "skills.toml")
	m := &Manifest{Meta: MetaConfig{Version: 1}}
	err := Save(dest, m)
	if err == nil {
		t.Error("expected error saving to read-only dir, got nil")
	}
}

func TestLoadPermissionDenied(t *testing.T) {
	// Trigger the non-ErrNotExist read error branch in Load.
	dir := t.TempDir()
	f := filepath.Join(dir, "unreadable.toml")
	if err := os.WriteFile(f, []byte("[meta]\nversion = 1\n"), 0o000); err != nil {
		t.Fatal(err)
	}
	if os.Getuid() == 0 {
		t.Skip("root bypasses file permissions")
	}
	_, err := Load(f)
	if err == nil {
		t.Error("expected error for unreadable file, got nil")
	}
}

func TestAtomicWriteCreateTempError(t *testing.T) {
	// CreateTemp fails when the directory portion of path is read-only.
	readonly := t.TempDir()
	if err := os.Chmod(readonly, 0o555); err != nil {
		t.Skip("cannot chmod:", err)
	}
	t.Cleanup(func() { _ = os.Chmod(readonly, 0o755) })
	if os.Getuid() == 0 {
		t.Skip("root bypasses permissions")
	}

	err := atomicWrite(filepath.Join(readonly, "out.toml"), []byte("hello"))
	if err == nil {
		t.Error("expected create-temp error, got nil")
	}
}

func TestLoadNilMapsAfterUnmarshal(t *testing.T) {
	// A TOML with no sources/skills/plugin sections should still return non-nil maps.
	dir := t.TempDir()
	f := filepath.Join(dir, "bare.toml")
	if err := os.WriteFile(f, []byte("[meta]\nversion = 1\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	m, err := Load(f)
	if err != nil {
		t.Fatalf("Load: %v", err)
	}
	if m.Sources == nil {
		t.Error("Sources map should not be nil")
	}
	if m.Skills == nil {
		t.Error("Skills map should not be nil")
	}
	if m.Plugin == nil {
		t.Error("Plugin map should not be nil")
	}
}
