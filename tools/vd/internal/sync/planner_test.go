package sync

import (
	"testing"

	"github.com/vanducng/skills/tools/vd/internal/config"
)

func makeManifest(skills map[string]config.SkillConfig) *config.Manifest {
	return &config.Manifest{
		Sources: map[string]config.SourceConfig{
			"upstream": {Type: "git", URL: "https://example.com/repo"},
		},
		Skills: skills,
	}
}

func makeLock(skills map[string]config.LockEntry) *config.Lockfile {
	return &config.Lockfile{Skills: skills}
}

func findOp(ops []Op, skill string) (Op, bool) {
	for _, op := range ops {
		if op.Skill == skill {
			return op, true
		}
	}
	return Op{}, false
}

func TestBuildPlan_Detached(t *testing.T) {
	m := makeManifest(map[string]config.SkillConfig{
		"myskill": {Mode: "detached"},
	})
	l := makeLock(nil)

	ops, err := BuildPlan(m, l, "/skills", nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	op, ok := findOp(ops, "myskill")
	if !ok {
		t.Fatal("expected op for myskill")
	}
	if op.Kind != OpSkip {
		t.Errorf("expected OpSkip, got %v", op.Kind)
	}
}

func TestBuildPlan_NoSourceIsDetached(t *testing.T) {
	m := makeManifest(map[string]config.SkillConfig{
		"myskill": {Source: "", Mode: "tracked"},
	})
	l := makeLock(nil)

	ops, err := BuildPlan(m, l, "/skills", nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	op, ok := findOp(ops, "myskill")
	if !ok {
		t.Fatal("expected op for myskill")
	}
	if op.Kind != OpSkip {
		t.Errorf("expected OpSkip for no-source skill, got %v", op.Kind)
	}
}

func TestBuildPlan_MissingFromDisk_Fetch(t *testing.T) {
	m := makeManifest(map[string]config.SkillConfig{
		"myskill": {Source: "upstream", Path: "skills/myskill", Mode: "tracked"},
	})
	l := makeLock(nil)
	fsHashes := map[string]string{} // absent

	ops, err := BuildPlan(m, l, "/skills", fsHashes, nil)
	if err != nil {
		t.Fatal(err)
	}
	op, ok := findOp(ops, "myskill")
	if !ok {
		t.Fatal("expected op for myskill")
	}
	if op.Kind != OpFetch {
		t.Errorf("expected OpFetch for missing skill, got %v", op.Kind)
	}
}

func TestBuildPlan_Dirty_RefuseDirty(t *testing.T) {
	m := makeManifest(map[string]config.SkillConfig{
		"myskill": {Source: "upstream", Path: "skills/myskill", Mode: "tracked"},
	})
	l := makeLock(map[string]config.LockEntry{
		// TreeHash is what planner uses for dirty detection.
		"myskill": {SHA: "aaa111", TreeHash: "aaa111"},
	})
	fsHashes := map[string]string{
		"myskill": "bbb222", // differs from lock TreeHash
	}

	ops, err := BuildPlan(m, l, "/skills", fsHashes, nil)
	if err != nil {
		t.Fatal(err)
	}
	op, ok := findOp(ops, "myskill")
	if !ok {
		t.Fatal("expected op for myskill")
	}
	if op.Kind != OpRefuseDirty {
		t.Errorf("expected OpRefuseDirty, got %v", op.Kind)
	}
}

func TestBuildPlan_PinnedUpToDate_Skip(t *testing.T) {
	const sha = "deadbeef"
	const treeHash = "treehash1234"
	m := makeManifest(map[string]config.SkillConfig{
		"myskill": {Source: "upstream", Path: "skills/myskill", Mode: "pinned", Pin: sha},
	})
	l := makeLock(map[string]config.LockEntry{
		// TreeHash is what planner uses for dirty detection; SHA must match Pin for skip.
		"myskill": {SHA: sha, TreeHash: treeHash},
	})
	fsHashes := map[string]string{
		"myskill": treeHash, // FS tree hash matches what was recorded at last sync
	}

	ops, err := BuildPlan(m, l, "/skills", fsHashes, nil)
	if err != nil {
		t.Fatal(err)
	}
	op, ok := findOp(ops, "myskill")
	if !ok {
		t.Fatal("expected op for myskill")
	}
	if op.Kind != OpSkip {
		t.Errorf("expected OpSkip for pinned+up-to-date, got %v", op.Kind)
	}
}

func TestBuildPlan_RequestedFilter(t *testing.T) {
	m := makeManifest(map[string]config.SkillConfig{
		"skill-a": {Source: "upstream", Path: "skills/a", Mode: "tracked"},
		"skill-b": {Source: "upstream", Path: "skills/b", Mode: "tracked"},
	})
	l := makeLock(nil)

	ops, err := BuildPlan(m, l, "/skills", nil, []string{"skill-a"})
	if err != nil {
		t.Fatal(err)
	}
	if len(ops) != 1 {
		t.Errorf("expected 1 op (filtered), got %d", len(ops))
	}
	if ops[0].Skill != "skill-a" {
		t.Errorf("expected skill-a, got %s", ops[0].Skill)
	}
}

func TestBuildPlan_RequestedUnknown(t *testing.T) {
	m := makeManifest(map[string]config.SkillConfig{})
	l := makeLock(nil)

	_, err := BuildPlan(m, l, "/skills", nil, []string{"nonexistent"})
	if err == nil {
		t.Error("expected error for unknown skill in requested filter")
	}
}

func TestBuildPlan_TrackedFetch(t *testing.T) {
	m := makeManifest(map[string]config.SkillConfig{
		"myskill": {Source: "upstream", Path: "skills/myskill", Mode: "tracked"},
	})
	const lockSHA = "abc123"
	l := makeLock(map[string]config.LockEntry{
		"myskill": {SHA: lockSHA},
	})
	fsHashes := map[string]string{
		"myskill": lockSHA, // FS matches lock — clean
	}

	ops, err := BuildPlan(m, l, "/skills", fsHashes, nil)
	if err != nil {
		t.Fatal(err)
	}
	op, ok := findOp(ops, "myskill")
	if !ok {
		t.Fatal("expected op for myskill")
	}
	// tracked always fetches (executor decides if upstream SHA changed)
	if op.Kind != OpFetch {
		t.Errorf("expected OpFetch for tracked+clean skill, got %v", op.Kind)
	}
}
