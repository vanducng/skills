package cli

import (
	"fmt"
	"path/filepath"
	"sort"
	"text/tabwriter"

	"github.com/spf13/cobra"

	"github.com/vanducng/skills/tools/vd/internal/config"
)

func newListCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "list",
		Short: "List tracked skills from skills.toml",
		Long:  `Read skills.toml at the repo root and print a table of tracked skills.`,
		Args:  cobra.NoArgs,
		RunE: func(cmd *cobra.Command, _ []string) error {
			root, err := resolveRepoRoot(flagRoot)
			if err != nil {
				return err
			}

			manifest, err := config.Load(filepath.Join(root, "skills.toml"))
			if err != nil {
				return fmt.Errorf("load skills.toml: %w", err)
			}

			if len(manifest.Skills) == 0 {
				if !flagQuiet {
					_, _ = fmt.Fprintln(cmd.OutOrStdout(), "no skills tracked")
				}
				return nil
			}

			// Load lockfile; missing lock is not an error — SHA column shows "-".
			lock, err := config.LoadLock(filepath.Join(root, "skills.lock"))
			if err != nil {
				return fmt.Errorf("load skills.lock: %w", err)
			}

			// Sort names for deterministic output.
			names := make([]string, 0, len(manifest.Skills))
			for name := range manifest.Skills {
				names = append(names, name)
			}
			sort.Strings(names)

			w := tabwriter.NewWriter(cmd.OutOrStdout(), 0, 0, 2, ' ', 0)
			_, _ = fmt.Fprintln(w, "NAME\tSOURCE\tMODE\tSHA\tDRIFT")
			for _, name := range names {
				s := manifest.Skills[name]
				mode := s.Mode
				if mode == "" {
					mode = "-"
				}
				sha := "-"
				if entry, ok := lock.Skills[name]; ok && entry.SHA != "" {
					// Show first 8 chars of SHA for readability.
					sha = entry.SHA
					if len(sha) > 8 {
						sha = sha[:8]
					}
				}
				_, _ = fmt.Fprintf(w, "%s\t%s\t%s\t%s\t%s\n", name, s.Source, mode, sha, "-")
			}
			return w.Flush()
		},
	}
}
