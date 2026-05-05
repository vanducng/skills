package cli

import (
	"fmt"
	"path/filepath"

	"github.com/spf13/cobra"

	"github.com/vanducng/skills/tools/vd/internal/config"
	"github.com/vanducng/skills/tools/vd/internal/target"
)

// defaultTargets lists the emitters run when no explicit target is given.
var defaultTargets = []string{"claude", "agents"}

func newBuildCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "build [target...]",
		Short: "Emit plugin files for configured targets (claude, agents)",
		Long: `Read skills.toml + skills.lock and emit output files for each target.

Targets: claude (marketplace.json + plugin.json), agents (.agents/ symlinks).
With no arguments all enabled targets are built.`,
		RunE: func(cmd *cobra.Command, args []string) error {
			root, err := resolveRepoRoot(flagRoot)
			if err != nil {
				return err
			}
			return runBuild(cmd, root, args)
		},
	}
	return cmd
}

// runBuild loads manifest + lock and emits each requested target.
// targets may be empty, in which case defaultTargets is used.
func runBuild(cmd *cobra.Command, repoRoot string, targets []string) error {
	manifestPath := filepath.Join(repoRoot, "skills.toml")
	manifest, err := config.Load(manifestPath)
	if err != nil {
		return fmt.Errorf("load skills.toml: %w", err)
	}

	// Seed defaults from live marketplace.json so first-run diff is zero.
	marketplacePath := filepath.Join(repoRoot, ".claude-plugin", "marketplace.json")
	config.ApplyDefaults(manifest, marketplacePath)

	lockPath := filepath.Join(repoRoot, "skills.lock")
	lock, err := config.LoadLock(lockPath)
	if err != nil {
		return fmt.Errorf("load skills.lock: %w", err)
	}

	ctx := target.Context{
		Manifest: manifest,
		Lock:     lock,
		RepoRoot: repoRoot,
	}

	names := targets
	if len(names) == 0 {
		names = defaultTargets
	}

	var built []string
	for _, name := range names {
		emitter, err := target.NewEmitter(name)
		if err != nil {
			return err
		}
		if err := emitter.Emit(ctx); err != nil {
			return fmt.Errorf("build %s: %w", name, err)
		}
		built = append(built, name)
	}

	if !flagQuiet {
		for _, name := range built {
			_, _ = fmt.Fprintf(cmd.OutOrStdout(), "built %s\n", name)
		}
	}
	return nil
}
