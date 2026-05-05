package cli

import (
	"fmt"
	"strings"

	"github.com/vanducng/skills/tools/vd/internal/config"
	"github.com/vanducng/skills/tools/vd/internal/source"
)

// resolveSource looks up srcName in the manifest. If absent and the full
// argument looks like owner/repo/path (≥3 slash-separated parts), it
// auto-registers a GitHub git source. Returns ErrUnknownSource otherwise.
func resolveSource(manifest *config.Manifest, srcName, fullArg, refFlag string) (config.SourceConfig, error) {
	if src, ok := manifest.Sources[srcName]; ok {
		return src, nil
	}

	parts := strings.SplitN(fullArg, "/", 3)
	if len(parts) < 3 {
		return config.SourceConfig{}, fmt.Errorf(
			"%w: source %q not declared in [sources]; add it to skills.toml or use owner/repo/path syntax",
			source.ErrUnknownSource, srcName)
	}

	// parts[0]=owner, parts[1]=repo — build GitHub URL.
	return config.SourceConfig{
		Type: "git",
		URL:  fmt.Sprintf("https://github.com/%s/%s", parts[0], parts[1]),
		Ref:  refFlag,
	}, nil
}

// resolveCatalogEntry returns the CatalogEntry whose Path matches skillPath.
// When the catalog is empty or the path is absent, a synthetic entry is returned
// so the caller can still proceed (sparse-checkout already validated the path).
// A non-nil error is returned only when the catalog is non-empty and the path
// clearly does not exist, listing available options.
func resolveCatalogEntry(cat *source.Catalog, skillPath string) (source.CatalogEntry, error) {
	if cat == nil || len(cat.Skills) == 0 {
		return source.CatalogEntry{Path: skillPath}, nil
	}

	for _, e := range cat.Skills {
		if e.Path == skillPath || strings.HasPrefix(skillPath, e.Path+"/") {
			return e, nil
		}
	}

	available := make([]string, 0, len(cat.Skills))
	for _, e := range cat.Skills {
		available = append(available, fmt.Sprintf("  %s (%s)", e.Path, e.Name))
	}

	return source.CatalogEntry{}, fmt.Errorf(
		"path %q not found in upstream catalog; available skills:\n%s",
		skillPath, strings.Join(available, "\n"))
}
