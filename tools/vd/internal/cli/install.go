package cli

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/spf13/cobra"

	"github.com/vanducng/skills/tools/vd/internal/config"
	agentinstall "github.com/vanducng/skills/tools/vd/internal/install"
)

type installOptions struct {
	scope  string
	dest   string
	copy   bool
	force  bool
	dryRun bool
}

func newInstallCmd() *cobra.Command {
	var opts installOptions

	cmd := &cobra.Command{
		Use:   "install [agent] [skill...]",
		Short: "Install local skills into an agent environment",
		Long: `Install skills from this repository into a local agent environment.

Run without an agent to select an install target:
  1) Codex user skills       symlink to $HOME/.agents/skills
  2) Codex repo skills       symlink to .agents/skills
  3) Codex snapshot copy     copy to $HOME/.agents/skills
  4) Claude Code plugin      marketplace/plugin install

Agents:
  codex   installs skills into Codex discovery paths
  claude  registers and installs this repo as a Claude Code plugin`,
		Args: cobra.ArbitraryArgs,
		RunE: func(cmd *cobra.Command, args []string) error {
			root, err := resolveRepoRoot(flagRoot)
			if err != nil {
				return err
			}
			return runInstall(cmd, root, args, opts)
		},
	}

	cmd.Flags().StringVar(&opts.scope, "scope", "user", "Install scope: codex user|repo, claude user|project|local")
	cmd.Flags().StringVar(&opts.dest, "dest", "", "Override Codex destination directory")
	cmd.Flags().BoolVar(&opts.copy, "copy", false, "Copy skills instead of symlinking them")
	cmd.Flags().BoolVar(&opts.force, "force", false, "Replace existing installed skill directories")
	cmd.Flags().BoolVar(&opts.dryRun, "dry-run", false, "Print actions without changing files")

	return cmd
}

func runInstall(cmd *cobra.Command, repoRoot string, args []string, opts installOptions) error {
	agent := ""
	skills := args
	if len(args) > 0 && isKnownInstallAgent(args[0]) {
		agent = normalizeInstallAgent(args[0])
		skills = args[1:]
	}

	if agent == "" {
		pickedAgent, pickedOpts, err := promptInstallSelection(cmd, opts)
		if err != nil {
			return err
		}
		agent = pickedAgent
		opts = pickedOpts
	}

	switch agent {
	case "codex":
		return runInstallCodex(cmd, repoRoot, skills, opts)
	case "claude":
		if len(skills) > 0 {
			return fmt.Errorf("claude install does not accept skill names; it installs the configured plugin bundle")
		}
		return runInstallClaude(cmd, repoRoot, opts)
	default:
		return fmt.Errorf("unknown agent %q (valid: codex, claude)", agent)
	}
}

func runInstallCodex(cmd *cobra.Command, repoRoot string, skills []string, opts installOptions) error {
	results, err := agentinstall.Codex(repoRoot, agentinstall.CodexOptions{
		Scope:  opts.scope,
		Dest:   opts.dest,
		Skills: skills,
		Copy:   opts.copy,
		Force:  opts.force,
		DryRun: opts.dryRun,
	})
	if err != nil {
		return err
	}
	if flagQuiet {
		return nil
	}
	for _, result := range results {
		_, _ = fmt.Fprintf(cmd.OutOrStdout(), "%s codex skill %s -> %s\n", result.Action, result.Name, result.Dest)
	}
	if !opts.dryRun {
		_, _ = fmt.Fprintln(cmd.OutOrStdout(), "restart Codex to pick up newly installed skills")
	}
	return nil
}

func runInstallClaude(cmd *cobra.Command, repoRoot string, opts installOptions) error {
	if opts.dest != "" || opts.copy || opts.force {
		return fmt.Errorf("--dest, --copy, and --force only apply to codex installs")
	}
	switch opts.scope {
	case "user", "project", "local":
	default:
		return fmt.Errorf("invalid claude scope %q (valid: user, project, local)", opts.scope)
	}

	pluginName, marketplaceName, err := claudePluginSpec(repoRoot)
	if err != nil {
		return err
	}
	spec := pluginName + "@" + marketplaceName

	if opts.dryRun {
		_, _ = fmt.Fprintf(cmd.OutOrStdout(), "would run: vd build claude\n")
		_, _ = fmt.Fprintf(cmd.OutOrStdout(), "would run: claude plugin marketplace add --scope %s %s\n", opts.scope, repoRoot)
		_, _ = fmt.Fprintf(cmd.OutOrStdout(), "would run: claude plugin install --scope %s %s\n", opts.scope, spec)
		return nil
	}

	if err := runBuild(cmd, repoRoot, []string{"claude"}); err != nil {
		return err
	}
	if _, err := exec.LookPath("claude"); err != nil {
		return fmt.Errorf("claude command not found in PATH")
	}

	if err := runExternal(cmd, "claude", "plugin", "marketplace", "add", "--scope", opts.scope, repoRoot); err != nil {
		return err
	}
	if err := runExternal(cmd, "claude", "plugin", "install", "--scope", opts.scope, spec); err != nil {
		return err
	}
	if !flagQuiet {
		_, _ = fmt.Fprintf(cmd.OutOrStdout(), "installed Claude Code plugin %s\n", spec)
		_, _ = fmt.Fprintln(cmd.OutOrStdout(), "restart Claude Code to pick up plugin changes")
	}
	return nil
}

