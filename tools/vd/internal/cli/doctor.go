package cli

import (
	"fmt"
	"os"
	"path/filepath"
	"text/tabwriter"

	"github.com/spf13/cobra"

	"github.com/vanducng/skills/tools/vd/internal/config"
	vdsync "github.com/vanducng/skills/tools/vd/internal/sync"
)

func newDoctorCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "doctor",
		Short: "Report drift between skills.lock and local skills/ directory",
		Long: `Walks all lock entries and compares their recorded SHA against the current
filesystem hash. Reports missing directories, local modifications, and skills
present on disk but absent from the lock (informational — these are typically
hand-authored or detached skills).

Always exits 0 (informational only).`,
		Args: cobra.NoArgs,
		RunE: func(cmd *cobra.Command, args []string) error {
			return runDoctor(cmd)
		},
	}
}

func runDoctor(cmd *cobra.Command) error {
	root, err := resolveRepoRoot(flagRoot)
	if err != nil {
		return err
	}

	lockPath := filepath.Join(root, "skills.lock")
	lock, err := config.LoadLock(lockPath)
	if err != nil {
		return fmt.Errorf("load skills.lock: %w", err)
	}

	skillsDir := filepath.Join(root, "skills")

	tw := tabwriter.NewWriter(cmd.OutOrStdout(), 0, 0, 2, ' ', 0)
	_, _ = fmt.Fprintln(tw, "SKILL\tSTATUS\tDETAIL")
	_, _ = fmt.Fprintln(tw, "-----\t------\t------")

	for name, entry := range lock.Skills {
		dir := filepath.Join(skillsDir, name)
		fsSHA := ""

		if _, statErr := os.Stat(dir); statErr == nil {
			fsSHA, _ = vdsync.TreeHash(dir)
		}

		// Use TreeHash for dirty detection; fall back to SHA for legacy entries.
		lockRef := entry.TreeHash
		if lockRef == "" {
			lockRef = entry.SHA
		}
		drift := vdsync.ComputeDrift(name, lockRef, fsSHA)

		detail := ""
		switch drift {
		case vdsync.DriftLocal:
			detail = fmt.Sprintf("lock=%s fs=%s", shortSHA(entry.SHA), shortSHA(fsSHA))
		case vdsync.DriftMissing:
			detail = fmt.Sprintf("expected at %s", dir)
		}

		_, _ = fmt.Fprintf(tw, "%s\t%s\t%s\n", name, drift, detail)
	}

	// Report FS dirs with no lock entry (hand-authored / detached) as informational.
	entries, _ := os.ReadDir(skillsDir)
	for _, e := range entries {
		if !e.IsDir() {
			continue
		}
		name := e.Name()
		if _, inLock := lock.Skills[name]; !inLock {
			_, _ = fmt.Fprintf(tw, "%s\t%s\t%s\n", name, "untracked", "(hand-authored or detached — OK)")
		}
	}

	if err := tw.Flush(); err != nil {
		return fmt.Errorf("flush tabwriter: %w", err)
	}
	return nil
}
