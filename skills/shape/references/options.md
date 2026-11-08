# --options: two or three approaches, then a pick

Use it when the path is not obvious. Write the result to the record's `reports/options.md`.

1. **Frame:** the decision in one sentence, the constraints that bind it, and how success is measured.
2. **Diverge:** two or three options that are really different. The third breaks an assumption the first two share: build versus buy, no new service, do nothing. Three database brands are one option, not three. Name the lens behind each: inversion, constraint removal, simplification, or 10x scale.
3. **Stress-test each:** a one-line pitch, how it works, one scenario where it fails here, the hidden cost (operations, lock-in, on-call), and the cost of undoing it in a year.
4. **Pick one.** Write `Pick: Option X` and one paragraph on why, grounded in the constraints. Then `Runner-up: Option Y, if <condition>`. If a missing constraint blocks the pick, ask that one question instead of writing "it depends".

Shape of `reports/options.md`:

```
# Options: <decision>
## Option A - <name>
## Option B - <name>
## Option C - <name>   (optional)
Pick: Option <X>. <why>
Runner-up: Option <Y>, if <condition>.
```

The pick feeds the default mode: the mini-requirements and the contract follow from it.
