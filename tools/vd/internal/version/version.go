package version

// Version is injected at build time via -ldflags "-X .../version.Version=<tag>".
// Falls back to "dev" for local builds.
var Version = "dev"
