package source

import (
	"errors"
	"fmt"
	"os"
)

// DetectCatalog discovers the skill catalog layout in localDir.
// It tries marketplace.json first; if that file is absent or produces no
// usable entries (e.g. all paths are null), it falls back to walking skills/.
// Returns an error if neither layout yields entries.
func DetectCatalog(localDir string) (*Catalog, error) {
	cat, err := parseMarketplace(localDir)
	if err != nil && !errors.Is(err, os.ErrNotExist) {
		return nil, fmt.Errorf("parse marketplace: %w", err)
	}
	// Use marketplace catalog only if it produced at least one usable entry.
	if err == nil && len(cat.Skills) > 0 {
		return cat, nil
	}

	// Marketplace absent or empty — try raw skills/ walk.
	cat, err = walkRaw(localDir)
	if err == nil {
		return cat, nil
	}

	return nil, fmt.Errorf("no catalog found in %s: no marketplace.json and no skills/ directory", localDir)
}
