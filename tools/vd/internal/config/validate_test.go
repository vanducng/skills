package config

import (
	"strings"
	"testing"
)

func TestValidate(t *testing.T) {
	cases := []struct {
		name        string
		manifest    *Manifest
		wantErr     bool
		errContains string
	}{
		{
			name: "pinned without pin",
			manifest: &Manifest{
				Skills: map[string]SkillConfig{
					"stagehand": {Source: "up", Path: "p", Mode: "pinned", Pin: ""},
				},
			},
			wantErr:     true,
			errContains: "requires non-empty pin",
		},
		{
			name: "tracked without source",
			manifest: &Manifest{
				Skills: map[string]SkillConfig{
					"stagehand": {Path: "p", Mode: "tracked"},
				},
			},
			wantErr:     true,
			errContains: "requires source",
		},
		{
			name: "tracked without path",
			manifest: &Manifest{
				Skills: map[string]SkillConfig{
					"stagehand": {Source: "up", Mode: "tracked"},
				},
			},
			wantErr:     true,
			errContains: "requires path",
		},
		{
			name: "detached with source",
			manifest: &Manifest{
				Skills: map[string]SkillConfig{
					"local": {Source: "up", Mode: "detached"},
				},
			},
			wantErr:     true,
			errContains: "forbids source",
		},
		{
			name: "detached with pin",
			manifest: &Manifest{
				Skills: map[string]SkillConfig{
					"local": {Pin: "abc123", Mode: "detached"},
				},
			},
			wantErr:     true,
			errContains: "forbids pin",
		},
		{
			name: "pinned with pin but missing path",
			manifest: &Manifest{
				Skills: map[string]SkillConfig{
					"stagehand": {Source: "up", Mode: "pinned", Pin: "abc123"},
				},
			},
			wantErr:     true,
			errContains: "requires path",
		},
		{
			name: "pinned with pin but missing source",
			manifest: &Manifest{
				Skills: map[string]SkillConfig{
					"stagehand": {Path: "p", Mode: "pinned", Pin: "abc123"},
				},
			},
			wantErr:     true,
			errContains: "requires source",
		},
		{
			name: "unknown mode",
			manifest: &Manifest{
				Skills: map[string]SkillConfig{
					"weird": {Mode: "flying"},
				},
			},
			wantErr:     true,
			errContains: "unknown mode",
		},
		{
			name: "valid tracked",
			manifest: &Manifest{
				Skills: map[string]SkillConfig{
					"ok": {Source: "up", Path: "p", Mode: "tracked"},
				},
			},
			wantErr: false,
		},
		{
			name: "valid pinned",
			manifest: &Manifest{
				Skills: map[string]SkillConfig{
					"ok": {Source: "up", Path: "p", Mode: "pinned", Pin: "abc1234"},
				},
			},
			wantErr: false,
		},
		{
			name: "valid detached",
			manifest: &Manifest{
				Skills: map[string]SkillConfig{
					"ok": {Mode: "detached"},
				},
			},
			wantErr: false,
		},
		{
			name: "all valid mixed",
			manifest: &Manifest{
				Skills: map[string]SkillConfig{
					"a": {Source: "up", Path: "pa", Mode: "tracked"},
					"b": {Source: "up", Path: "pb", Mode: "pinned", Pin: "sha1"},
					"c": {Mode: "detached"},
				},
			},
			wantErr: false,
		},
		{
			name:     "empty manifest",
			manifest: &Manifest{},
			wantErr:  false,
		},
		{
			name:        "nil manifest",
			manifest:    nil,
			wantErr:     true,
			errContains: "nil",
		},
	}

	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			err := Validate(tc.manifest)
			if tc.wantErr {
				if err == nil {
					t.Fatalf("expected error, got nil")
				}
				if tc.errContains != "" && !strings.Contains(err.Error(), tc.errContains) {
					t.Errorf("error %q does not contain %q", err.Error(), tc.errContains)
				}
			} else {
				if err != nil {
					t.Errorf("expected nil error, got: %v", err)
				}
			}
		})
	}
}

func TestValidateErrorAccumulation(t *testing.T) {
	// Two broken skills — both errors should appear in the joined message.
	m := &Manifest{
		Skills: map[string]SkillConfig{
			"alpha": {Mode: "pinned", Source: "up", Path: "p"}, // missing pin
			"beta":  {Mode: "tracked"},                         // missing source + path
		},
	}
	err := Validate(m)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	msg := err.Error()
	if !strings.Contains(msg, "alpha") {
		t.Errorf("error should mention alpha: %q", msg)
	}
	if !strings.Contains(msg, "beta") {
		t.Errorf("error should mention beta: %q", msg)
	}
}
