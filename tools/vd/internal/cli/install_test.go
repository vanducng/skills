package cli

import (
	"bytes"
	"path/filepath"
	"strings"
	"testing"

	"github.com/spf13/cobra"
)

func TestRunInstallCodex_DryRunOutput(t *testing.T) {
	root := setupE2ERepo(t)
	dest := filepath.Join(t.TempDir(), "codex-skills")
	cmd := &cobra.Command{}
	var out bytes.Buffer
	cmd.SetOut(&out)

	err := runInstallCodex(cmd, root, []string{"foo"}, installOptions{
		dest:   dest,
		dryRun: true,
	})
	if err != nil {
		t.Fatalf("runInstallCodex: %v", err)
	}
	got := out.String()
	if !strings.Contains(got, "would symlink codex skill foo -> "+filepath.Join(dest, "foo")) {
		t.Fatalf("output = %q", got)
	}
}

func TestRunInstallClaude_DryRunOutput(t *testing.T) {
	root := setupE2ERepo(t)
	cmd := &cobra.Command{}
	var out bytes.Buffer
	cmd.SetOut(&out)

	if err := runInstallClaude(cmd, root, installOptions{scope: "user", dryRun: true}); err != nil {
		t.Fatalf("runInstallClaude: %v", err)
	}
	got := out.String()
	for _, want := range []string{
		"would run: vd build claude",
		"would run: claude plugin marketplace add --scope user " + root,
		"would run: claude plugin install --scope user test-bundle@test-skills",
	} {
		if !strings.Contains(got, want) {
			t.Fatalf("output missing %q:\n%s", want, got)
		}
	}
}

func TestResolveInstallSelection(t *testing.T) {
	tests := []struct {
		name      string
		selection string
		wantAgent string
		wantScope string
		wantCopy  bool
	}{
		{
			name:      "codex user symlink is default choice",
			selection: "1",
			wantAgent: "codex",
			wantScope: "user",
		},
		{
			name:      "codex repo symlink",
			selection: "codex repo",
			wantAgent: "codex",
			wantScope: "repo",
		},
		{
			name:      "codex snapshot copy",
			selection: "snapshot",
			wantAgent: "codex",
			wantScope: "user",
			wantCopy:  true,
		},
		{
			name:      "claude plugin",
			selection: "claude-code",
			wantAgent: "claude",
			wantScope: "project",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			agent, opts, err := resolveInstallSelection(tt.selection, installOptions{scope: "project"})
			if err != nil {
				t.Fatalf("resolveInstallSelection: %v", err)
			}
			if agent != tt.wantAgent {
				t.Fatalf("agent = %q, want %q", agent, tt.wantAgent)
			}
			if opts.scope != tt.wantScope {
				t.Fatalf("scope = %q, want %q", opts.scope, tt.wantScope)
			}
			if opts.copy != tt.wantCopy {
				t.Fatalf("copy = %v, want %v", opts.copy, tt.wantCopy)
			}
		})
	}
}
