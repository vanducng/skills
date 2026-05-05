package cli

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/spf13/cobra"

	"github.com/vanducng/skills/tools/vd/internal/config"
	"github.com/vanducng/skills/tools/vd/internal/source"
	vdsync "github.com/vanducng/skills/tools/vd/internal/sync"
)

func newSyncCmd() *cobra.Command {
	var forceFlag bool
	var noBuildFlag bool

	cmd := &cobra.Command{
		Use:   "sync [skill...]",
		Short: "Sync tracked and pinned skills from upstream cache to skills/",
		Long: `Fetch upstream content for all tracked and pinned skills (or a subset),
copy them atomically into skills/<name>/, and update skills.lock.

Skills with local modifications refuse to sync unless --force is given.
Detached skills are always skipped.
After a successful sync, 'vd build' is run automatically unless --no-build is set.`,
		RunE: func(cmd *cobra.Command, args []string) error {
			return runSync(cmd, args, forceFlag, noBuildFlag, false)
		},
	}

	cmd.Flags().BoolVar(&forceFlag, "force", false, "Overwrite locally modified skills without refusing")
	cmd.Flags().BoolVar(&noBuildFlag, "no-build", false, "Skip automatic 'vd build' after successful sync")
	return cmd
}

// runSync is shared by sync and update (updateOnly restricts to mode=tracked).
func runSync(cmd *cobra.Command, requested []string, force, noBuild, updateOnly bool) error {
	ctx := context.Background()

	root, err := resolveRepoRoot(flagRoot)
	if err != nil {
		return err
	}

	manifestPath := filepath.Join(root, "skills.toml")
	manifest, err := config.Load(manifestPath)
	if err != nil {
		return fmt.Errorf("load skills.toml: %w", err)
	}

	lockPath := filepath.Join(root, "skills.lock")
	lock, err := config.LoadLock(lockPath)
	if err != nil {
		return fmt.Errorf("load skills.lock: %w", err)
	}

	if updateOnly {
		manifest = filterTracked(manifest)
	}

	skillsDir := filepath.Join(root, "skills")
	fsHashes := computeFSHashes(manifest, skillsDir)

	plan, err := vdsync.BuildPlan(manifest, lock, skillsDir, fsHashes, requested)
	if err != nil {
		return err
	}

	if err := source.RequireGit(ctx); err != nil {
		return err
	}

	cacheRoot := source.CacheRoot(root)
	fetcher := source.NewGitFetcher(cacheRoot)

	newLock, results, execErr := vdsync.Execute(ctx, manifest, lock, fetcher, root, plan, force)

	// Print per-skill results.
	for _, r := range results {
		switch {
		case r.Refused:
			_, _ = fmt.Fprintf(cmd.OutOrStdout(), "REFUSED  %s — local edits detected\n", r.Skill)
			_, _ = fmt.Fprintf(cmd.OutOrStdout(), "         run: vd detach %s  (keep edits) or use --force (overwrite)\n", r.Skill)
		case r.Skipped:
			if !flagQuiet {
				_, _ = fmt.Fprintf(cmd.OutOrStdout(), "skip     %s\n", r.Skill)
			}
		case r.Err != nil:
			_, _ = fmt.Fprintf(cmd.ErrOrStderr(), "ERROR    %s: %v\n", r.Skill, r.Err)
		default:
			_, _ = fmt.Fprintf(cmd.OutOrStdout(), "synced   %s @ %s\n", r.Skill, shortSHA(r.SHA))
		}
	}

	if execErr != nil {
		if vdsync.IsRefuseDirty(execErr) {
			_, _ = fmt.Fprintln(cmd.ErrOrStderr(), "\nSync aborted: refused skills listed above. Lock not updated.")
			return execErr
		}
		return execErr
	}

	// Count actual syncs.
	synced := 0
	for _, r := range results {
		if !r.Skipped && !r.Refused && r.Err == nil {
			synced++
		}
	}

	if synced == 0 && !flagQuiet {
		_, _ = fmt.Fprintln(cmd.OutOrStdout(), "all skills up to date")
	}

	newLock.Generated = time.Now().UTC().Format(time.RFC3339)
	if err := config.SaveLock(lockPath, newLock); err != nil {
		return fmt.Errorf("save skills.lock: %w", err)
	}

	if !noBuild {
		if err := runBuild(cmd, root, nil); err != nil {
			return fmt.Errorf("post-sync build: %w", err)
		}
	}

	return nil
}

// computeFSHashes returns TreeHash for each skill directory that exists on disk.
func computeFSHashes(m *config.Manifest, skillsDir string) map[string]string {
	hashes := make(map[string]string, len(m.Skills))
	for name := range m.Skills {
		dir := filepath.Join(skillsDir, name)
		if _, err := os.Stat(dir); err != nil {
			continue // missing → not in map
		}
		h, err := vdsync.TreeHash(dir)
		if err == nil {
			hashes[name] = h
		}
	}
	return hashes
}

// filterTracked returns a shallow copy of manifest with only mode=tracked skills.
func filterTracked(m *config.Manifest) *config.Manifest {
	out := &config.Manifest{
		Meta:    m.Meta,
		Sources: m.Sources,
		Skills:  make(map[string]config.SkillConfig),
		Targets: m.Targets,
		Plugin:  m.Plugin,
	}
	for name, sc := range m.Skills {
		if sc.Mode == "tracked" {
			out.Skills[name] = sc
		}
	}
	return out
}

func shortSHA(sha string) string {
	if len(sha) > 8 {
		return sha[:8]
	}
	return sha
}
