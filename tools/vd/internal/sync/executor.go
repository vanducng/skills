package sync

import (
	"context"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"time"

	"github.com/vanducng/skills/tools/vd/internal/config"
	"github.com/vanducng/skills/tools/vd/internal/source"
)

// ExecResult records the outcome of executing one Op.
type ExecResult struct {
	Skill   string
	Kind    OpKind
	SHA     string
	Skipped bool
	Refused bool
	Err     error
}

// Execute walks the plan, calls the fetcher for OpFetch/OpForceOverwrite ops,
// copies files atomically, and returns an updated in-memory Lockfile.
//
// Caller must persist the returned Lockfile via config.SaveLock on success.
// If force is true, OpRefuseDirty ops are treated as OpForceOverwrite.
// Returns ErrRefuseDirty (wrapping details) if any op was refused without force.
func Execute(
	ctx context.Context,
	m *config.Manifest,
	l *config.Lockfile,
	fetcher source.Fetcher,
	repoRoot string,
	plan []Op,
	force bool,
) (*config.Lockfile, []ExecResult, error) {
	// Deep-copy the lock so we never mutate the caller's original on failure.
	newLock := copyLock(l)

	skillsDir := filepath.Join(repoRoot, "skills")
	results := make([]ExecResult, 0, len(plan))
	anyRefused := false

	for _, op := range plan {
		res := ExecResult{Skill: op.Skill, Kind: op.Kind}

		switch op.Kind {
		case OpSkip:
			res.Skipped = true

		case OpRefuseDirty:
			if !force {
				res.Refused = true
				anyRefused = true
				results = append(results, res)
				continue
			}
			// force=true: fall through to fetch logic below
			if err := executeFetch(ctx, m, newLock, fetcher, skillsDir, op, &res); err != nil {
				return nil, results, err
			}

		case OpFetch, OpForceOverwrite:
			if err := executeFetch(ctx, m, newLock, fetcher, skillsDir, op, &res); err != nil {
				return nil, results, err
			}
		}

		results = append(results, res)
	}

	if anyRefused {
		return newLock, results, ErrRefuseDirty
	}
	return newLock, results, nil
}

// executeFetch performs the fetch + atomic copy for a single Op and updates newLock in place.
func executeFetch(
	ctx context.Context,
	m *config.Manifest,
	newLock *config.Lockfile,
	fetcher source.Fetcher,
	skillsDir string,
	op Op,
	res *ExecResult,
) error {
	sc, ok := m.Skills[op.Skill]
	if !ok {
		return fmt.Errorf("skill %q not found in manifest", op.Skill)
	}

	src, ok := m.Sources[sc.Source]
	if !ok {
		return fmt.Errorf("source %q not declared in [sources]", sc.Source)
	}

	// For pinned mode, override the ref so fetcher checks out the exact SHA.
	fetchSrc := src
	if sc.Mode == "pinned" && sc.Pin != "" {
		fetchSrc.Ref = sc.Pin
	}

	result, err := fetcher.Fetch(ctx, fetchSrc, sc.Source, sc.Path)
	if err != nil {
		return fmt.Errorf("fetch %s: %w", op.Skill, err)
	}

	// Skip copy if already at the right upstream SHA and local tree is untouched.
	if entry, hasEntry := newLock.Skills[op.Skill]; hasEntry && entry.SHA == result.SHA {
		dstDir := filepath.Join(skillsDir, op.Skill)
		fsSHA, hashErr := TreeHash(dstDir)
		// entry.TreeHash is the hash recorded at last sync; fsSHA is current FS state.
		if hashErr == nil && entry.TreeHash != "" && fsSHA == entry.TreeHash {
			res.Skipped = true
			res.SHA = result.SHA
			return nil
		}
		// TreeHash mismatch or missing: FS is dirty or copy needed; fall through.
	}

	// srcSubpath is the skill's sub-directory inside the cache.
	srcSubpath := filepath.Join(result.LocalDir, sc.Path)
	dstFinal := filepath.Join(skillsDir, op.Skill)

	if err := os.MkdirAll(skillsDir, 0o755); err != nil {
		return fmt.Errorf("ensure skills dir: %w", err)
	}

	if err := atomicCopyDir(srcSubpath, dstFinal, skillsDir); err != nil {
		return fmt.Errorf("copy %s: %w", op.Skill, err)
	}

	// Compute tree hash of the freshly copied directory for future dirty-detection.
	treeHash, err := TreeHash(dstFinal)
	if err != nil {
		return fmt.Errorf("hash copied tree %s: %w", op.Skill, err)
	}

	// Measure copied tree for the lock entry.
	size, mtime := measureDir(dstFinal)

	newLock.Skills[op.Skill] = config.LockEntry{
		SHA:      result.SHA,
		TreeHash: treeHash,
		Source:   src.URL,
		Path:     sc.Path,
		Size:     size,
		Mtime:    mtime,
	}

	res.SHA = result.SHA
	return nil
}

// measureDir returns the total byte size and RFC3339 mtime of the newest file in dir.
func measureDir(dir string) (size int64, mtime string) {
	var newest time.Time
	_ = filepath.WalkDir(dir, func(path string, d fs.DirEntry, err error) error {
		if err != nil || d.IsDir() {
			return err
		}
		info, statErr := os.Stat(path)
		if statErr != nil {
			return nil
		}
		size += info.Size()
		if info.ModTime().After(newest) {
			newest = info.ModTime()
		}
		return nil
	})
	if !newest.IsZero() {
		mtime = newest.UTC().Format(time.RFC3339)
	}
	return size, mtime
}

// copyLock returns a deep copy of l so mutations don't affect the original.
func copyLock(l *config.Lockfile) *config.Lockfile {
	nl := &config.Lockfile{
		Generated: l.Generated,
		Skills:    make(map[string]config.LockEntry, len(l.Skills)),
	}
	for k, v := range l.Skills {
		nl.Skills[k] = v
	}
	return nl
}
