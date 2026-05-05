package target

import (
	"bufio"
	"bytes"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"gopkg.in/yaml.v3"
)

// Frontmatter holds parsed SKILL.md YAML front-matter fields we care about.
type Frontmatter struct {
	Name        string `yaml:"name"`
	Description string `yaml:"description"`
}

// PluginDefaults are fallback values when neither override nor frontmatter supply a field.
type PluginDefaults struct {
	Version  string
	Category string
	Homepage string
	Author   AuthorInfo
}

// AuthorInfo mirrors the author object in marketplace.json.
type AuthorInfo struct {
	Name string
	URL  string
}

// PluginEntry is the resolved plugin metadata for one entry.
type PluginEntry struct {
	Name        string
	Description string
	Version     string
	Author      AuthorInfo
	Source      string
	Category    string
	Homepage    string
}

// ResolvePlugin applies the precedence chain: override > frontmatter > defaults.
// The name parameter is always used as-is (it comes from the directory name).
func ResolvePlugin(
	name string,
	override *PluginOverrideFields,
	fm Frontmatter,
	defaults PluginDefaults,
	source string,
) PluginEntry {
	entry := PluginEntry{
		Name:     name,
		Source:   source,
		Author:   defaults.Author,
		Version:  defaults.Version,
		Category: defaults.Category,
		Homepage: defaults.Homepage,
	}

	// Description: override > frontmatter > empty
	if override != nil && override.Description != "" {
		entry.Description = override.Description
	} else if fm.Description != "" {
		entry.Description = fm.Description
	}

	// Version: override > defaults
	if override != nil && override.Version != "" {
		entry.Version = override.Version
	}

	// Category: override > defaults
	if override != nil && override.Category != "" {
		entry.Category = override.Category
	}

	// Homepage: override > defaults
	if override != nil && override.Homepage != "" {
		entry.Homepage = override.Homepage
	}

	return entry
}

// PluginOverrideFields mirrors config.PluginOverride but avoids an import cycle
// in tests by keeping the target package self-contained for field access.
type PluginOverrideFields struct {
	Description string
	Version     string
	Category    string
	Homepage    string
}

// ParseFrontmatter reads the YAML front-matter from a SKILL.md file.
// Returns a zero-value Frontmatter on any parse failure.
func ParseFrontmatter(path string) (Frontmatter, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return Frontmatter{}, fmt.Errorf("read %s: %w", path, err)
	}
	return parseFrontmatterBytes(data)
}

func parseFrontmatterBytes(data []byte) (Frontmatter, error) {
	// Front-matter is delimited by "---" on its own line.
	if !bytes.HasPrefix(data, []byte("---")) {
		return Frontmatter{}, nil
	}
	// Find closing ---
	rest := data[3:]
	// Skip the newline after the opening ---
	if len(rest) > 0 && rest[0] == '\n' {
		rest = rest[1:]
	} else if len(rest) > 1 && rest[0] == '\r' && rest[1] == '\n' {
		rest = rest[2:]
	}

	scanner := bufio.NewScanner(bytes.NewReader(rest))
	var fmLines []string
	for scanner.Scan() {
		line := scanner.Text()
		if line == "---" {
			break
		}
		fmLines = append(fmLines, line)
	}

	raw := strings.Join(fmLines, "\n")
	var fm Frontmatter
	if err := yaml.Unmarshal([]byte(raw), &fm); err != nil {
		return Frontmatter{}, fmt.Errorf("parse frontmatter: %w", err)
	}
	return fm, nil
}

// DetectLicense reads <repoRoot>/LICENSE and returns an SPDX identifier.
// Falls back to fallbackLicense if file is absent or unrecognized.
// Scans up to the first 5 non-empty lines to handle multi-line headers (e.g. GPL version).
func DetectLicense(repoRoot, fallbackLicense string) string {
	path := filepath.Join(repoRoot, "LICENSE")
	data, err := os.ReadFile(path)
	if err != nil {
		return fallbackLicense
	}

	// Collect first 5 non-empty lines and join for pattern matching.
	scanner := bufio.NewScanner(bytes.NewReader(data))
	var header []string
	for scanner.Scan() && len(header) < 5 {
		line := strings.TrimSpace(scanner.Text())
		if line != "" {
			header = append(header, line)
		}
	}
	if len(header) == 0 {
		return fallbackLicense
	}
	upper := strings.ToUpper(strings.Join(header, " "))

	switch {
	case strings.Contains(upper, "MIT LICENSE"):
		return "MIT"
	case strings.Contains(upper, "APACHE"):
		return "Apache-2.0"
	case strings.Contains(upper, "GNU GENERAL PUBLIC LICENSE"):
		if strings.Contains(upper, "VERSION 3") {
			return "GPL-3.0"
		}
		return "GPL-2.0"
	case strings.Contains(upper, "BSD"):
		return "BSD-3-Clause"
	case strings.Contains(upper, "ISC LICENSE"):
		return "ISC"
	case strings.Contains(upper, "MOZILLA PUBLIC LICENSE"):
		return "MPL-2.0"
	}

	return fallbackLicense
}
