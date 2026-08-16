# Deep-module vocabulary

Shared design language for this catalog (adapted from Ousterhout's *A Philosophy of Software Design*). Other skills point here; use these terms exactly, and avoid the listed synonyms so the vocabulary stays load-bearing.

## The terms

- **Module** - any unit with an interface and an implementation: a function, class, package, service, or CLI. *Avoid: component, unit, service* (each drags in framework baggage).
- **Interface** - everything a caller must know to use the module: signatures, error semantics, ordering constraints, performance expectations. If a caller must know it, it's interface - documented or not (Hyrum's Law).
- **Implementation** - everything the module knows that callers don't have to.
- **Depth** - the ratio of hidden capability to exposed interface. A **deep module** does a lot behind a small, stable surface (e.g. a filesystem behind `open/read/write/close`). A **shallow module** exposes roughly as much as it hides - the interface costs as much to learn as the implementation would.

```
deep:                          shallow:
┌───────┐  small interface     ┌───────────────────────┐  wide interface
│  API  │                      │          API          │
├───────┤                      ├───────────────────────┤
│       │                      │  impl                 │  thin logic
│ impl  │  lots of capability  └───────────────────────┘
│       │
└───────┘
```

- **Seam** - a boundary where behavior is observable and substitutable; where tests attach (see `vd:tdd`) and where systems get swapped.
- **Adapter** - a module that translates between your domain and an external shape. **One adapter is a hypothetical seam; two is a real one** - don't build the abstraction until the second implementation exists.
- **Leverage** - how much behavior one interface decision moves. High-leverage decisions (error strategy, ID types, pagination shape) deserve design-time care; low-leverage ones don't.
- **Locality** - can a reader understand this module from this file alone? Every hop to another file to understand this one is a locality failure.

## Principles

- **The deletion test.** If deleting a module would force its logic to reappear elsewhere nearly verbatim, it earns its existence. If callers would just inline two lines, it was a shallow wrapper - delete it.
- **The interface is the test surface.** Test what the interface promises, never how the implementation delivers it.
- **Design it twice.** For any non-trivial surface, sketch two genuinely different interface shapes before committing (different boundary, different granularity, different error model). The second design is cheap; being locked into the first idea is not. `vd:brainstorm` is the heavyweight version of this; two sketches in a reply is the lightweight one.
- **Pull complexity downward.** Given the choice, make the implementation more complex so the interface can be simpler - the module is written once and used many times.
