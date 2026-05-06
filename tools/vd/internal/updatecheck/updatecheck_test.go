package updatecheck

import (
	"context"
	"errors"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

// fakeHTTP returns canned responses and records calls. If the test forgets
// to inject one, hits are visible because Calls stays at 0.
type fakeHTTP struct {
	body       string
	statusCode int
	err        error
	calls      int
}

func (f *fakeHTTP) Do(req *http.Request) (*http.Response, error) {
	f.calls++
	if f.err != nil {
		return nil, f.err
	}
	status := f.statusCode
	if status == 0 {
		status = http.StatusOK
	}
	return &http.Response{
		StatusCode: status,
		Body:       io.NopCloser(strings.NewReader(f.body)),
		Header:     make(http.Header),
	}, nil
}

func newChecker(t *testing.T, http HTTPClient, current string) *Checker {
	t.Helper()
	return &Checker{
		Repo:      "vanducng/skills",
		Current:   current,
		UserAgent: "vd/" + current,
		HTTP:      http,
		CachePath: filepath.Join(t.TempDir(), "version-check.json"),
		TTL:       24 * time.Hour,
		NowFunc:   func() time.Time { return time.Date(2026, 5, 6, 0, 0, 0, 0, time.UTC) },
	}
}

const sampleBody = `{"tag_name": "v1.1.0", "html_url": "https://example.com/r/v1.1.0"}`

func TestChecker_NoCacheFetches(t *testing.T) {
	fh := &fakeHTTP{body: sampleBody}
	c := newChecker(t, fh, "1.0.0")

	r, err := c.Check(context.Background())
	if err != nil {
		t.Fatalf("Check: %v", err)
	}
	if fh.calls != 1 {
		t.Errorf("HTTP calls = %d, want 1", fh.calls)
	}
	if r.Latest != "1.1.0" {
		t.Errorf("Latest = %q, want 1.1.0", r.Latest)
	}
	if r.URL != "https://example.com/r/v1.1.0" {
		t.Errorf("URL = %q", r.URL)
	}
	if r.Current != "1.0.0" {
		t.Errorf("Current = %q, want 1.0.0", r.Current)
	}
	if !r.NeedsUpgrade() {
		t.Errorf("NeedsUpgrade should be true for 1.0.0 → 1.1.0")
	}
}

func TestChecker_FreshCacheHitNoFetch(t *testing.T) {
	fh := &fakeHTTP{body: sampleBody}
	c := newChecker(t, fh, "1.0.0")

	// Pre-populate cache 1h old (well within 24h TTL).
	cached := Result{
		Current:   "0.9.0", // intentionally stale; Check should overwrite with c.Current
		Latest:    "1.0.5",
		URL:       "https://example.com/r/v1.0.5",
		FetchedAt: c.NowFunc().Add(-1 * time.Hour),
	}
	if err := WriteCache(c.CachePath, cached); err != nil {
		t.Fatalf("seed cache: %v", err)
	}

	r, err := c.Check(context.Background())
	if err != nil {
		t.Fatalf("Check: %v", err)
	}
	if fh.calls != 0 {
		t.Errorf("HTTP calls = %d, want 0 (cache hit)", fh.calls)
	}
	if r.Latest != "1.0.5" {
		t.Errorf("Latest = %q, want 1.0.5 (from cache)", r.Latest)
	}
	if r.Current != "1.0.0" {
		t.Errorf("Current = %q, want 1.0.0 (overwritten by Checker.Current)", r.Current)
	}
}

func TestChecker_StaleCacheRefetches(t *testing.T) {
	fh := &fakeHTTP{body: sampleBody}
	c := newChecker(t, fh, "1.0.0")

	stale := Result{
		Latest:    "1.0.5",
		FetchedAt: c.NowFunc().Add(-25 * time.Hour),
	}
	if err := WriteCache(c.CachePath, stale); err != nil {
		t.Fatalf("seed cache: %v", err)
	}

	r, err := c.Check(context.Background())
	if err != nil {
		t.Fatalf("Check: %v", err)
	}
	if fh.calls != 1 {
		t.Errorf("HTTP calls = %d, want 1 (cache stale)", fh.calls)
	}
	if r.Latest != "1.1.0" {
		t.Errorf("Latest = %q, want 1.1.0 (refetched)", r.Latest)
	}
	// Cache should be rewritten with new FetchedAt.
	disk, err := ReadCache(c.CachePath)
	if err != nil {
		t.Fatalf("ReadCache after refetch: %v", err)
	}
	if !disk.FetchedAt.Equal(c.NowFunc()) {
		t.Errorf("FetchedAt = %v, want %v", disk.FetchedAt, c.NowFunc())
	}
}

func TestChecker_HTTPErrorBubbles(t *testing.T) {
	fh := &fakeHTTP{err: errors.New("dial tcp: no route")}
	c := newChecker(t, fh, "1.0.0")

	_, err := c.Check(context.Background())
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if _, err := ReadCache(c.CachePath); !errors.Is(err, os.ErrNotExist) {
		t.Errorf("cache should not exist on fetch error, err=%v", err)
	}
}

func TestChecker_HTTPNon2xxBubbles(t *testing.T) {
	fh := &fakeHTTP{statusCode: http.StatusForbidden, body: ""}
	c := newChecker(t, fh, "1.0.0")

	_, err := c.Check(context.Background())
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !strings.Contains(err.Error(), "403") {
		t.Errorf("error %q should mention 403", err.Error())
	}
}

func TestChecker_ContextCanceled(t *testing.T) {
	// Use a real http.Client with an immediately-canceled context — fake
	// would not exercise the context path because it doesn't honor ctx.
	c := newChecker(t, http.DefaultClient, "1.0.0")
	c.Repo = "vanducng/skills"
	// Point at a non-routable IP so even DNS doesn't matter; context
	// cancel should preempt before any TCP work completes.
	ctx, cancel := context.WithCancel(context.Background())
	cancel() // already canceled

	_, err := c.Check(ctx)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	// http client returns context.Canceled wrapped.
	if !errors.Is(err, context.Canceled) && !strings.Contains(err.Error(), "context canceled") {
		t.Errorf("error %q does not look like context cancellation", err.Error())
	}
}

func TestChecker_MissingTagNameFails(t *testing.T) {
	fh := &fakeHTTP{body: `{"html_url": "x"}`}
	c := newChecker(t, fh, "1.0.0")

	_, err := c.Check(context.Background())
	if err == nil {
		t.Fatal("expected error for missing tag_name")
	}
	if !strings.Contains(err.Error(), "tag_name") {
		t.Errorf("error %q should mention tag_name", err.Error())
	}
}

func TestResult_NeedsUpgrade(t *testing.T) {
	cases := []struct {
		name    string
		current string
		latest  string
		want    bool
	}{
		{"older_current", "1.0.0", "1.1.0", true},
		{"older_current_patch", "1.0.0", "1.0.1", true},
		{"same", "1.1.0", "1.1.0", false},
		{"newer_current", "2.0.0", "1.9.9", false},
		{"dev_build", "dev", "1.1.0", false},
		{"empty_current", "", "1.1.0", false},
		{"empty_latest", "1.0.0", "", false},
		{"unparseable", "garbage", "1.1.0", false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			r := Result{Current: tc.current, Latest: tc.latest}
			if got := r.NeedsUpgrade(); got != tc.want {
				t.Errorf("NeedsUpgrade() = %v, want %v", got, tc.want)
			}
		})
	}
}

func TestNormalizeTag(t *testing.T) {
	cases := map[string]string{
		"v1.0.0": "1.0.0",
		"V1.0.0": "1.0.0",
		"1.0.0":  "1.0.0",
		"v":      "v", // single char, leave alone
		"":       "",
	}
	for in, want := range cases {
		if got := normalizeTag(in); got != want {
			t.Errorf("normalizeTag(%q) = %q, want %q", in, got, want)
		}
	}
}
