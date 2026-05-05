package target

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"

	"github.com/vanducng/skills/tools/vd/internal/config"
)

type perSkillEmitter struct{}

func (e *perSkillEmitter) emit(ctx Context) error {
	meta := ctx.Manifest.Meta
	skillsDir := filepath.Join(ctx.RepoRoot, "skills")

	author := ownerInfo{
		Name: meta.OwnerName,
		URL:  meta.OwnerURL,
	}

	plugins, err := discoverSkillPlugins(skillsDir, ctx.Manifest, ctx.Lock, author, meta.Homepage)
	if err != nil {
		return fmt.Errorf("per-skill emitter: discover skills: %w", err)
	}

	sort.Slice(plugins, func(i, j int) bool {
		return plugins[i].Name < plugins[j].Name
	})

	doc := marketplaceDoc{
		Schema:      "https://anthropic.com/claude-code/marketplace.schema.json",
		Name:        meta.Name,
		Description: meta.Description,
		Owner:       author,
		Plugins:     plugins,
	}

	outDir := filepath.Join(ctx.RepoRoot, ".claude-plugin")
	if err := os.MkdirAll(outDir, 0o755); err != nil {
		return fmt.Errorf("per-skill emitter: ensure .claude-plugin dir: %w", err)
	}

	if err := writeJSON(filepath.Join(outDir, "marketplace.json"), doc); err != nil {
		return fmt.Errorf("per-skill emitter: write marketplace.json: %w", err)
	}

	// plugin.json is not written in per-skill mode (irrelevant for multi-plugin).
	return nil
}

// discoverSkillPlugins walks skillsDir, parses SKILL.md frontmatter for each
// subdirectory that has one, and resolves final plugin metadata.
func discoverSkillPlugins(
	skillsDir string,
	m *config.Manifest,
	lock *config.Lockfile,
	defaultAuthor ownerInfo,
	defaultHomepage string,
) ([]marketplacePlugin, error) {
	entries, err := os.ReadDir(skillsDir)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, fmt.Errorf("read skills dir: %w", err)
	}

	var plugins []marketplacePlugin
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		name := entry.Name()
		skillMD := filepath.Join(skillsDir, name, "SKILL.md")
		if _, err := os.Stat(skillMD); err != nil {
			continue // no SKILL.md — not a skill
		}

		fm, err := ParseFrontmatter(skillMD)
		if err != nil {
			return nil, fmt.Errorf("parse frontmatter for %s: %w", name, err)
		}

		// [plugin.<name>] override takes highest priority.
		var ov *PluginOverrideFields
		if m.Plugin != nil {
			if po, ok := m.Plugin[name]; ok {
				ov = &PluginOverrideFields{
					Description: po.Description,
					Version:     po.Version,
					Category:    po.Category,
					Homepage:    po.Homepage,
				}
			}
		}

		// Version: override > lock SHA short > git log > "0.0.0"
		version := resolveSkillVersion(name, skillsDir, lock, ov)

		defaults := PluginDefaults{
			Version:  version,
			Category: "utilities",
			Homepage: defaultHomepage,
			Author:   AuthorInfo(defaultAuthor),
		}

		source := "./skills/" + name
		entry := ResolvePlugin(name, ov, fm, defaults, source)

		plugins = append(plugins, marketplacePlugin{
			Name:        entry.Name,
			Description: entry.Description,
			Version:     entry.Version,
			Author:      ownerInfo{Name: entry.Author.Name, URL: entry.Author.URL},
			Source:      entry.Source,
			Category:    entry.Category,
			Homepage:    entry.Homepage,
		})
	}

	return plugins, nil
}

// resolveSkillVersion determines version for a per-skill plugin entry.
// Priority: override.Version > lock short SHA > git log short SHA > "0.0.0".
func resolveSkillVersion(
	name, skillsDir string,
	lock *config.Lockfile,
	ov *PluginOverrideFields,
) string {
	if ov != nil && ov.Version != "" {
		return ov.Version
	}
	if lock != nil {
		if entry, ok := lock.Skills[name]; ok && entry.SHA != "" {
			return shortSHA(entry.SHA)
		}
	}
	// Try git log for detached skills.
	sha := gitShortSHA(filepath.Join(skillsDir, name))
	if sha != "" {
		return sha
	}
	return "0.0.0"
}

func shortSHA(sha string) string {
	if len(sha) > 8 {
		return sha[:8]
	}
	return sha
}
