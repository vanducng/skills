# Makefile for tools/vd — run targets from this directory.
# Usage: make build | make test | make vet | make lint | make run

# Use mise-managed Go if available; callers can still override: GO=/path/to/go make build
GO      ?= $(shell mise which go 2>/dev/null || command -v go)
VERSION ?= dev
BINARY  := vd
LDFLAGS := -ldflags "-X github.com/vanducng/skills/tools/vd/internal/version.Version=$(VERSION)"

.PHONY: build test vet lint run clean

build:
	$(GO) build $(LDFLAGS) -o $(BINARY) ./cmd/vd

test:
	$(GO) test ./...

vet:
	$(GO) vet ./...

lint:
	@if command -v golangci-lint >/dev/null 2>&1; then \
		golangci-lint run; \
	else \
		echo "golangci-lint not found — skipping (install from https://golangci-lint.run/usage/install/)"; \
	fi

run:
	$(GO) run $(LDFLAGS) ./cmd/vd $(ARGS)

clean:
	rm -f $(BINARY)
