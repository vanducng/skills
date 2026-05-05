// Package target implements the pluggable Emitter interface and its registry.
package target

import (
	"github.com/vanducng/skills/tools/vd/internal/config"
)

// Emitter produces one or more output files from the current manifest + lock state.
type Emitter interface {
	// Name returns the canonical emitter identifier (e.g. "claude", "agents").
	Name() string
	// Emit writes all output files for this target.
	Emit(ctx Context) error
}

// Context carries all inputs an Emitter needs; callers must not mutate fields.
type Context struct {
	Manifest *config.Manifest
	Lock     *config.Lockfile
	RepoRoot string // absolute path to repo root
}