func claudePluginSpec(repoRoot string) (pluginName, marketplaceName string, err error) {
	manifestPath := filepath.Join(repoRoot, "skills.toml")
	manifest, err := config.Load(manifestPath)
	if err != nil {
		return "", "", fmt.Errorf("load skills.toml: %w", err)
	}
	config.ApplyDefaults(manifest, filepath.Join(repoRoot, ".claude-plugin", "marketplace.json"))
	pluginName = manifest.Targets.Claude.Bundle.Name
	marketplaceName = manifest.Meta.Name
	if pluginName == "" {
		return "", "", fmt.Errorf("missing [targets.claude.bundle].name")
	}
	if marketplaceName == "" {
		return "", "", fmt.Errorf("missing [meta].name")
	}
	return pluginName, marketplaceName, nil
}

func runExternal(cmd *cobra.Command, name string, args ...string) error {
	ext := exec.Command(name, args...)
	ext.Stdout = cmd.OutOrStdout()
	ext.Stderr = cmd.ErrOrStderr()
	ext.Stdin = cmd.InOrStdin()
	if err := ext.Run(); err != nil {
		return fmt.Errorf("%s %s: %w", name, strings.Join(args, " "), err)
	}
	return nil
}

func isKnownInstallAgent(s string) bool {
	switch normalizeInstallAgent(s) {
	case "codex", "claude":
		return true
	default:
		return false
	}
}

func normalizeInstallAgent(s string) string {
	switch strings.ToLower(s) {
	case "codex":
		return "codex"
	case "claude", "claude-code", "claudecode":
		return "claude"
	default:
		return strings.ToLower(s)
	}
}

func promptInstallSelection(cmd *cobra.Command, opts installOptions) (string, installOptions, error) {
	in := cmd.InOrStdin()
	file, ok := in.(*os.File)
	if !ok {
		return "", opts, fmt.Errorf("agent argument required when stdin is not interactive")
	}
	info, err := file.Stat()
	if err != nil {
		return "", opts, fmt.Errorf("inspect stdin: %w", err)
	}
	if info.Mode()&os.ModeCharDevice == 0 {
		return "", opts, fmt.Errorf("agent argument required when stdin is not interactive")
	}

	out := cmd.OutOrStdout()
	_, _ = fmt.Fprintln(out, "Install skills for:")
	_, _ = fmt.Fprintln(out, "  1) Codex user skills       symlink to $HOME/.agents/skills")
	_, _ = fmt.Fprintln(out, "  2) Codex repo skills       symlink to .agents/skills")
	_, _ = fmt.Fprintln(out, "  3) Codex snapshot copy     copy to $HOME/.agents/skills")
	_, _ = fmt.Fprintln(out, "  4) Claude Code plugin      marketplace/plugin install")
	_, _ = fmt.Fprint(out, "Select install target [1-4]: ")

	reader := bufio.NewReader(in)
	text, err := reader.ReadString('\n')
	if err != nil {
		return "", opts, fmt.Errorf("read selection: %w", err)
	}
	agent, opts, err := resolveInstallSelection(text, opts)
	if err != nil {
		return "", opts, err
	}
	return agent, opts, nil
}

func resolveInstallSelection(selection string, opts installOptions) (string, installOptions, error) {
	switch normalizeInstallSelection(selection) {
	case "codex-user":
		opts.scope = "user"
		opts.copy = false
		return "codex", opts, nil
	case "codex-repo":
		opts.scope = "repo"
		opts.copy = false
		return "codex", opts, nil
	case "codex-copy":
		opts.scope = "user"
		opts.copy = true
		return "codex", opts, nil
	case "claude":
		return "claude", opts, nil
	default:
		return "", opts, fmt.Errorf("invalid selection %q", strings.TrimSpace(selection))
	}
}

func normalizeInstallSelection(selection string) string {
	s := strings.ToLower(strings.TrimSpace(selection))
	s = strings.ReplaceAll(s, "_", "-")
	s = strings.Join(strings.Fields(s), "-")
	switch s {
	case "1", "codex", "codex-user", "codex-user-skills", "user":
		return "codex-user"
	case "2", "codex-repo", "codex-repo-skills", "repo":
		return "codex-repo"
	case "3", "codex-copy", "codex-snapshot", "codex-snapshot-copy", "copy", "snapshot":
		return "codex-copy"
	case "4", "claude", "claude-code", "claudecode":
		return "claude"
	default:
		return s
	}
}
