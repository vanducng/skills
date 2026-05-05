package target

import "fmt"

// NewEmitter returns the Emitter for the given target name.
// Known names: "claude", "agents".
func NewEmitter(name string) (Emitter, error) {
	switch name {
	case "claude":
		return &claudeEmitter{}, nil
	case "agents":
		return &agentsEmitter{}, nil
	default:
		return nil, fmt.Errorf("unknown emitter %q: valid names are claude, agents", name)
	}
}
