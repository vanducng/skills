package target

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
)

type agentsEmitter struct{}

func (e *agentsEmitter) Name() string { return "agents" }

func (e *agentsEmitter) Emit(ctx Context) error {
	skillsDir := filepath.Join(ctx.RepoRoot, "skills")
	agentsDir := filepath.Join(ctx.RepoRoot, ".agents", "skills")

	desired, err := discoverSkillNames(skillsDir)
	if err != nil {
		return fmt.Errorf("agents emitter: discover skills: %w", err)
	}

	if err := os.MkdirAll(agentsDir, 0o755); err != nil {
		return fmt.Errorf("agents emitter: create .agents dir: %w", err)
	}

	// Add/update desired entries.
	for _, name := range desired {
		skillPath := filepath.Join(skillsDir, name)
		agentPath := filepath.Join(agentsDir, name)

		// Path traversal defense: skill path must be inside repoRoot.
		if err := assertInsideRoot(skillPath, ctx.RepoRoot); err != nil {
			return fmt.Errorf("agents emitter: %w", err)
		}

		if runtime.GOOS == "windows" {
			if err := syncCopyDir(skillPath, agentPath); err != nil {
				return fmt.Errorf("agents emitter: copy %s: %w", name, err)
			}
		} else {
			// Relative symlink: ../skills/<name>
			rel, err := filepath.Rel(agentsDir, skillPath)
			if err != nil {
				return fmt.Errorf("agents emitter: rel path for %s: %w", name, err)
			}
			if err := ensureSymlink(agentPath, rel); err != nil {
				return fmt.Errorf("agents emitter: symlink %s: %w", name, err)
			}
		}
	}

	// Remove stale entries from the managed Codex skills directory only.
	desiredSet := make(map[string]struct{}, len(desired))
	for _, n := range desired {
		desiredSet[n] = struct{}{}
	}

	entries, err := os.ReadDir(agentsDir)
	if err != nil {
		return fmt.Errorf("agents emitter: read .agents dir: %w", err)
	}
	for _, entry := range entries {
		if _, ok := desiredSet[entry.Name()]; !ok {
			target := filepath.Join(agentsDir, entry.Name())
			if err := os.RemoveAll(target); err != nil {
				return fmt.Errorf("agents emitter: remove stale %s: %w", entry.Name(), err)
			}
		}
	}

	return nil
}

// discoverSkillNames returns the names of all subdirectories under skillsDir
// that contain a SKILL.md file.
func discoverSkillNames(skillsDir string) ([]string, error) {
	entries, err := os.ReadDir(skillsDir)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, fmt.Errorf("read skills dir: %w", err)
	}

	var names []string
	for _, e := range entries {
		if !e.IsDir() {
			continue
		}
		if _, statErr := os.Stat(filepath.Join(skillsDir, e.Name(), "SKILL.md")); statErr == nil {
			names = append(names, e.Name())
		}
	}
	return names, nil
}

// ensureSymlink creates or corrects a symlink at linkPath pointing to target.
// If it already points to the right target it is left untouched.
func ensureSymlink(linkPath, target string) error {
	existing, err := os.Readlink(linkPath)
	if err == nil {
		if existing == target {
			return nil // already correct
		}
		// Wrong target — remove and recreate.
		if err := os.Remove(linkPath); err != nil {
			return fmt.Errorf("remove stale symlink %s: %w", linkPath, err)
		}
	} else if !os.IsNotExist(err) {
		// Exists but is not a symlink (e.g. a directory from a previous copy fallback).
		if rmErr := os.RemoveAll(linkPath); rmErr != nil {
			return fmt.Errorf("remove non-symlink %s: %w", linkPath, rmErr)
		}
	}
	return os.Symlink(target, linkPath)
}

// assertInsideRoot returns an error if path escapes repoRoot.
func assertInsideRoot(path, repoRoot string) error {
	abs, err := filepath.Abs(path)
	if err != nil {
		return fmt.Errorf("resolve path %s: %w", path, err)
	}
	root, err := filepath.Abs(repoRoot)
	if err != nil {
		return fmt.Errorf("resolve root %s: %w", repoRoot, err)
	}
	if !strings.HasPrefix(abs+string(filepath.Separator), root+string(filepath.Separator)) {
		return fmt.Errorf("path %s escapes repo root %s", path, repoRoot)
	}
	return nil
}

// gitShortSHA runs `git -C dir log -n1 --format=%h` and returns the 8-char SHA.
// Returns "" on any failure.
func gitShortSHA(dir string) string {
	out, err := exec.Command("git", "-C", dir, "log", "-n1", "--format=%h").Output()
	if err != nil {
		return ""
	}
	return strings.TrimSpace(string(out))
}
