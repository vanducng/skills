package updatecheck

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"os"
	"time"
)

// devVersion is the version string used by local builds (no -ldflags stamp).
// Comparisons against this short-circuit: dev never needs an upgrade nudge.
const devVersion = "dev"

// Result is the cached form of one upstream lookup.
type Result struct {
	Current   string    `json:"current"`    // local version, e.g. "1.0.0" or "dev"
	Latest    string    `json:"latest"`     // upstream tag, normalized (no leading "v")
	URL       string    `json:"url"`        // release html_url
	FetchedAt time.Time `json:"fetched_at"` // for TTL freshness check
}

// NeedsUpgrade reports whether the running binary is strictly older than
// the latest upstream release. Always false for "dev" builds.
func (r Result) NeedsUpgrade() bool {
	if r.Current == devVersion || r.Current == "" || r.Latest == "" {
		return false
	}
	return Less(r.Current, r.Latest)
}

// HTTPClient is the minimum surface used by Checker. http.Client satisfies it.
type HTTPClient interface {
	Do(req *http.Request) (*http.Response, error)
}

// Checker performs the cached upstream lookup. All fields are set by the
// caller; nothing is read from globals.
type Checker struct {
	Repo      string        // "vanducng/skills"
	Current   string        // version.Version
	UserAgent string        // "vd/<version>"
	HTTP      HTTPClient    // http.DefaultClient in production; fake in tests
	CachePath string        // resolved via ResolveCachePath
	TTL       time.Duration // typical: 24h
	NowFunc   func() time.Time
}

// Check returns the freshest available Result. If the cache is fresh
// (<TTL old), no network call is made. Any error from the HTTP path is
// returned to the caller; the cache is left intact on failure.
func (c *Checker) Check(ctx context.Context) (Result, error) {
	now := c.now()

	if cached, err := ReadCache(c.CachePath); err == nil {
		if now.Sub(cached.FetchedAt) < c.TTL {
			cached.Current = c.Current
			return cached, nil
		}
	} else if !errors.Is(err, os.ErrNotExist) {
		// Corrupt cache: fall through and refetch; don't propagate.
		_ = err
	}

	r, err := c.fetch(ctx)
	if err != nil {
		return Result{}, err
	}
	r.Current = c.Current
	r.FetchedAt = now

	// Cache write failures are non-fatal — return the fresh result anyway.
	_ = WriteCache(c.CachePath, r)
	return r, nil
}

// fetch hits the GitHub releases-latest endpoint. Returns a Result with
// Latest and URL populated; Current and FetchedAt are stamped by Check.
func (c *Checker) fetch(ctx context.Context) (Result, error) {
	url := fmt.Sprintf("https://api.github.com/repos/%s/releases/latest", c.Repo)
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return Result{}, fmt.Errorf("build request: %w", err)
	}
	req.Header.Set("Accept", "application/vnd.github+json")
	req.Header.Set("User-Agent", c.UserAgent)
	req.Header.Set("X-GitHub-Api-Version", "2022-11-28")

	resp, err := c.HTTP.Do(req)
	if err != nil {
		return Result{}, fmt.Errorf("github fetch: %w", err)
	}
	defer func() { _ = resp.Body.Close() }()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return Result{}, fmt.Errorf("github status %d", resp.StatusCode)
	}

	var payload struct {
		TagName string `json:"tag_name"`
		HTMLURL string `json:"html_url"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&payload); err != nil {
		return Result{}, fmt.Errorf("decode github response: %w", err)
	}
	if payload.TagName == "" {
		return Result{}, fmt.Errorf("github response missing tag_name")
	}

	return Result{
		Latest: normalizeTag(payload.TagName),
		URL:    payload.HTMLURL,
	}, nil
}

func (c *Checker) now() time.Time {
	if c.NowFunc != nil {
		return c.NowFunc()
	}
	return time.Now()
}

// normalizeTag strips a leading "v" so the cached value is comparable
// without needing to remember the upstream tag style.
func normalizeTag(tag string) string {
	if len(tag) > 1 && (tag[0] == 'v' || tag[0] == 'V') {
		return tag[1:]
	}
	return tag
}
