# Sequencing the build

When the work needs more than one sitting, write the order into the record's `PROGRESS.md` under `## Plan`, not into new files.

- **Order by dependency, not by layer.** "Backend, then frontend" splits by domain; split by what unblocks the next step.
- **The first step ships something small and real.** One setup step at most.
- **The last step is integration**: the system works end to end against the proof contract.
- **One concern per step**, about five files, one sitting. An "and" in a step's title means split it.
- **Pick a slicing strategy:**
  - vertical (the default): each step is one complete path through the stack;
  - contract-first: freeze the shared interface first, so later steps can run in parallel;
  - risk-first: take the riskiest unknown first, so a dead end is found cheaply.
- Each step names its files, its test, and the contract item it moves.
