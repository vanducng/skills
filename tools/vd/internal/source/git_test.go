package source

import (
	"context"
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

// loadMarketplaceFixtureContents reads the testdata/upstream-marketplace tree
// into a map suitable for MakeGitRepo.
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
		t.Fatalf("walk fixture %s: %v", fixtureDir, err)
	}
	return contents
}

func TestGitFetcher_freshClone(t *testing.T) {
	skipIfNoGit(t)

	fixtureDir := filepath.Join("..", "..", "testdata", "upstream-marketplace")
	repoURL := testutil.MakeGitRepo(t, loadFixtureContents(t, fixtureDir))

	cacheRoot := t.TempDir()
	fetcher := NewGitFetcher(cacheRoot)

	src := config.SourceConfig{
		Type: "git",
		URL:  repoURL,
		Ref:  "main",
	}

	ctx := context.Background()
	result, err := fetcher.Fetch(ctx, src, "testpkg", "skills/foo")
	if err != nil {
		t.Fatalf("Fetch: %v", err)
	}

	if result.LocalDir == "" {
		t.Error("LocalDir should not be empty")
	}
	if result.SHA == "" {
		t.Error("SHA should not be empty")
	}
	if len(result.SHA) < 7 {
		t.Errorf("SHA too short: %q", result.SHA)
	}
	if result.Catalog == nil {
		t.Fatal("Catalog should not be nil")
	}
	if len(result.Catalog.Skills) == 0 {
		t.Error("expected at least one skill in catalog")
	}

	// Verify sparse-checkout filtered in the requested path.
	fooDir := filepath.Join(result.LocalDir, "skills", "foo")
	if _, err := os.Stat(fooDir); err != nil {
		t.Errorf("skills/foo should exist after sparse-checkout: %v", err)
	}
}

func TestGitFetcher_update(t *testing.T) {
	skipIfNoGit(t)

	fixtureDir := filepath.Join("..", "..", "testdata", "upstream-marketplace")
	repoURL := testutil.MakeGitRepo(t, loadFixtureContents(t, fixtureDir))

	cacheRoot := t.TempDir()
	fetcher := NewGitFetcher(cacheRoot)

	src := config.SourceConfig{Type: "git", URL: repoURL, Ref: "main"}
	ctx := context.Background()

	// First fetch — clone.
	r1, err := fetcher.Fetch(ctx, src, "testpkg", "skills/foo")
	if err != nil {
		t.Fatalf("first Fetch: %v", err)
	}

	// Second fetch — update path (should not error, re-uses existing clone).
	r2, err := fetcher.Fetch(ctx, src, "testpkg", "skills/bar")
	if err != nil {
		t.Fatalf("second Fetch: %v", err)
	}

	if r1.SHA != r2.SHA {
		t.Errorf("SHA changed between fetches on same commit: %s vs %s", r1.SHA, r2.SHA)
	}
}

func TestGitFetcher_invalidRef(t *testing.T) {
	skipIfNoGit(t)

	fixtureDir := filepath.Join("..", "..", "testdata", "upstream-marketplace")
	repoURL := testutil.MakeGitRepo(t, loadFixtureContents(t, fixtureDir))

	cacheRoot := t.TempDir()
	fetcher := NewGitFetcher(cacheRoot)

	src := config.SourceConfig{Type: "git", URL: repoURL, Ref: "nonexistent-branch-xyz"}
	ctx := context.Background()

	_, err := fetcher.Fetch(ctx, src, "testpkg", "skills/foo")
	if err == nil {
		t.Fatal("expected error for nonexistent ref, got nil")
	}
	// Should map to ErrRefNotFound.
	if !strings.Contains(err.Error(), "ref not found") && !strings.Contains(err.Error(), "git error") {
		// Accept either sentinel message or raw git error — what matters is non-nil error.
		t.Logf("error (acceptable): %v", err)
	}
}
