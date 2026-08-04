# Stack: <name>

Blank skeleton. Copy this file, rename it, fill every row.

## How to add a stack

1. Copy this file to `references/stacks/<kebab-name>.md`.
2. Fill the detection block: what marks the stack, its manifests and lockfiles, and which first-party
   source files make it code-bearing (§ Stack detection in `../signals.md` defines code-bearing).
3. Fill **all 13 rows** below. A signal that does not apply to the ecosystem still keeps its row and
   states the ecosystem-specific verdict rule instead. A missing row is a matrix hole, and a matrix hole
   is what makes a signal silently unscored.
4. Register the file in the stack index table in `../signals.md` § Stack detection.

Nothing else changes: the signal list, the scopes, the skip conditions, and the `Fix:` classifications all
stay in `../signals.md`. A stack file only supplies evidence.

## Detection

| Field | Value |
|---|---|
| Detect by | `<manifest or extension marker>` |
| Manifests / lockfiles | `<files>` |
| First-party sources | `<extensions>` |
| Notes | `<ecosystem quirks that change how evidence is read>` |

## Stack-heavy signals (all 13, one row each)

| signal_id | Evidence (PASS if any one) | Notes |
|---|---|---|
| test_command_declared | | |
| test_command_runnable | | |
| lint_configured | | |
| format_check_available | | |
| static_analysis_configured | | |
| coverage_threshold_enforced | | |
| dependencies_locked | | |
| runtime_version_pinned | | |
| module_boundaries_enforced | | |
| dead_code_detection | | |
| duplicate_code_detection | | |
| file_size_or_complexity_guard | | |
| naming_conventions_stated | | |

## Supplementary detail for universal signals

Optional. These signals are defined in full in `../signals.md`; the rows below only name the
ecosystem-specific API, key set, or tool the universal clause refers to. No row here is required.

| signal_id | Per-stack detail |
|---|---|
| env_vars_documented | `<env-access API>` |
| service_dependencies_documented | `<driver extractor keys, if the framework is in the extractor table>` |
| tech_debt_markers_tracked | `<marker lint rule and its limits, if the ecosystem has one>` |
