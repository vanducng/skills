package cli

import (
	"github.com/spf13/cobra"
)

func newUpdateCmd() *cobra.Command {
	var forceFlag bool

	cmd := &cobra.Command{
		Use:   "update [skill...]",
		Short: "Bump tracked skills to upstream HEAD",
		Long: `Re-fetch upstream HEAD for all tracked skills (or a subset) and update
skills.lock. Pinned skills are skipped with a note — use 'vd pin' to change
the pinned SHA, then 'vd sync' to apply.

Detached skills are never touched.`,
		RunE: func(cmd *cobra.Command, args []string) error {
			return runSync(cmd, args, forceFlag, false, true)
		},
	}

	cmd.Flags().BoolVar(&forceFlag, "force", false, "Overwrite locally modified skills without refusing")
	return cmd
}
