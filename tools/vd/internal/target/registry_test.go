package target

import "testing"

func TestNewEmitter_KnownNames(t *testing.T) {
	for _, name := range []string{"claude", "agents"} {
		e, err := NewEmitter(name)
		if err != nil {
			t.Errorf("NewEmitter(%q): unexpected error: %v", name, err)
			continue
		}
		if e == nil {
			t.Errorf("NewEmitter(%q): returned nil emitter", name)
			continue
		}
		if e.Name() != name {
			t.Errorf("NewEmitter(%q).Name() = %q, want %q", name, e.Name(), name)
		}
	}
}

func TestNewEmitter_UnknownName(t *testing.T) {
	_, err := NewEmitter("bogus")
	if err == nil {
		t.Error("NewEmitter(\"bogus\"): expected error, got nil")
	}
}
