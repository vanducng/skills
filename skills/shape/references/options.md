# --options: two or three approaches, then a pick

Use it when the path is not obvious. Write the result to the record's `reports/options.md`.

1. **Ground:** read every system the change touches (the code, the record, the callers) before any option. List what you read at the top of the report; an option written without it is a guess.
2. **Frame:** the decision in one sentence, the constraints that bind it, and how success is measured.
3. **Design it twice:** two candidates that differ in structure (who owns the data, where the boundary sits), not in naming or brand. Add a third only if it breaks an assumption the first two share: build versus buy, no new service, do nothing. Name the lens behind each: inversion, constraint removal, simplification, or 10x scale.
4. **Screen each** against `references/red-flags.md`, assuming the next contributor is an agent that sees one file and none of this discussion. A candidate with a red flag is fixed or dropped, and the report says which.
5. **Stress-test each:** a one-line pitch, how it works, one scenario where it fails here, the hidden cost (operations, lock-in, on-call), and the cost of undoing it in a year.
6. **Prefer the deeper interface:** the candidate with a small surface hiding more behaviour wins a tie over one that exposes its parts.
7. **Scrap the sketch** when the same workaround appears twice in a candidate (a special case, a flag, a retry). The repeat means the shape is wrong: start that candidate again from the framing.
8. **Pick one.** Write `Pick: Option X` and one paragraph on why, grounded in the constraints. Then `Runner-up: Option Y, if <condition>`. If a missing constraint blocks the pick, ask that one question instead of writing "it depends".

Shape of `reports/options.md`:

```
# Options: <decision>
Read: <the systems and files grounded on>
## Option A - <name>
## Option B - <name>   (a different structure from A)
## Option C - <name>   (optional)
Red flags: <per option: none, or the flag and the fix>
Pick: Option <X>. <why>
Runner-up: Option <Y>, if <condition>.
```

The pick feeds the default mode: the mini-requirements and the contract follow from it.
