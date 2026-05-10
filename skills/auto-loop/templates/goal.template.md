# Goal
All bats tests in tests/ pass and ruff lint is clean across the repo.

# Verify
verify: `bats tests/ && ruff check .`

# Scope
allow: src/**/*.py, tests/**/*.bats
deny: .env, secrets/**, .auto-loop/**

# Caps
max_iterations: 30
max_tokens: 1_500_000
max_wallclock: 2h
restart_at_context_pct: 70
max_restarts: 5
