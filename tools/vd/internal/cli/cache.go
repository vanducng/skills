package cli

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/spf13/cobra"

	"github.com/vanducng/skills/tools/vd/internal/source"
)

func newCacheCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "cache",
		Short: "Manage the vd download cache",
		Long:  `Commands for inspecting and managing the .vd-cache/ directory.`,
	}
	cmd.AddCommand(newCacheCleanCmd())
	return cmd
}

func newCacheCleanCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "clean",
		Short: "Remove the .vd-cache/ directory",
		Long:  `Deletes .vd-cache/ at the repo root. The cache will be repopulated on next 'vd add' or 'vd sync'.`,
		Args:  cobra.NoArgs,
		RunE: func(cmd *cobra.Command, _ []string) error {
			root, err := resolveRepoRoot(flagRoot)
			if err != nil {
				return err
			}

			cacheDir := source.CacheRoot(root)

			// Report whether anything was actually removed.
			info, statErr := os.Stat(cacheDir)
			if os.IsNotExist(statErr) || (statErr == nil && !info.IsDir()) {
				if !flagQuiet {
					_, _ = fmt.Fprintln(cmd.OutOrStdout(), "cache empty")
				}
				return nil
			}

			// Collect the top-level entries to report what was removed.
			entries, readErr := os.ReadDir(cacheDir)
			removed := []string{}
			if readErr == nil {
				for _, e := range entries {
					removed = append(removed, filepath.Join(".vd-cache", e.Name()))
				}
			}

			if err := source.Clean(root); err != nil {
				return err
			}

			if !flagQuiet {
				if len(removed) == 0 {
					_, _ = fmt.Fprintln(cmd.OutOrStdout(), "removed .vd-cache/ (was empty)")
				} else {
					for _, r := range removed {
						_, _ = fmt.Fprintf(cmd.OutOrStdout(), "removed %s\n", r)
					}
				}
			}
			return nil
		},
	}
}
