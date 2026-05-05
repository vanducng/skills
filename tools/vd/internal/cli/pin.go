package cli

import (
	"fmt"
	"path/filepath"

	"github.com/spf13/cobra"

	"github.com/vanducng/skills/tools/vd/internal/config"
)

func newPinCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "pin <skill> <sha>",
		Short: "Pin a skill to a specific upstream commit SHA",
		Long: `Sets the skill's mode to 'pinned' and records the given SHA. The SHA must
be at least 7 hex characters. Does NOT trigger a sync — run 'vd sync' afterward
to apply the pinned version locally.`,
		Args: cobra.ExactArgs(2),
		RunE: func(cmd *cobra.Command, args []string) error {
			return runPin(cmd, args[0], args[1])
		},
	}
}

func runPin(cmd *cobra.Command, skillName, sha string) error {
	if !isHexSHA(sha) {
		return fmt.Errorf("invalid SHA %q: must be at least 7 hex characters", sha)
	}

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

	sc.Mode = "pinned"
	sc.Pin = sha
	manifest.Skills[skillName] = sc

	if err := config.Save(manifestPath, manifest); err != nil {
		return fmt.Errorf("save skills.toml: %w", err)
	}

	if !flagQuiet {
		_, _ = fmt.Fprintf(cmd.OutOrStdout(), "pinned %s @ %s (run 'vd sync' to apply)\n", skillName, sha)
	}
	return nil
}

// isHexSHA returns true if s is at least 7 characters of lowercase/uppercase hex.
func isHexSHA(s string) bool {
	if len(s) < 7 {
		return false
	}
	for _, c := range s {
		if (c < '0' || c > '9') && (c < 'a' || c > 'f') && (c < 'A' || c > 'F') {
			return false
		}
	}
	return true
}
