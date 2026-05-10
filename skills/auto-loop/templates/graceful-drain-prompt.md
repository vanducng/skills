Budget cap reached: {REASON}.

# Goal
{GOAL}

# Context
iterations completed: {ITERATION}
last status: {STATUS}
elapsed: {ELAPSED}
tokens used: {TOKENS_USED}

# This is your final iteration
Do NOT start new work. Do these in order:

1. Commit any uncommitted progress with message:
   `git commit -am "wip(auto-loop): graceful drain at cap {REASON}"`
   (skip if there's nothing to commit).

2. Update `.auto-loop/goal-state.json` with:
   - status: `budget-limited`
   - next_action: short summary of where the loop stopped
   - evidence[]: bullet points of what was achieved (≤ 20 entries)
   - blockers[]: what still needs doing for the goal to be met

3. Exit. Do not modify any other files.

The loop will end after this iteration whether or not you complete steps above.
