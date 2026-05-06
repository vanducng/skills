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

func TestResolveInstallSelection_ClaudeClearsCodexFlags(t *testing.T) {
	in := installOptions{
		scope: "user",
		dest:  "/tmp/somewhere",
		copy:  true,
		force: true,
	}
	agent, opts, err := resolveInstallSelection("4", in)
	if err != nil {
		t.Fatalf("resolveInstallSelection: %v", err)
	}
	if agent != "claude" {
		t.Fatalf("agent = %q, want claude", agent)
	}
	if opts.copy || opts.force || opts.dest != "" {
		t.Fatalf("codex-only flags not cleared: %+v", opts)
	}
}

func TestResolveInstallSelection_ClaudeRewritesRepoScope(t *testing.T) {
	// `--scope repo` is codex-only; if the user mixed it with a claude
	// pick, fall back to the safe default rather than carrying it over.
	agent, opts, err := resolveInstallSelection("claude", installOptions{scope: "repo"})
	if err != nil {
		t.Fatalf("resolveInstallSelection: %v", err)
	}
	if agent != "claude" || opts.scope != "user" {
		t.Fatalf("agent=%q scope=%q, want claude/user", agent, opts.scope)
	}
}

func TestRunInstall_RejectsUnknownAgentTypo(t *testing.T) {
	root := setupE2ERepo(t)
	cmd := &cobra.Command{}
	var out bytes.Buffer
	cmd.SetOut(&out)

	err := runInstall(cmd, root, []string{"codeex"}, installOptions{scope: "user"})
	if err == nil {
		t.Fatal("expected error for unknown agent typo")
	}
	if !strings.Contains(err.Error(), "unknown agent or skill") {
		t.Fatalf("unexpected error: %v", err)
	}
}
