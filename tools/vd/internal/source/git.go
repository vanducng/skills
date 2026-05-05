package source

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/vanducng/skills/tools/vd/internal/config"
)

// gitFetcher implements Fetcher using shallow git clones + sparse-checkout.
type gitFetcher struct {
	cacheRoot string
}

// NewGitFetcher returns a Fetcher that caches clones under cacheRoot.
func NewGitFetcher(cacheRoot string) Fetcher {
	return &gitFetcher{cacheRoot: cacheRoot}
}

// catalogPatterns are checked out before catalog detection so DetectCatalog
// can read marketplace.json and walk skills/ regardless of the requested path.
var catalogPatterns = []string{".claude-plugin/", "skills/"}

// Fetch clones or updates the upstream repo, detects the catalog, then sets
// sparse-checkout to the requested path. srcName is the manifest source key
// used as the cache directory name.
func (f *gitFetcher) Fetch(ctx context.Context, src config.SourceConfig, srcName, path string) (FetchResult, error) {
	ref := src.Ref
	if ref == "" {
		ref = "main"
	}

	cacheDir := filepath.Join(f.cacheRoot, srcName)

	if _, err := os.Stat(filepath.Join(cacheDir, ".git")); os.IsNotExist(err) {
		if err := f.clone(ctx, src.URL, ref, cacheDir); err != nil {
			return FetchResult{}, err
		}
	} else {
		if err := f.update(ctx, ref, cacheDir); err != nil {
			return FetchResult{}, err
		}
	}

	// Broaden sparse-checkout to include catalog discovery paths first.
	// This ensures DetectCatalog can read marketplace.json and skills/ entries.
	catalogArgs := append([]string{"sparse-checkout", "set"}, catalogPatterns...)
	if err := runGit(ctx, cacheDir, catalogArgs...); err != nil {
		return FetchResult{}, fmt.Errorf("sparse-checkout set catalog patterns: %w", err)
	}

	sha, err := resolveHEAD(ctx, cacheDir)
	if err != nil {
		return FetchResult{}, err
	}

	catalog, err := DetectCatalog(cacheDir)
	if err != nil {
		return FetchResult{}, fmt.Errorf("detect catalog: %w", err)
	}

	// Now narrow sparse-checkout to only the requested path (forward slashes required).
	sparsePattern := filepath.ToSlash(path)
	if err := runGit(ctx, cacheDir, "sparse-checkout", "set", sparsePattern); err != nil {
		return FetchResult{}, fmt.Errorf("sparse-checkout set %q: %w", sparsePattern, err)
	}

	return FetchResult{
		LocalDir: cacheDir,
		SHA:      sha,
		Catalog:  catalog,
	}, nil
}

func (f *gitFetcher) clone(ctx context.Context, url, ref, dest string) error {
	if err := os.MkdirAll(filepath.Dir(dest), 0o755); err != nil {
		return fmt.Errorf("prepare cache dir: %w", err)
	}

	args := []string{
		"-c", "core.autocrlf=false",
		"clone",
		"--depth=1",
		"--filter=tree:0",
		"--sparse",
		"--branch", ref,
		url,
		dest,
	}
	cmd := exec.CommandContext(ctx, "git", args...)
	out, err := cmd.CombinedOutput()
	if err != nil {
		return classifyGitError(err, out)
	}
	return nil
}

func (f *gitFetcher) update(ctx context.Context, ref, cacheDir string) error {
	cmd := exec.CommandContext(ctx, "git", "-C", cacheDir, "fetch", "--depth=1", "origin", ref)
	out, err := cmd.CombinedOutput()
	if err != nil {
		return classifyGitError(err, out)
	}

	if err := runGit(ctx, cacheDir, "reset", "--hard", "FETCH_HEAD"); err != nil {
		return fmt.Errorf("reset to FETCH_HEAD: %w", err)
	}
	return nil
}

// runGit runs a git command with -C dir and returns a wrapped error on failure.
func runGit(ctx context.Context, dir string, args ...string) error {
	full := append([]string{"-C", dir}, args...)
	cmd := exec.CommandContext(ctx, "git", full...)
	out, err := cmd.CombinedOutput()
	if err != nil {
		return classifyGitError(err, out)
	}
	return nil
}

// resolveHEAD returns the full SHA of HEAD in the given git repo directory.
func resolveHEAD(ctx context.Context, dir string) (string, error) {
	cmd := exec.CommandContext(ctx, "git", "-C", dir, "rev-parse", "HEAD")
	out, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("rev-parse HEAD: %w", err)
	}
	return strings.TrimSpace(string(out)), nil
}

// classifyGitError maps known git error substrings to sentinel errors.
func classifyGitError(execErr error, output []byte) error {
	s := strings.ToLower(string(output))

	switch {
	case strings.Contains(s, "authentication failed") ||
		strings.Contains(s, "could not read username") ||
		strings.Contains(s, "repository not found") && strings.Contains(s, "fatal: repository"):
		return fmt.Errorf("%w: %s", ErrAuthRequired, strings.TrimSpace(string(output)))
	case strings.Contains(s, "couldn't find remote ref") ||
		strings.Contains(s, "invalid branch name") ||
		strings.Contains(s, "remote branch") && strings.Contains(s, "not found"):
		return fmt.Errorf("%w: %s", ErrRefNotFound, strings.TrimSpace(string(output)))
	default:
		return fmt.Errorf("git error: %w: %s", execErr, strings.TrimSpace(string(output)))
	}
}
