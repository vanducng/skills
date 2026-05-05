package updatecheck

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestResolveCachePath_XDGSet(t *testing.T) {
	tmp := t.TempDir()
	t.Setenv("XDG_CACHE_HOME", tmp)

	got, err := ResolveCachePath()
	if err != nil {
		t.Fatalf("ResolveCachePath: %v", err)
	}
	want := filepath.Join(tmp, "vd", "version-check.json")
	if got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}

func TestResolveCachePath_XDGUnset(t *testing.T) {
	t.Setenv("XDG_CACHE_HOME", "")

	got, err := ResolveCachePath()
	if err != nil {
		t.Fatalf("ResolveCachePath: %v", err)
	}
	if !strings.HasSuffix(got, filepath.Join("vd", "version-check.json")) {
		t.Errorf("path %q does not end with vd/version-check.json", got)
	}
}

func TestWriteCache_AtomicRename(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "nested", "version-check.json")

	r := Result{
		Current:   "1.0.0",
		Latest:    "1.1.0",
		URL:       "https://example.com/r/v1.1.0",
		FetchedAt: time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC),
	}

	if err := WriteCache(path, r); err != nil {
		t.Fatalf("WriteCache: %v", err)
	}

	// Tempfile must be cleaned up post-rename.
	if _, err := os.Stat(path + ".tmp"); !errors.Is(err, os.ErrNotExist) {
		t.Errorf("tmp file leaked, err=%v", err)
	}

	info, err := os.Stat(path)
	if err != nil {
		t.Fatalf("stat cache: %v", err)
	}
	if info.Mode().Perm() != 0o644 {
		t.Errorf("mode = %v, want 0644", info.Mode().Perm())
	}
}

func TestReadCache_MissingFile(t *testing.T) {
	_, err := ReadCache(filepath.Join(t.TempDir(), "absent.json"))
	if !errors.Is(err, os.ErrNotExist) {
		t.Errorf("err = %v, want os.ErrNotExist", err)
	}
}

func TestReadCache_CorruptJSON(t *testing.T) {
	path := filepath.Join(t.TempDir(), "corrupt.json")
	if err := os.WriteFile(path, []byte("{not json"), 0o644); err != nil {
		t.Fatalf("setup: %v", err)
	}
	_, err := ReadCache(path)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if errors.Is(err, os.ErrNotExist) {
		t.Errorf("err should not be ErrNotExist, got %v", err)
	}
}

func TestRoundTrip_WriteThenRead(t *testing.T) {
	path := filepath.Join(t.TempDir(), "rt.json")
	want := Result{
		Current:   "1.0.0",
		Latest:    "1.2.3",
		URL:       "https://example.com/r/v1.2.3",
		FetchedAt: time.Now().UTC().Truncate(time.Second),
	}

	if err := WriteCache(path, want); err != nil {
		t.Fatalf("WriteCache: %v", err)
	}
	got, err := ReadCache(path)
	if err != nil {
		t.Fatalf("ReadCache: %v", err)
	}
	// Compare field-by-field; FetchedAt comparison via Equal because
	// JSON round-trips can drop nanoseconds even after Truncate.
	if got.Current != want.Current || got.Latest != want.Latest || got.URL != want.URL {
		t.Errorf("string fields mismatch: got %+v, want %+v", got, want)
	}
	if !got.FetchedAt.Equal(want.FetchedAt) {
		t.Errorf("FetchedAt = %v, want %v", got.FetchedAt, want.FetchedAt)
	}
}
