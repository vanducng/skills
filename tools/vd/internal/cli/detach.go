package cli

import (
	"fmt"
	"path/filepath"

	"github.com/spf13/cobra"

	"github.com/vanducng/skills/tools/vd/internal/config"
)

func newDetachCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "detach <skill>",
		Short: "Detach a skill from upstream tracking",
		Long: `Sets the skill's mode to 'detached', clears source/path/pin, and removes
it from skills.lock. The skill directory in skills/<name>/ is left untouched.

After detaching, 'vd sync' will skip the skill entirely, leaving you free to
edit it without interference.`,
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			return runDetach(cmd, args[0])
		},
	}
}

func runDetach(cmd *cobra.Command, skillName string) error {
	root, err := resolveRepoRoot(flagRoot)
	if err != nil {
		return err
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

	if sc.Mode == "detached" {
		if !flagQuiet {
			_, _ = fmt.Fprintf(cmd.OutOrStdout(), "skill %s is already detached\n", skillName)
		}
		return nil
	}

	sc.Mode = "detached"
	sc.Source = ""
	sc.Path = ""
	sc.Pin = ""
	manifest.Skills[skillName] = sc

	if err := config.Save(manifestPath, manifest); err != nil {
		return fmt.Errorf("save skills.toml: %w", err)
	}

	// Remove from lock.
	lockPath := filepath.Join(root, "skills.lock")
	lock, err := config.LoadLock(lockPath)
	if err != nil {
		return fmt.Errorf("load skills.lock: %w", err)
	}

	delete(lock.Skills, skillName)

	if err := config.SaveLock(lockPath, lock); err != nil {
		return fmt.Errorf("save skills.lock: %w", err)
	}

	if !flagQuiet {
		_, _ = fmt.Fprintf(cmd.OutOrStdout(), "detached %s (skills/%s/ unchanged)\n", skillName, skillName)
	}
	return nil
}
