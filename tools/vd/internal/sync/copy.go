package sync

import (
	"fmt"
	"io"
	"io/fs"
	"os"
	"path/filepath"
)

// atomicCopyDir copies the directory tree rooted at srcSubpath into dstFinal,
// staging the work in a sibling temp directory first, then renaming atomically.
//
// stagingParent must be on the same filesystem as dstFinal so that os.Rename
// is atomic. Callers typically pass filepath.Dir(dstFinal).
//
// Symlinks anywhere in srcSubpath are rejected with a descriptive error.
// Only regular files are copied; exec bit is preserved; full unix modes are not.
// Each written file is fsynced (best-effort) before the final rename.
func atomicCopyDir(srcSubpath, dstFinal, stagingParent string) error {
	stagingDir := filepath.Join(stagingParent, filepath.Base(dstFinal)+".tmp")

	// Clean any leftover staging dir from a previous interrupted run.
	_ = os.RemoveAll(stagingDir)

	if err := os.MkdirAll(stagingDir, 0o755); err != nil {
		return fmt.Errorf("create staging dir: %w", err)
	}

	// On any error, remove the incomplete staging dir.
	ok := false
	defer func() {
		if !ok {
			_ = os.RemoveAll(stagingDir)
		}
	}()

	err := filepath.WalkDir(srcSubpath, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}

		// Reject symlinks loudly.
		if d.Type()&fs.ModeSymlink != 0 {
			return fmt.Errorf("symlink rejected: %s", path)
		}

		relPath, err := filepath.Rel(srcSubpath, path)
		if err != nil {
			return fmt.Errorf("rel path: %w", err)
		}

		dst := filepath.Join(stagingDir, relPath)

		if d.IsDir() {
			return os.MkdirAll(dst, 0o755)
		}

		// Only copy regular files.
		if d.Type() != 0 {
			return nil
		}

		info, err := d.Info()
		if err != nil {
			return fmt.Errorf("stat %s: %w", path, err)
		}

		return copyFile(path, dst, info.Mode()&0o111 != 0)
	})
	if err != nil {
		return fmt.Errorf("copy tree: %w", err)
	}

	// Remove existing dstFinal before rename (rename over non-empty dir fails on some OS).
	if _, statErr := os.Lstat(dstFinal); statErr == nil {
		if err := os.RemoveAll(dstFinal); err != nil {
			return fmt.Errorf("remove existing %s: %w", dstFinal, err)
		}
	}

	if err := os.Rename(stagingDir, dstFinal); err != nil {
		return fmt.Errorf("rename staging to %s: %w", dstFinal, err)
	}

	ok = true
	return nil
}

// copyFile copies src to dst, preserving exec bit if execBit is true.
// The file is fsynced before close (best-effort).
func copyFile(src, dst string, execBit bool) error {
	perm := fs.FileMode(0o644)
	if execBit {
		perm = 0o755
	}

	in, err := os.Open(src)
	if err != nil {
		return fmt.Errorf("open src %s: %w", src, err)
	}
	defer func() { _ = in.Close() }()

	out, err := os.OpenFile(dst, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, perm)
	if err != nil {
		return fmt.Errorf("create dst %s: %w", dst, err)
	}

	_, copyErr := io.Copy(out, in)
	_ = out.Sync() // best-effort fsync
	closeErr := out.Close()

	if copyErr != nil {
		return fmt.Errorf("copy %s → %s: %w", src, dst, copyErr)
	}
	if closeErr != nil {
		return fmt.Errorf("close dst %s: %w", dst, closeErr)
	}
	return nil
}
