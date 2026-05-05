// Package sync implements the vd sync engine: tree hashing, drift detection,
// plan building, atomic copy, and execution.
package sync

import (
	"crypto/sha256"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// skipNames are file/dir names excluded from tree hashing.
var skipNames = map[string]bool{
	".DS_Store": true,
	"Thumbs.db": true,
	".git":      true,
}

// fileEntry holds the data collected for one file during a tree walk.
type fileEntry struct {
	relPath string
	execBit bool
	sha     string
}

// TreeHash computes a deterministic SHA-256 fingerprint of a directory tree.
// For each regular file it collects (relPath, execBit, sha256-of-content),
// sorts by relPath, then hashes the canonical joined lines.
// Returns an empty string and no error for an empty directory.
func TreeHash(dir string) (string, error) {
	var entries []fileEntry

	err := filepath.WalkDir(dir, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}

		name := d.Name()

		if d.IsDir() {
			if skipNames[name] && path != dir {
				return filepath.SkipDir
			}
			return nil
		}

		if skipNames[name] {
			return nil
		}

		// Only regular files — skip symlinks, devices, etc.
		if d.Type() != 0 {
			return nil
		}

		relPath, err := filepath.Rel(dir, path)
		if err != nil {
			return fmt.Errorf("rel path %s: %w", path, err)
		}
		relPath = filepath.ToSlash(relPath)

		info, err := d.Info()
		if err != nil {
			return fmt.Errorf("stat %s: %w", path, err)
		}
		execBit := info.Mode()&0o111 != 0

		fileSHA, err := sha256File(path)
		if err != nil {
			return err
		}

		entries = append(entries, fileEntry{
			relPath: relPath,
			execBit: execBit,
			sha:     fileSHA,
		})
		return nil
	})
	if err != nil {
		return "", fmt.Errorf("walk %s: %w", dir, err)
	}

	sort.Slice(entries, func(i, j int) bool {
		return entries[i].relPath < entries[j].relPath
	})

	var sb strings.Builder
	for i, e := range entries {
		exec := "0"
		if e.execBit {
			exec = "1"
		}
		if i > 0 {
			sb.WriteByte('\n')
		}
		sb.WriteString(e.relPath)
		sb.WriteByte('\t')
		sb.WriteString(exec)
		sb.WriteByte('\t')
		sb.WriteString(e.sha)
	}

	sum := sha256.Sum256([]byte(sb.String()))
	return fmt.Sprintf("%x", sum), nil
}

func sha256File(path string) (string, error) {
	f, err := os.Open(path)
	if err != nil {
		return "", fmt.Errorf("open %s: %w", path, err)
	}
	defer func() { _ = f.Close() }()

	h := sha256.New()
	if _, err := io.Copy(h, f); err != nil {
		return "", fmt.Errorf("hash %s: %w", path, err)
	}
	return fmt.Sprintf("%x", h.Sum(nil)), nil
}
