# Prototype tickets - answer a decision by building

Use a prototype ticket when the question cannot be answered from docs, code, or a grilling conversation: "is this API ergonomic?", "is it fast enough?", "does this library actually support X?", "how should this look?".

## Rules

1. **The ticket's Question decides the shape.** Build the smallest thing that answers it - a script, a spike endpoint, a single throwaway page. Nothing more.
2. **Throwaway and marked as such.** Put it on a `prototype/{slug}` branch (or a scratch dir outside `src/`), with a README line stating the question it answers. Never merge it.
3. **Trivial to run.** One command. No persistence, no auth, no config - hardcode everything that isn't the question.
4. **Skip polish entirely.** No error handling, no tests, no naming care. Polish on a prototype is waste.
5. **Surface the answer, not the code.** Post the measurement on the ticket: "Prototype answers Q: yes/no/number - because {evidence}." Link the branch or artifact. Then close the ticket.
6. **Keep it as a primary source.** The map's Decisions-so-far line links the ticket; the later `vd:plan` may consult the artifact. Do not paste the spike into production.

## When not to prototype

- Answerable by reading docs, code, or existing benchmarks → `research` ticket (`vd:research`), not prototype.
- The question is a conversation ("what do we actually want?", "which tradeoff do you accept?") → `grilling` ticket (`vd:interview --grill`).
- The work is delivering the destination → you have left the map. Hand off to `vd:plan`.
