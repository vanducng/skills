# Stack: Python

Evidence only. Scope, skippability, skip conditions, floor rules, and the `Fix:` classification for every
signal below live in `../signals.md`; this file says what counts as evidence in this ecosystem. Each row is
additive to that signal's catch-all clause - a stack row never overrides the catch-all, and a signal passes
for the app when any one clause (this file's or the catch-all's) holds.

## Detection

| Field | Value |
|---|---|
| Detect by | `pyproject.toml`, `setup.py`, `requirements*.txt` |
| Manifests / lockfiles | `pyproject.toml`, `poetry.lock`, `uv.lock`, `Pipfile.lock` |
| First-party sources | `.py`, `.pyi` |
| Notes | A `pyproject.toml` holding only tool config for a non-Python app is **not** code-bearing and does not participate in the multi-stack ALL rule. |

## Stack-heavy signals (all 13, one row each)

| signal_id | Evidence (PASS if any one) | Notes |
|---|---|---|
| test_command_declared | `pytest`/`tox`/`nox` config in `pyproject.toml`, `pytest.ini`, `tox.ini`, or `noxfile.py` | |
| test_command_runnable | `pytest --collect-only -q` | Collection-only, never the full suite. Fail on a collection error |
| lint_configured | `[tool.ruff]`, `.flake8`, `setup.cfg` `[flake8]`, or `.pylintrc` | |
| format_check_available | black/ruff/isort as a declared dependency plus a declared `black --check`, `ruff format --check`, or `isort --check-only` command | Both halves required: resolved formatter and a non-mutating check command. Config presence alone fails |
| static_analysis_configured | `[tool.mypy]`, `mypy.ini`, or `[tool.pyright]` with a documented run command | A type-stub directory is data, not an analysis run |
| coverage_threshold_enforced | `[tool.coverage.report] fail_under = N`, or `--cov-fail-under=N` in the pytest addopts | Subject to the floor rule in `../signals.md`: a committed `0`, or any value at or below 1 percent, fails |
| dependencies_locked | `poetry.lock`, `uv.lock`, `Pipfile.lock`, or a fully pinned `requirements.txt` (every line `==`) | A gitignored lockfile fails even when present locally |
| runtime_version_pinned | `.python-version`, `.tool-versions`, or `mise.toml`; or an immutable image reference (digest or exact tag such as `python:3.12.6-slim`) | `requires-python` is a compatibility range and does **not** pin |
| module_boundaries_enforced | `import-linter` contracts, or ruff `flake8-tidy-imports` banned-api rules | Documentation alone never passes this signal |
| dead_code_detection | `vulture` config, or ruff `F401`/`ERA` rules enabled | |
| duplicate_code_detection | `pylint` duplicate-code checker enabled with a threshold | A committed `.codeclimate.yml`/`sonar-project.properties` with duplication rules on also passes (universal clause) |
| file_size_or_complexity_guard | ruff `C901`/`PLR0915`, or flake8 `max-complexity` | |
| naming_conventions_stated | Automated: ruff `N` rules | Otherwise the documentation clause in `../signals.md` (3 of 4 categories) decides it |

## Supplementary detail for universal signals

| signal_id | Per-stack detail |
|---|---|
| env_vars_documented | Env-access API: `os.environ[...]`, `os.getenv`. Pydantic settings satisfy the typed-config clause |
| service_dependencies_documented | Driver extractor (Django row): `settings*.py` `DATABASES[*]['ENGINE']`, `CACHES[*]['BACKEND']`, `EMAIL_BACKEND`, `CELERY_BROKER_URL`, `STORAGES`/`DEFAULT_FILE_STORAGE` |
| tech_debt_markers_tracked | ruff `TD002`/`TD003` (missing author, missing issue link) satisfy an owner-or-link policy |
