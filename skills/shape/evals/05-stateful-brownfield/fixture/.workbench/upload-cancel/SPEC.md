---
depends_on: []
id: upload-cancel
type: bug-fix
lenses: [statechart]
intent: "Cancelling an upload stops it for good, so a cancelled file is never sent."
---
# Cancelled uploads come back

Support reports that a file the user cancelled still arrived. The upload code is `src/upload.js`: it retries a failed send after a short wait, up to three tries, and the user can cancel while it uploads or waits. The rule from the ask: once cancelled, an upload never sends again.

## Mini-requirements

1. TODO

## Proof contract

- [ ] TODO
