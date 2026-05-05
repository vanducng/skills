// Package cli wires the Cobra command tree for the vd binary.
package cli

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"

	"github.com/vanducng/skills/tools/vd/internal/version"
)

// Global flag values — read by subcommands via Flags() on root or passed down.
var (
	flagQuiet   bool
	flagVerbose bool
	flagRoot    string
)

// NewRootCmd constructs and returns the root Cobra command.
// Callers should use Execute() rather than invoking this directly.
func NewRootCmd() *cobra.Command {
	root := &cobra.Command{
		Use:   "vd",
		Short: "Manage and vendor Claude skills in your repo",
		Long: `vd tracks, vendors, and publishes Claude skills inside a skills monorepo.

Run 'vd --help' on any subcommand for details.`,

		// Prevent Cobra from printing usage on every runtime error.
		SilenceUsage: true,
		// Let Execute() surface the error string; we format it ourselves.
		SilenceErrors: true,
	}

	root.Version = version.Version
	root.SetVersionTemplate("vd {{.Version}}\n")

	// Persistent flags — inherited by all subcommands.
	pf := root.PersistentFlags()
	pf.BoolVarP(&flagQuiet, "quiet", "q", false, "Suppress non-error output")
	pf.BoolVarP(&flagVerbose, "verbose", "v", false, "Verbose output (reserved for future phases)")
	pf.StringVar(&flagRoot, "root", "", "Override repo root path (must be an existing directory; takes precedence over VD_ROOT env var)")

	root.AddCommand(newInitCmd())
	root.AddCommand(newListCmd())
	root.AddCommand(newAddCmd())
	root.AddCommand(newCacheCmd())
	root.AddCommand(newSyncCmd())
	root.AddCommand(newUpdateCmd())
	root.AddCommand(newDiffCmd())
	root.AddCommand(newDoctorCmd())
	root.AddCommand(newDetachCmd())
	root.AddCommand(newPinCmd())
	root.AddCommand(newRemoveCmd())
	root.AddCommand(newBuildCmd())

	return root
}

// Execute runs the command tree and returns an exit code.
// main.go calls os.Exit(cli.Execute()).
func Execute() int {
	root := NewRootCmd()
	if err := root.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}
	return 0
}
