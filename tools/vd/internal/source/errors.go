package source

import "errors"

// Sentinel errors for use with errors.Is.
var (
	// ErrGitMissing is returned when git is not found in PATH or is too old.
	ErrGitMissing = errors.New("git not found or version too old")

	// ErrAuthRequired is returned when git reports an authentication failure.
	ErrAuthRequired = errors.New("git authentication required")

	// ErrRefNotFound is returned when the requested branch/tag/SHA does not exist.
	ErrRefNotFound = errors.New("git ref not found")

	// ErrUnknownSource is returned when a source name is not registered in the manifest.
	ErrUnknownSource = errors.New("unknown source")
)
