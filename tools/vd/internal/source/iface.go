// Package source provides abstractions for fetching upstream skill content.
package source

import (
	"context"

	"github.com/vanducng/skills/tools/vd/internal/config"
)

// Fetcher fetches upstream content for a given source and sub-path.
type Fetcher interface {
	Fetch(ctx context.Context, src config.SourceConfig, srcName, path string) (FetchResult, error)
}

// FetchResult holds the outcome of a successful fetch operation.
type FetchResult struct {
	// LocalDir is the filesystem path to the fetched content (cache dir root).
	LocalDir string
	// SHA is the resolved HEAD commit SHA of the upstream repo.
	SHA string
	// Catalog is the detected skill catalog from the fetched content.
	Catalog *Catalog
}

// Catalog describes available skills discovered in a fetched upstream source.
type Catalog struct {
	Skills []CatalogEntry
}

// CatalogEntry describes a single skill entry in a catalog.
type CatalogEntry struct {
	// Name is the canonical identifier for the skill.
	Name string
	// Path is the sub-path within the upstream repo (e.g. "skills/stagehand").
	Path string
	// Description is the optional human-readable description.
	Description string
	// Source is the catalog type that produced this entry ("marketplace" or "raw").
	Source string
}
