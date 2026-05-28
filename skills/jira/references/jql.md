# JQL (Jira Query Language) Reference

## Basic Syntax

```
field operator value [AND|OR field operator value]
```

## Common Fields

| Field | Description | Example |
|---|---|---|
| `project` | Project key | `project = "PROJ"` |
| `issuetype` | Issue type | `issuetype = Bug` |
| `status` | Issue status | `status = "In Progress"` |
| `assignee` | Assigned user | `assignee = currentUser()` |
| `reporter` | Issue creator | `reporter = "user"` |
| `priority` | Priority level | `priority = High` |
| `labels` | Issue labels | `labels = "backend"` |
| `component` | Components | `component = "API"` |
| `created` | Creation date | `created >= -30d` |
| `updated` | Last update | `updated >= -7d` |
| `resolved` | Resolution date | `resolved >= startOfMonth()` |
| `sprint` | Sprint name/ID | `sprint in openSprints()` |
| `epic` | Parent epic | `"Epic Link" = PROJ-100` |
| `parent` | Parent issue | `parent = PROJ-50` |
| `text` | Full-text search | `text ~ "authentication"` |
| `summary` | Title search | `summary ~ "login"` |
| `description` | Desc search | `description ~ "OAuth"` |

## Operators

| Operator | Meaning | Example |
|---|---|---|
| `=` | Exact match | `status = Done` |
| `!=` | Not equal | `status != Closed` |
| `~` | Contains (text) | `summary ~ "auth*"` |
| `!~` | Does not contain | `summary !~ "test"` |
| `>` `>=` `<` `<=` | Comparisons | `priority >= High` |
| `IN` | Multiple values | `status IN (Open, "In Progress")` |
| `NOT IN` | Exclude values | `status NOT IN (Done, Closed)` |
| `IS` | Null check | `assignee IS EMPTY` |
| `IS NOT` | Not null | `assignee IS NOT EMPTY` |
| `WAS` | Historical value | `status WAS "In Progress"` |
| `CHANGED` | Field changed | `status CHANGED` |

## Functions

| Function | Description | Example |
|---|---|---|
| `currentUser()` | Logged-in user | `assignee = currentUser()` |
| `now()` | Current timestamp | `created <= now()` |
| `startOfDay()` | Midnight today | `updated >= startOfDay()` |
| `startOfWeek()` | Start of week | `created >= startOfWeek()` |
| `startOfMonth()` | Start of month | `created >= startOfMonth()` |
| `endOfDay()` | End of today | `due <= endOfDay()` |
| `openSprints()` | Active sprints | `sprint in openSprints()` |
| `closedSprints()` | Done sprints | `sprint in closedSprints()` |
| `linkedIssues()` | Linked issues | `issue in linkedIssues("PROJ-123")` |

## Relative Dates

```jql
created >= -7d     # Last 7 days
updated >= -30d    # Last 30 days
created >= -2w     # Last 2 weeks
created >= -1M     # Last month
created >= "2024-01-01"  # Specific date
```

## Ordering

```jql
project = PROJ ORDER BY priority DESC
project = PROJ ORDER BY status ASC, created DESC
```

## Complex Query Examples

```jql
# My open issues, high priority
assignee = currentUser() AND status NOT IN (Done, Closed) AND priority >= High

# Bugs created this week
issuetype = Bug AND created >= startOfWeek() ORDER BY priority DESC

# Unassigned high-priority bugs
issuetype = Bug AND assignee IS EMPTY AND priority >= High

# Sprint backlog items
sprint in openSprints() AND status = "To Do" ORDER BY rank ASC

# Issues linked to specific epic
"Epic Link" = PROJ-100 AND status != Done

# Recently resolved by team
resolved >= -7d AND project = PROJ ORDER BY resolved DESC

# Issues I'm watching
watcher = currentUser()

# Updated by me recently
updatedBy = currentUser() AND updated >= -7d ORDER BY updated DESC
```

## Using JQL with CLI

```bash
jira issue list -q"assignee = currentUser() AND status = 'In Progress'"
jira issue list -q"project = PROJ AND issuetype = Bug AND priority >= High"
```
