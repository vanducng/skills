// Package updatecheck queries the upstream release feed and decides whether
// the running binary is behind. It is intentionally minimal: stdlib only,
// no global state, all I/O injected.
package updatecheck

import (
	"strconv"
	"strings"
)

// parse extracts (major, minor, patch) from a version string, returning
// ok=false on anything unparseable. Handles a leading "v" and an optional
// alphabetic component prefix (e.g. "vd-v1.2.3" → 1.2.3). Pre-release and
// build metadata (anything after "-" or "+") cause ok=false — we'd rather
// drop the nudge than misrank.
func parse(s string) (major, minor, patch int, ok bool) {
	s = strings.TrimSpace(s)

	// Strip "<alpha>-" prefix (e.g. "vd-").
	if i := strings.Index(s, "-"); i > 0 && isAllAlpha(s[:i]) {
		s = s[i+1:]
	}

	// Strip leading "v" / "V".
	s = strings.TrimPrefix(s, "v")
	s = strings.TrimPrefix(s, "V")

	// Reject pre-release ("1.2.3-rc1") or build metadata ("1.2.3+meta").
	if strings.ContainsAny(s, "-+") {
		return 0, 0, 0, false
	}

	parts := strings.Split(s, ".")
	if len(parts) != 3 {
		return 0, 0, 0, false
	}

	var err error
	if major, err = strconv.Atoi(parts[0]); err != nil {
		return 0, 0, 0, false
	}
	if minor, err = strconv.Atoi(parts[1]); err != nil {
		return 0, 0, 0, false
	}
	if patch, err = strconv.Atoi(parts[2]); err != nil {
		return 0, 0, 0, false
	}
	return major, minor, patch, true
}

// Less reports whether semver a is strictly less than semver b. Returns
// false if either side is unparseable (conservative: no nudge).
func Less(a, b string) bool {
	am, an, ap, okA := parse(a)
	bm, bn, bp, okB := parse(b)
	if !okA || !okB {
		return false
	}
	if am != bm {
		return am < bm
	}
	if an != bn {
		return an < bn
	}
	return ap < bp
}

// Equal reports whether a and b normalize to the same (major, minor, patch).
// Returns false if either side is unparseable.
func Equal(a, b string) bool {
	am, an, ap, okA := parse(a)
	bm, bn, bp, okB := parse(b)
	if !okA || !okB {
		return false
	}
	return am == bm && an == bn && ap == bp
}

func isAllAlpha(s string) bool {
	if s == "" {
		return false
	}
	for _, r := range s {
		if (r < 'a' || r > 'z') && (r < 'A' || r > 'Z') {
			return false
		}
	}
	return true
}
