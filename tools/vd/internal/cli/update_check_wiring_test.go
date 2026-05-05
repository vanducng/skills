package cli

import (
	"bytes"
	"context"
	"testing"
	"time"

	"github.com/vanducng/skills/tools/vd/internal/updatecheck"
	"github.com/vanducng/skills/tools/vd/internal/version"
)

// withVersion temporarily replaces version.Version for the duration of the
// test, restoring on cleanup.
func withVersion(t *testing.T, v string) {
	t.Helper()
	orig := version.Version
	version.Version = v
	t.Cleanup(func() { version.Version = orig })
}

func TestStartUpdateCheck_DevBuildReturnsNil(t *testing.T) {
	withVersion(t, "dev")
	t.Setenv(envDisableCheck, "")
	t.Setenv(envCI, "")
	if got := startUpdateCheck(context.Background()); got != nil {
		t.Errorf("expected nil for dev build, got %+v", got)
	}
}

func TestStartUpdateCheck_DisableEnvReturnsNil(t *testing.T) {
	withVersion(t, "1.0.0")
	t.Setenv(envDisableCheck, "1")
	if got := startUpdateCheck(context.Background()); got != nil {
		t.Errorf("expected nil with %s set, got %+v", envDisableCheck, got)
	}
}

func TestStartUpdateCheck_CIEnvReturnsNil(t *testing.T) {
	withVersion(t, "1.0.0")
	t.Setenv(envDisableCheck, "")
	t.Setenv(envCI, "true")
	if got := startUpdateCheck(context.Background()); got != nil {
		t.Errorf("expected nil with CI=true, got %+v", got)
	}
}

func TestPrintUpdateNudge_PrintsExpectedLine(t *testing.T) {
	pc := &pendingCheck{done: make(chan struct{})}
	pc.result = updatecheck.Result{
		Current: "1.0.0",
		Latest:  "1.1.0",
	}
	close(pc.done)

	var buf bytes.Buffer
	printUpdateNudge(pc, &buf, false)

	got := buf.String()
	want := "vd 1.0.0 (latest: 1.1.0). Upgrade: brew upgrade vd\n"
	if got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}

func TestPrintUpdateNudge_QuietSuppresses(t *testing.T) {
	pc := &pendingCheck{done: make(chan struct{})}
	pc.result = updatecheck.Result{Current: "1.0.0", Latest: "1.1.0"}
	close(pc.done)

	var buf bytes.Buffer
	printUpdateNudge(pc, &buf, true)
	if buf.Len() != 0 {
		t.Errorf("expected empty buffer, got %q", buf.String())
	}
}

func TestPrintUpdateNudge_NoUpgradeNeeded(t *testing.T) {
	pc := &pendingCheck{done: make(chan struct{})}
	pc.result = updatecheck.Result{Current: "1.1.0", Latest: "1.1.0"}
	close(pc.done)

	var buf bytes.Buffer
	printUpdateNudge(pc, &buf, false)
	if buf.Len() != 0 {
		t.Errorf("expected empty buffer, got %q", buf.String())
	}
}

func TestPrintUpdateNudge_DeadlineExceeded(t *testing.T) {
	// Shorten both deadlines so the test isn't slow.
	origNudge, origCache := nudgeWait, cacheWait
	nudgeWait = 10 * time.Millisecond
	cacheWait = 30 * time.Millisecond
	t.Cleanup(func() { nudgeWait, cacheWait = origNudge, origCache })

	// done channel is never closed → goroutine "stuck"; printUpdateNudge
	// must give up after cacheWait rather than hanging.
	pc := &pendingCheck{done: make(chan struct{})}

	var buf bytes.Buffer
	start := time.Now()
	printUpdateNudge(pc, &buf, false)
	elapsed := time.Since(start)

	if buf.Len() != 0 {
		t.Errorf("expected empty buffer on timeout, got %q", buf.String())
	}
	// Total elapsed should be ≈ cacheWait. 2x for slack.
	if elapsed > 2*cacheWait {
		t.Errorf("printUpdateNudge took %v; expected ≤ %v", elapsed, 2*cacheWait)
	}
	// Should have waited at least the nudge window.
	if elapsed < nudgeWait {
		t.Errorf("printUpdateNudge returned in %v; expected ≥ %v", elapsed, nudgeWait)
	}
}

func TestPrintUpdateNudge_NilPending(t *testing.T) {
	var buf bytes.Buffer
	printUpdateNudge(nil, &buf, false)
	if buf.Len() != 0 {
		t.Errorf("expected empty buffer for nil pending, got %q", buf.String())
	}
}

func TestPrintUpdateNudge_FetchError(t *testing.T) {
	pc := &pendingCheck{done: make(chan struct{})}
	pc.err = errFakeNetwork
	close(pc.done)

	var buf bytes.Buffer
	printUpdateNudge(pc, &buf, false)
	if buf.Len() != 0 {
		t.Errorf("expected empty buffer on fetch error, got %q", buf.String())
	}
}

// errFakeNetwork is used by the fetch-error test; declared at package
// scope so it doesn't leak into other test files.
var errFakeNetwork = fakeError("simulated network failure")

type fakeError string

func (e fakeError) Error() string { return string(e) }

// Sanity: confirm the wiring path doesn't accidentally fire real HTTP
// when nudge is supposed to be suppressed. We check this indirectly by
// asserting the gates above; a real network call would slow the test
// suite and flake offline.
func TestPrintUpdateNudge_NoNetworkOnSuppressedPaths(t *testing.T) {
	t.Setenv(envDisableCheck, "1")
	withVersion(t, "1.0.0")
	if pc := startUpdateCheck(context.Background()); pc != nil {
		t.Errorf("expected nil pendingCheck when disable env set, got %+v", pc)
	}
}
