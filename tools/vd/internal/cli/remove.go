package cli

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/spf13/cobra"

	"github.com/vanducng/skills/tools/vd/internal/config"
	vdsync "github.com/vanducng/skills/tools/vd/internal/sync"
)

func newRemoveCmd() *cobra.Command {
	var keepFilesFlag bool
	var forceFlag bool

	cmd := &cobra.Command{
		Use:   "remove <skill>",
		Short: "Remove a skill from the manifest, lock, and optionally disk",
		Long: `Removes the skill from skills.toml and skills.lock. Unless --keep-files is
given, also deletes the skills/<name>/ directory.

Without --force, refuses to delete the directory if it has local modifications
(FS hash differs from lock SHA) to avoid silent data loss.`,
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			return runRemove(cmd, args[0], keepFilesFlag, forceFlag)
		},
	}

	cmd.Flags().BoolVar(&keepFilesFlag, "keep-files", false, "Do not delete skills/<name>/ from disk")
	cmd.Flags().BoolVar(&forceFlag, "force", false, "Delete even if local modifications detected")
	return cmd
}

func runRemove(cmd *cobra.Command, skillName string, keepFiles, force bool) error {
	root, err := resolveRepoRoot(flagRoot)
	if err != nil {
		return err
	}

	manifestPath := filepath.Join(root, "skills.toml")
	manifest, err := config.Load(manifestPath)
	if err != nil {
		return fmt.Errorf("load skills.toml: %w", err)
	}

	if _, ok := manifest.Skills[skillName]; !ok {
		return fmt.Errorf("skill %q not found in skills.toml", skillName)
	}

	lockPath := filepath.Join(root, "skills.lock")
	lock, err := config.LoadLock(lockPath)
	if err != nil {
		return fmt.Errorf("load skills.lock: %w", err)
	}

	skillDir := filepath.Join(root, "skills", skillName)

	if !keepFiles {
		// Guard against silent data loss: refuse if FS has local edits.
		if entry, inLock := lock.Skills[skillName]; inLock && !force {
			if _, statErr := os.Stat(skillDir); statErr == nil {
				fsSHA, hashErr := vdsync.TreeHash(skillDir)
				// Compare against TreeHash if available; fall back to SHA.
				lockRef := entry.TreeHash
				if lockRef == "" {
					lockRef = entry.SHA
				}
				if hashErr == nil && fsSHA != lockRef {
					return fmt.Errorf(
						"skill %q has local modifications (run 'vd detach %s' to keep edits, or use --force to delete anyway)",
						skillName, skillName,
					)
				}
			}
		}

		if err := os.RemoveAll(skillDir); err != nil {
			return fmt.Errorf("remove skills/%s: %w", skillName, err)
		}
	}

	delete(manifest.Skills, skillName)
	if err := config.Save(manifestPath, manifest); err != nil {
		return fmt.Errorf("save skills.toml: %w", err)
	}

	delete(lock.Skills, skillName)
	if err := config.SaveLock(lockPath, lock); err != nil {
		return fmt.Errorf("save skills.lock: %w", err)
	}

	if !flagQuiet {
		if keepFiles {
			_, _ = fmt.Fprintf(cmd.OutOrStdout(), "removed %s from manifest and lock (files kept)\n", skillName)
		} else {
			_, _ = fmt.Fprintf(cmd.OutOrStdout(), "removed %s\n", skillName)
		}
	}
	return nil
}
