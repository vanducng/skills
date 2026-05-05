package sync

import "testing"

func TestComputeDrift(t *testing.T) {
	const (
		sha1 = "aaaa1111"
		sha2 = "bbbb2222"
	)

	cases := []struct {
		name     string
		lockSHA  string
		fsSHA    string
		expected DriftStatus
	}{
		{"no lock entry", "", sha1, DriftUntracked},
		{"dir missing", sha1, "", DriftMissing},
		{"hashes match", sha1, sha1, DriftNone},
		{"local edits", sha1, sha2, DriftLocal},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := ComputeDrift("myskill", tc.lockSHA, tc.fsSHA)
			if got != tc.expected {
				t.Errorf("ComputeDrift(%q, %q) = %v; want %v", tc.lockSHA, tc.fsSHA, got, tc.expected)
			}
		})
	}
}

func TestDriftStatus_String(t *testing.T) {
	cases := []struct {
		d    DriftStatus
		want string
	}{
		{DriftNone, "none"},
		{DriftLocal, "local"},
		{DriftMissing, "missing"},
		{DriftUntracked, "untracked"},
	}
	for _, tc := range cases {
		if got := tc.d.String(); got != tc.want {
			t.Errorf("DriftStatus(%d).String() = %q; want %q", tc.d, got, tc.want)
		}
	}
}
