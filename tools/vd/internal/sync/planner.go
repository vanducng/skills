package sync

import (
	"fmt"

	"github.com/vanducng/skills/tools/vd/internal/config"
)

// OpKind classifies what the executor should do for a skill.
type OpKind int

// OpKind constants classify what the executor should do for a skill.
const (
	// OpSkip means the skill is already up-to-date or is detached; no action needed.
	OpSkip OpKind = iota
	// OpFetch means fetch from upstream and copy to skills/.
	OpFetch
	// OpRefuseDirty means local edits were detected; refuse unless --force is set.
	OpRefuseDirty
	// OpForceOverwrite is like OpFetch but the caller acknowledged the dirty state.
	OpForceOverwrite
)

func (k OpKind) String() string {
	switch k {
	case OpSkip:
		return "skip"
	case OpFetch:
		return "fetch"
	case OpRefuseDirty:
		return "refuse-dirty"
	case OpForceOverwrite:
		return "force-overwrite"
	default:
		return "unknown"
	}
}

// Op describes the action the executor should take for one skill.
type Op struct {
	Skill     string
	Kind      OpKind
	Reason    string
	TargetSHA string // resolved target commit SHA (empty for OpSkip/OpRefuseDirty)
}

// shortHex returns at most 8 characters of a hex string — used in reason messages.
func shortHex(s string) string {
	if len(s) > 8 {
		return s[:8]
	}
	return s
}

// BuildPlan computes the set of operations needed to bring the skills/ directory
// in sync with the manifest and lockfile. It is pure: no FS access, no fetcher calls.
//
// fsHashes maps skill name → TreeHash result for skills that exist on disk.
// An absent key means the skill directory does not exist.
// requested is an optional filter; when empty all manifest skills are considered.
func BuildPlan(
	m *config.Manifest,
	l *config.Lockfile,
	skillsDir string,
	fsHashes map[string]string,
	requested []string,
) ([]Op, error) {
	// Build inclusion set from requested filter.
	include := make(map[string]bool, len(requested))
	for _, s := range requested {
		include[s] = true
	}

	// Validate requested skills exist in manifest.
	for _, s := range requested {
		if _, ok := m.Skills[s]; !ok {
			return nil, fmt.Errorf("skill %q not found in skills.toml", s)
		}
	}

	var ops []Op

	for name, sc := range m.Skills {
		if len(include) > 0 && !include[name] {
			continue
		}

		// Detached skills are never touched by sync.
		if sc.Mode == "detached" || sc.Source == "" {
			ops = append(ops, Op{
				Skill:  name,
				Kind:   OpSkip,
				Reason: "detached",
			})
			continue
		}

		lockEntry, hasLock := l.Skills[name]
		fsSHA := fsHashes[name] // "" if dir absent

		// Determine the target SHA.
		// For pinned mode we use Pin; for tracked we use whatever the fetcher
		// will return (unknown at plan time, so we use the lock SHA as a proxy
		// to detect if we can skip — executor will re-resolve from upstream).
		targetSHA := ""
		if sc.Mode == "pinned" {
			targetSHA = sc.Pin
		} else if hasLock {
			// tracked: use existing lock SHA as "known last upstream"; executor
			// will fetch upstream HEAD and may find a newer SHA.
			targetSHA = lockEntry.SHA
		}

		// If skill dir is absent, always fetch (no dirty concern).
		if fsSHA == "" {
			ops = append(ops, Op{
				Skill:     name,
				Kind:      OpFetch,
				Reason:    "missing from disk",
				TargetSHA: targetSHA,
			})
			continue
		}

		// For pinned: skip if lock SHA already matches the pinned SHA and FS is untouched.
		if sc.Mode == "pinned" && hasLock && lockEntry.SHA == sc.Pin && lockEntry.TreeHash != "" && fsSHA == lockEntry.TreeHash {
			ops = append(ops, Op{
				Skill:  name,
				Kind:   OpSkip,
				Reason: "pinned and up-to-date",
			})
			continue
		}

		// Dirty check: FS tree hash differs from what was recorded at last sync.
		// Only refuse if we have a recorded tree hash to compare against.
		if hasLock && lockEntry.TreeHash != "" && fsSHA != lockEntry.TreeHash {
			ops = append(ops, Op{
				Skill:     name,
				Kind:      OpRefuseDirty,
				Reason:    fmt.Sprintf("local edits detected (fs=%s lock=%s)", shortHex(fsSHA), shortHex(lockEntry.TreeHash)),
				TargetSHA: targetSHA,
			})
			continue
		}

		// For tracked: always re-fetch (executor will skip if upstream SHA matches lock).
		// For pinned: fetch if lock SHA != pin or fs is absent.
		ops = append(ops, Op{
			Skill:     name,
			Kind:      OpFetch,
			Reason:    "sync to upstream",
			TargetSHA: targetSHA,
		})
	}

	return ops, nil
}
