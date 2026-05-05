package cli

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"

	"github.com/spf13/cobra"

	"github.com/vanducng/skills/tools/vd/internal/config"
	"github.com/vanducng/skills/tools/vd/internal/source"
)

func newDiffCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "diff <skill>",
		Short: "Show diff between cache and local skill directory",
		Long: `Shells out to 'git diff --no-index' to compare the cached upstream copy
of a skill against the local skills/<name>/ directory. Exit code mirrors git diff
(0 = identical, 1 = differences, >1 = error).`,
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			return runDiff(cmd, args[0])
		},
	}
}

func runDiff(cmd *cobra.Command, skillName string) error {
	root, err := resolveRepoRoot(flagRoot)
	if err != nil {
		return err
	}

	lockPath := filepath.Join(root, "skills.lock")
	lock, err := config.LoadLock(lockPath)
	if err != nil {
		return fmt.Errorf("load skills.lock: %w", err)
	}

	entry, ok := lock.Skills[skillName]
	if !ok {
		return fmt.Errorf("skill %q not found in skills.lock; run 'vd sync' first", skillName)
	}

	manifestPath := filepath.Join(root, "skills.toml")
	manifest, err := config.Load(manifestPath)
	if err != nil {
		return fmt.Errorf("load skills.toml: %w", err)
	}

	sc, ok := manifest.Skills[skillName]
	if !ok {
		return fmt.Errorf("skill %q not found in skills.toml", skillName)
	}

	cacheDir := filepath.Join(source.CacheRoot(root), sc.Source, sc.Path)
	if _, err := os.Stat(cacheDir); err != nil {
		return fmt.Errorf("cache for %q not found at %s; run 'vd sync' to populate it", skillName, cacheDir)
	}
	_ = entry // lock entry validated above; cache path derived from manifest

	localDir := filepath.Join(root, "skills", skillName)

	gitBin, err := exec.LookPath("git")
	if err != nil {
		return fmt.Errorf("git not found in PATH: %w", err)
	}

	// Stream git diff --no-index directly; exit code passes through via RunE.
	gitCmd := exec.Command(gitBin, "diff", "--no-index", "--color", cacheDir, localDir)
	gitCmd.Stdout = cmd.OutOrStdout()
	gitCmd.Stderr = cmd.ErrOrStderr()

	if err := gitCmd.Run(); err != nil {
		// Exit code 1 means differences found — not an error for this command.
		if exitErr, ok := err.(*exec.ExitError); ok && exitErr.ExitCode() == 1 {
			os.Exit(1)
		}
		return fmt.Errorf("git diff: %w", err)
	}
	return nil
}
