package config

import (
	"errors"
	"fmt"
	"sort"
)

// Validate checks all skills in the manifest against their mode rules.
// All errors are accumulated and returned together via errors.Join.
//
// Mode rules:
//   - "pinned"   → pin must be non-empty; source + path required
//   - "tracked"  → source + path required; pin must be empty
//   - "detached" → source and pin must both be empty
func Validate(m *Manifest) error {
	if m == nil {
		return errors.New("manifest is nil")
	}

	// Sort names for deterministic error ordering.
	names := make([]string, 0, len(m.Skills))
	for name := range m.Skills {
		names = append(names, name)
	}
	sort.Strings(names)

	var errs []error
	for _, name := range names {
		s := m.Skills[name]
		errs = append(errs, validateSkill(name, s)...)
	}

	return errors.Join(errs...)
}

func validateSkill(name string, s SkillConfig) []error {
	var errs []error
	add := func(msg string) {
		errs = append(errs, fmt.Errorf("skill %q: %s", name, msg))
	}

	switch s.Mode {
	case "pinned":
		if s.Pin == "" {
			add(fmt.Sprintf("mode=pinned requires non-empty pin (set [skills.%s].pin)", name))
		}
		if s.Source == "" {
			add(fmt.Sprintf("mode=pinned requires source (set [skills.%s].source)", name))
		}
		if s.Path == "" {
			add(fmt.Sprintf("mode=pinned requires path (set [skills.%s].path)", name))
		}

	case "tracked":
		if s.Source == "" {
			add(fmt.Sprintf("mode=tracked requires source (set [skills.%s].source)", name))
		}
		if s.Path == "" {
			add(fmt.Sprintf("mode=tracked requires path (set [skills.%s].path)", name))
		}

	case "detached":
		if s.Source != "" {
			add(fmt.Sprintf("mode=detached forbids source (remove [skills.%s].source)", name))
		}
		if s.Pin != "" {
			add(fmt.Sprintf("mode=detached forbids pin (remove [skills.%s].pin)", name))
		}

	default:
		add(fmt.Sprintf("unknown mode %q (must be tracked, pinned, or detached)", s.Mode))
	}

	return errs
}
