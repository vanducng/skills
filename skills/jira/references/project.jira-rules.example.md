# Jira rules: example

Copy this file to `~/.config/vd/jira-rules/<alias>.jira-rules.md`. Keep the local copy outside Git.

## Connection

- Base URL: `https://example.atlassian.net`
- Token environment variable: `JIRA_EXAMPLE_API_TOKEN`
- Email environment variable: `JIRA_EXAMPLE_USER_EMAIL`
- Environment file: `~/.envrc`
- Issue key prefixes: `EXAMPLE`
- Default board: `Example Board`

## Bug

- Assignee: me
- Sprint: current active sprint
- Parent: `EXAMPLE-1`
- Initial status: `In Development`

## Task

- Assignee: me
- Sprint: current active sprint
- Parent: `EXAMPLE-1`
- Initial status: `In Development`

## Ticket content

- Bare symptom and basic finding only.
- Include one short sample error when available.
- Attach provided evidence when available.
- Omit implementation details and speculative analysis.
