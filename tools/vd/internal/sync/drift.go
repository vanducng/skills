package sync

// DriftStatus describes the relationship between a skill's FS state and its lock entry.
type DriftStatus int

const (
	// DriftNone means FS hash matches lock SHA — no local changes.
	DriftNone DriftStatus = iota
	// DriftLocal means FS hash differs from lock SHA — user has edited files.
	DriftLocal
	// DriftMissing means the skill directory does not exist on disk.
	DriftMissing
	// DriftUntracked means there is no lock entry for this skill.
	DriftUntracked
)

func (d DriftStatus) String() string {
	switch d {
	case DriftNone:
		return "none"
	case DriftLocal:
		return "local"
	case DriftMissing:
		return "missing"
	case DriftUntracked:
		return "untracked"
	default:
		return "unknown"
	}
}

// ComputeDrift compares a skill's lock SHA with its current FS hash.
// lockSHA is the SHA stored in the lockfile ("" means no entry exists).
// fsSHA is the result of TreeHash on the skill dir ("" means dir is absent).
func ComputeDrift(skill, lockSHA, fsSHA string) DriftStatus {
	if lockSHA == "" {
		return DriftUntracked
	}
	if fsSHA == "" {
		return DriftMissing
	}
	if fsSHA != lockSHA {
		return DriftLocal
	}
	return DriftNone
}
