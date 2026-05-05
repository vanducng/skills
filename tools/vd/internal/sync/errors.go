package sync

import "errors"

// ErrRefuseDirty is returned by Execute when one or more skills have local
// modifications that would be overwritten by a sync. Use --force to bypass.
var ErrRefuseDirty = errors.New("local modifications detected; use --force or 'vd detach <skill>'")

// IsRefuseDirty reports whether err (or any in its chain) is ErrRefuseDirty.
func IsRefuseDirty(err error) bool {
	return errors.Is(err, ErrRefuseDirty)
}
