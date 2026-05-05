package config

import (
	"bytes"
	"errors"
	"fmt"
	"os"
	"path/filepath"

	"github.com/pelletier/go-toml/v2"
)

// Load reads path and returns a Manifest.
// If the file does not exist, an empty Manifest with defaults is returned (not an error).
func Load(path string) (*Manifest, error) {
	m := &Manifest{
		Sources: make(map[string]SourceConfig),
		Skills:  make(map[string]SkillConfig),
		Plugin:  make(map[string]PluginOverride),
	}

	data, err := os.ReadFile(path)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return m, nil
		}
		return nil, fmt.Errorf("read %s: %w", path, err)
	}

	if err := toml.Unmarshal(data, m); err != nil {
		return nil, fmt.Errorf("parse %s: %w", path, err)
	}

	// Ensure maps are never nil after unmarshal.
	if m.Sources == nil {
		m.Sources = make(map[string]SourceConfig)
	}
	if m.Skills == nil {
		m.Skills = make(map[string]SkillConfig)
	}
	if m.Plugin == nil {
		m.Plugin = make(map[string]PluginOverride)
	}

	return m, nil
}

// Save atomically writes the manifest to path (temp file + rename).
// Maps are serialized in alphabetic key order for stable diffs.
func Save(path string, m *Manifest) error {
	var buf bytes.Buffer
	enc := toml.NewEncoder(&buf)

	// pelletier/go-toml/v2 serializes struct fields in declaration order and
	// map keys in alphabetic order by default — no extra sort helpers needed.
	if err := enc.Encode(m); err != nil {
		return fmt.Errorf("encode manifest: %w", err)
	}

	return atomicWrite(path, buf.Bytes())
}

// atomicWrite writes data to path via a temp file + rename to avoid partial writes.
func atomicWrite(path string, data []byte) error {
	dir := filepath.Dir(path)
	tmp, err := os.CreateTemp(dir, ".vd-tmp-*")
	if err != nil {
		return fmt.Errorf("create temp file: %w", err)
	}
	tmpPath := tmp.Name()

	// Always remove the temp file on failure.
	ok := false
	defer func() {
		if !ok {
			_ = os.Remove(tmpPath)
		}
	}()

	if _, err := tmp.Write(data); err != nil {
		_ = tmp.Close()
		return fmt.Errorf("write temp file: %w", err)
	}
	if err := tmp.Close(); err != nil {
		return fmt.Errorf("close temp file: %w", err)
	}

	if err := os.Rename(tmpPath, path); err != nil {
		return fmt.Errorf("rename temp file to %s: %w", path, err)
	}

	ok = true
	return nil
}
