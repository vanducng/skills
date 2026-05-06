package updatecheck

import "testing"

func TestLess(t *testing.T) {
	cases := []struct {
		a, b string
		want bool
	}{
		// Basic numeric ordering.
		{"1.0.0", "1.1.0", true},
		{"1.0.0", "1.0.1", true},
		{"1.0.0", "2.0.0", true},
		{"1.1.0", "1.0.0", false},
		{"2.0.0", "1.9.9", false},
		// Equal → not less.
		{"1.0.0", "1.0.0", false},
		// Leading "v" stripped.
		{"v1.0.0", "v1.0.1", true},
		{"V1.0.0", "1.0.1", true},
		// Component prefix stripped.
		{"vd-v1.0.0", "vd-v1.0.1", true},
		{"vd-1.0.0", "1.0.1", true},
		// Pre-release / build metadata → conservative false.
		{"1.0.0-rc1", "1.0.0", false},
		{"1.0.0", "1.0.0-rc1", false},
		{"1.0.0+meta", "1.0.1", false},
		// Garbage → conservative false.
		{"garbage", "1.0.0", false},
		{"1.0.0", "garbage", false},
		{"1.0", "1.0.0", false},     // not three parts
		{"1.0.0.0", "1.0.0", false}, // four parts
		{"", "1.0.0", false},
	}
	for _, tc := range cases {
		t.Run(tc.a+"_vs_"+tc.b, func(t *testing.T) {
			if got := Less(tc.a, tc.b); got != tc.want {
				t.Errorf("Less(%q, %q) = %v, want %v", tc.a, tc.b, got, tc.want)
			}
		})
	}
}

func TestEqual(t *testing.T) {
	cases := []struct {
		a, b string
		want bool
	}{
		{"1.0.0", "1.0.0", true},
		{"v1.0.0", "1.0.0", true},
		{"vd-v1.0.0", "1.0.0", true},
		{"1.0.0", "1.0.1", false},
		{"1.0.0-rc1", "1.0.0", false},
		{"garbage", "1.0.0", false},
	}
	for _, tc := range cases {
		t.Run(tc.a+"_eq_"+tc.b, func(t *testing.T) {
			if got := Equal(tc.a, tc.b); got != tc.want {
				t.Errorf("Equal(%q, %q) = %v, want %v", tc.a, tc.b, got, tc.want)
			}
		})
	}
}

func TestIsAllAlpha(t *testing.T) {
	cases := map[string]bool{
		"":      false,
		"vd":    true,
		"VD":    true,
		"vd1":   false,
		"v-d":   false,
		"hello": true,
	}
	for in, want := range cases {
		if got := isAllAlpha(in); got != want {
			t.Errorf("isAllAlpha(%q) = %v, want %v", in, got, want)
		}
	}
}
