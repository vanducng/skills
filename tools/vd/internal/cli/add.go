package cli

import (
	"context"
	"fmt"
	"path/filepath"
	"strings"

	"github.com/spf13/cobra"

	"github.com/vanducng/skills/tools/vd/internal/config"
	"github.com/vanducng/skills/tools/vd/internal/source"
)

func newAddCmd() *cobra.Command {
	var (
		asFlag      string
		modeFlag    string
		refFlag     string
		refreshFlag bool
	)

	cmd := &cobra.Command{
		Use:   "add <source>/<path>",
		Short: "Add a skill from an upstream source to skills.toml",
		Long: `Fetch skill metadata from an upstream git source and register the skill
in skills.toml. Does not copy files locally — that is done by 'vd sync' (phase 04).

The <source>/<path> argument must contain at least one slash. If <source> is not
declared in [sources], it is auto-registered as a GitHub source when the argument
looks like owner/repo/... (three or more slash-separated parts).`,
		Args: cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			return runAdd(cmd, args[0], asFlag, modeFlag, refFlag, refreshFlag)
		},
	}

	cmd.Flags().StringVar(&asFlag, "as", "", "Override the skill name in skills.toml")
	cmd.Flags().StringVar(&modeFlag, "mode", "tracked", "Tracking mode: tracked or pinned")
	cmd.Flags().StringVar(&refFlag, "ref", "", "Override branch/tag/SHA (defaults to source ref or main)")
	cmd.Flags().BoolVar(&refreshFlag, "refresh", false, "Bypass cache TTL and re-fetch from upstream")

	return cmd
}

func runAdd(cmd *cobra.Command, arg, asFlag, modeFlag, refFlag string, refresh bool) error {
	// Parse <source>/<path> — require at least one slash.
	slashIdx := strings.Index(arg, "/")
	if slashIdx < 1 {
		return fmt.Errorf("argument must be <source>/<path> (e.g. browserbase/skills/stagehand); got %q", arg)
	}
	srcName := arg[:slashIdx]
	skillPath := arg[slashIdx+1:]
	if skillPath == "" {
		return fmt.Errorf("argument must be <source>/<path>; path part is empty in %q", arg)
	}

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

	src, err := resolveSource(manifest, srcName, arg, refFlag)
	if err != nil {
		return err
	}

	if refFlag != "" {
		src.Ref = refFlag
	}

	if err := source.RequireGit(ctx); err != nil {
		return err
	}

	cacheRoot := source.CacheRoot(root)
	fetcher := source.NewGitFetcher(cacheRoot)

	cacheDir := filepath.Join(cacheRoot, srcName)
	if refresh || source.Stale(cacheDir, source.DefaultTTL) {
		if !flagQuiet {
			_, _ = fmt.Fprintf(cmd.OutOrStdout(), "fetching %s ...\n", src.URL)
		}
	}

	result, err := fetcher.Fetch(ctx, src, srcName, skillPath)
	if err != nil {
		return fmt.Errorf("fetch %s: %w", srcName, err)
	}

	entry, err := resolveCatalogEntry(result.Catalog, skillPath)
	if err != nil {
		return err
	}

	skillName := asFlag
	if skillName == "" {
		skillName = entry.Name
	}
	if skillName == "" {
		skillName = filepath.Base(skillPath)
	}

	// Idempotency: no-op if skill is already tracked with identical config.
	if existing, ok := manifest.Skills[skillName]; ok {
		if existing.Source == srcName && existing.Path == skillPath && existing.Mode == modeFlag {
			if !flagQuiet {
				_, _ = fmt.Fprintf(cmd.OutOrStdout(), "skill %s already tracked, no changes\n", skillName)
			}
			return nil
		}
	}

	sc := config.SkillConfig{
		Source: srcName,
		Path:   skillPath,
		Mode:   modeFlag,
	}
	if modeFlag == "pinned" {
		sc.Pin = result.SHA
	}

	manifest.Sources[srcName] = src
	manifest.Skills[skillName] = sc

	if err := config.Save(manifestPath, manifest); err != nil {
		return fmt.Errorf("save skills.toml: %w", err)
	}

	shortSHA := result.SHA
	if len(shortSHA) > 8 {
		shortSHA = shortSHA[:8]
	}

	if !flagQuiet {
		_, _ = fmt.Fprintf(cmd.OutOrStdout(), "added skill %s from %s/%s (mode=%s, sha=%s)\n",
			skillName, srcName, skillPath, modeFlag, shortSHA)
	}
	return nil
}
