package source

import (
	"bytes"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"gopkg.in/yaml.v3"
)

const skillsDir = "skills"
const skillMarker = "SKILL.md"

// skillFrontmatter holds the YAML frontmatter fields we care about in SKILL.md.
type skillFrontmatter struct {
	Name        string `yaml:"name"`
	Description string `yaml:"description"`
}

// walkRaw walks <localDir>/skills/ looking for SKILL.md files and parses their
// YAML frontmatter. Returns a Catalog with one entry per skill directory found.
func walkRaw(localDir string) (*Catalog, error) {
	root := filepath.Join(localDir, skillsDir)

	if _, err := os.Stat(root); err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil, fmt.Errorf("no skills/ directory found in %s", localDir)
		}
		return nil, fmt.Errorf("stat skills/: %w", err)
	}

	var entries []CatalogEntry

	err := filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() || d.Name() != skillMarker {
			return nil
		}

		fm, parseErr := parseFrontmatter(path)
		if parseErr != nil {
			// Skip files with unparseable frontmatter rather than aborting.
			return nil
		}

		// Compute the relative path from localDir (e.g. "skills/baz").
		rel, relErr := filepath.Rel(localDir, filepath.Dir(path))
		if relErr != nil {
			return relErr
		}
		rel = filepath.ToSlash(rel)

		name := fm.Name
		if name == "" {
			// Fall back to the directory name if frontmatter lacks a name.
			name = filepath.Base(filepath.Dir(path))
		}

		entries = append(entries, CatalogEntry{
			Name:        name,
			Path:        rel,
			Description: fm.Description,
			Source:      "raw",
		})
		return nil
	})
	if err != nil {
		return nil, fmt.Errorf("walk %s: %w", root, err)
	}

	return &Catalog{Skills: entries}, nil
}

// parseFrontmatter extracts YAML frontmatter delimited by "---" from a markdown file.
func parseFrontmatter(path string) (skillFrontmatter, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return skillFrontmatter{}, fmt.Errorf("read %s: %w", path, err)
	}

	content := strings.TrimPrefix(string(data), "\xef\xbb\xbf") // strip BOM
	if !strings.HasPrefix(content, "---") {
		return skillFrontmatter{}, fmt.Errorf("no frontmatter in %s", path)
	}

	// Find the closing "---" delimiter.
	rest := content[3:]
	end := strings.Index(rest, "\n---")
	if end == -1 {
		return skillFrontmatter{}, fmt.Errorf("unclosed frontmatter in %s", path)
	}

	raw := bytes.TrimSpace([]byte(rest[:end]))
	var fm skillFrontmatter
	if err := yaml.Unmarshal(raw, &fm); err != nil {
		return skillFrontmatter{}, fmt.Errorf("parse frontmatter in %s: %w", path, err)
	}
	return fm, nil
}
