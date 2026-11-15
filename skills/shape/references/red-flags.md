# Red flags for a candidate design

Screen each `--options` candidate against these. The reader is the next contributor: an agent that opens one file, reads it and edits it. A design that needs the whole system in its head fails this screen.

| Flag | What it looks like | Fix |
|---|---|---|
| Shallow module | The interface is as big as the code behind it; callers must know the steps | Merge the steps behind one call |
| Leaked detail | A caller must know an order, a format or a flag the module could own | Move it inside |
| Pass-through | A layer only forwards its arguments | Delete the layer |
| Special case | An `if` for one customer, host or input kind | Change the model so the case is not special |
| Repeated workaround | The same patch appears a second time | Scrap the sketch and reframe (options.md step 7) |
| Spread change | One rule change touches many files | Give the rule one home |
| Hidden coupling | Two files must change together and nothing says so | Put them in one file or make the link explicit |
| Needs a map | A new contributor cannot place the change from one file | Name and co-locate the parts |

## Worked example: where to retry failed webhook sends

Grounded on: `send.py` (callers: 3), `config.yaml`, the record's SPEC.

- **A, retry inside `send()`:** one call; the backoff and the give-up rule live in `send.py`. Flags: none; the interface stays one function.
- **B, a separate `Retrier` the callers wrap around `send()`:** each caller loops, waits and gives up. Flags: shallow module (callers know the steps), spread change (three callers edit on any backoff change).

`Red flags: A none; B shallow module, spread change (fix would be to fold it into send(), which is A).`
`Pick: Option A.` Deeper interface, one home for the retry rule.

## Credit

The design-twice and red-flag steps adapt the architect pass of the pstack plugin, https://github.com/cursor/plugins/tree/main/pstack/skills/architect (MIT, Copyright (c) 2026 Lauren Tan), as `statechart` adapts its statechart skill. The list and the example here are rewritten for this repository.
