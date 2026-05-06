package cli

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"

	"github.com/vanducng/skills/tools/vd/internal/updatecheck"
	"github.com/vanducng/skills/tools/vd/internal/version"
)

const (
	envDisableCheck = "VD_NO_UPDATE_CHECK"
	envCI           = "CI"
	repoSlug        = "vanducng/skills"
	fetchTimeout    = 2 * time.Second
	cacheTTL        = 24 * time.Hour
)

// nudgeWait is how long PostRun will block waiting for the nudge to
// be printable. Short — keeps the CLI snappy.
// cacheWait is the *additional* tail PostRun will silently wait so the
// goroutine can finish its cache write before main exits. Without it,
// os.Exit kills the goroutine and the cache never populates on a slow
// first run, leaving the next run to repeat the same race.
// Both are vars (not const) so tests can shorten them.
var (
	nudgeWait = 50 * time.Millisecond
	cacheWait = 3 * time.Second
)

// pendingCheck holds an in-flight version lookup. Populated by the
// background goroutine; consumed by printUpdateNudge once the command
// finishes. A nil value means "no check ran" — gates failed.
type pendingCheck struct {
	done   chan struct{}
	result updatecheck.Result
	err    error
}

// startUpdateCheck kicks off a background lookup. Returns nil if any
// gating condition fails (dev build, CI, opt-out env, non-TTY stderr,
// cache path resolution failure). Caller stores the handle and passes
// it to printUpdateNudge after the subcommand returns.
func startUpdateCheck(ctx context.Context) *pendingCheck {
	if version.Version == "dev" {
		return nil
	}
	if os.Getenv(envDisableCheck) != "" {
		return nil
	}
	if os.Getenv(envCI) != "" {
		return nil
	}
	if !stderrIsTerminal() {
		return nil
	}

	cachePath, err := updatecheck.ResolveCachePath()
	if err != nil {
		return nil
	}

	// Fast path: a fresh cache lets us return synchronously with a
	// pre-completed handle. Avoids spawning a goroutine and racing
	// main's exit on the common path.
	if cached, err := updatecheck.ReadCache(cachePath); err == nil {
		if time.Since(cached.FetchedAt) < cacheTTL {
			cached.Current = version.Version
			done := make(chan struct{})
			close(done)
			return &pendingCheck{done: done, result: cached}
		}
	}

	checker := &updatecheck.Checker{
		Repo:      repoSlug,
		Current:   version.Version,
		UserAgent: "vd/" + version.Version,
		HTTP:      &http.Client{Timeout: fetchTimeout},
		CachePath: cachePath,
		TTL:       cacheTTL,
	}

	pc := &pendingCheck{done: make(chan struct{})}
	// Detach from cobra's ctx: it gets canceled when the subcommand
	// returns, but we want the cache write to complete on a normal lookup.
	_ = ctx
	go func() {
		defer close(pc.done)
		fetchCtx, cancel := context.WithTimeout(context.Background(), fetchTimeout)
		defer cancel()
		pc.result, pc.err = checker.Check(fetchCtx)
	}()
	return pc
}

// printUpdateNudge waits up to nudgeWait for the goroutine to complete
// and prints a stderr nudge if a newer version is available. If the
// goroutine misses the nudge window, we silently keep waiting up to
// cacheWait so the cache write can land before main exits — that
// guarantees a future run will hit the fast path.
func printUpdateNudge(pc *pendingCheck, w io.Writer, quiet bool) {
	if pc == nil {
		return
	}

	select {
	case <-pc.done:
		// Got result quickly — fall through to print logic.
	case <-time.After(nudgeWait):
		// Goroutine still running. Drain silently so the cache write
		// has a chance to complete before os.Exit kills it.
		select {
		case <-pc.done:
		case <-time.After(cacheWait - nudgeWait):
		}
		return
	}

	if pc.err != nil {
		return
	}
	if !pc.result.NeedsUpgrade() {
		return
	}
	if quiet {
		return
	}

	_, _ = fmt.Fprintf(w, "vd %s (latest: %s). Upgrade: brew upgrade vd\n",
		pc.result.Current, pc.result.Latest)
}

// stderrIsTerminal returns true when os.Stderr is a character device,
// which is a reasonable proxy for "user is watching this terminal" and
// avoids printing the nudge when stderr is captured by tooling.
func stderrIsTerminal() bool {
	info, err := os.Stderr.Stat()
	if err != nil {
		return false
	}
	return (info.Mode() & os.ModeCharDevice) != 0
}
