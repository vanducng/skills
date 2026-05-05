package source

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

// marketplaceFile is the well-known path within a fetched upstream repo.
const marketplaceFile = ".claude-plugin/marketplace.json"

// marketplaceJSON mirrors the structure of a marketplace.json file.
type marketplaceJSON struct {
	Plugins []marketplacePlugin `json:"plugins"`
}

type marketplacePlugin struct {
	Name        string `json:"name"`
	Description string `json:"description"`
	Path        string `json:"path"`
}

// parseMarketplace reads <localDir>/.claude-plugin/marketplace.json and returns
// one CatalogEntry per plugin. Returns os.ErrNotExist if the file is absent.
func parseMarketplace(localDir string) (*Catalog, error) {
	path := filepath.Join(localDir, marketplaceFile)

	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err // caller checks os.IsNotExist
	}

	var mj marketplaceJSON
	if err := json.Unmarshal(data, &mj); err != nil {
		return nil, fmt.Errorf("parse %s: %w", path, err)
	}

	entries := make([]CatalogEntry, 0, len(mj.Plugins))
	for _, p := range mj.Plugins {
		if p.Name == "" || p.Path == "" {
			continue
		}
		entries = append(entries, CatalogEntry{
			Name:        p.Name,
			Path:        p.Path,
			Description: p.Description,
			Source:      "marketplace",
		})
	}

	return &Catalog{Skills: entries}, nil
}
