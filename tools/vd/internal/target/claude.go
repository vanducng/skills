package target

import "fmt"

// claudeEmitter dispatches to bundle or per-skill mode based on manifest config.
type claudeEmitter struct{}

func (e *claudeEmitter) Name() string { return "claude" }

func (e *claudeEmitter) Emit(ctx Context) error {
	mode := ctx.Manifest.Targets.Claude.Mode
	if mode == "" {
		mode = "bundle"
	}

	switch mode {
	case "bundle":
		return (&bundleEmitter{}).emit(ctx)
	case "per-skill":
		return (&perSkillEmitter{}).emit(ctx)
	default:
		return fmt.Errorf("claude emitter: unknown mode %q (valid: bundle, per-skill)", mode)
	}
}
