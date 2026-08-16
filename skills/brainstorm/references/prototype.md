# Prototype detour - answer a design question by building

Some questions in Phase 2/3 cannot be answered by argument: "is this API ergonomic?", "is this fast enough?", "does this library actually support X?". When an option's viability hinges on such a question, take a prototype detour instead of speculating.

## Rules

1. **The question decides the shape.** Build the smallest thing that answers the specific question - a script, a spike endpoint, a single throwaway page. Nothing more.
2. **Throwaway and marked as such.** Put it on a `prototype/{slug}` branch (or a scratch dir outside `src/`), with a README line stating the question it answers. Never merge it.
3. **Trivial to run.** One command. No persistence, no auth, no config - hardcode everything that isn't the question.
4. **Skip polish entirely.** No error handling, no tests, no naming care. Polish on a prototype is waste.
5. **Surface the answer, not the code.** Report back into the brainstorm: "Prototype answers Q: yes/no/number - because {evidence}." The measurement or observation goes into the option's Phase 3 row.
6. **Keep it as a primary source.** Reference the branch/dir in the decision brief so the plan phase can consult it. Prototype-derived snippets are the one exception to the brief's no-code rule.

## When not to detour

If the question is answerable by reading docs, code, or benchmarks that already exist - that's a fact lookup (see `grilling.md`), not a prototype. Prototype only when the environment cannot tell you and the answer changes the recommendation.
