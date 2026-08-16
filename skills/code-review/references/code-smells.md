# Code smells baseline (Standards axis)

The fixed vocabulary for the Standards pass - Fowler's catalog, trimmed to the twelve that show up in real diffs. Each entry: what it is → how to fix. Flag a smell only when the fix is worth the author's time; "different from how I'd write it" is not a smell.

| Smell | What it is | How to fix |
|---|---|---|
| **Duplicated code** | The same logic in two+ places (or new code re-deriving something the codebase ships) | Extract Function / import the existing one. Cite the existing `path:line` |
| **Long function** | One function doing several jobs at several abstraction levels | Extract Function along the comment boundaries; each piece one job |
| **Long parameter list** | 4+ positional params, booleans steering behavior | Introduce Parameter Object; split the boolean-switched paths |
| **Feature envy** | A function that mostly reads/writes another module's data | Move Function to where the data lives |
| **Data clumps** | The same 3 fields traveling together through signatures | Extract them into a type/struct with a domain name |
| **Primitive obsession** | Domain concepts passed as bare strings/ints (`userId: string` everywhere) | Introduce a domain type at the boundary; validate once |
| **Shotgun surgery** | One logical change forces edits in many files | Move the pieces into one module; the diff itself is the evidence |
| **Divergent change** | One file edited for many unrelated reasons across commits | Split by reason-to-change (`git log` on the file is the evidence) |
| **Speculative generality** | Hooks, params, interfaces for futures nobody scheduled | Delete. YAGNI. An interface with one implementation defined at the producer is this smell in Go |
| **Message chains** | `a.b().c().d()` reaching through the object graph | Hide Delegate, or move the behavior to the end of the chain |
| **Comments as deodorant** | A comment explaining code that could be self-explanatory | Rename / extract until the comment is redundant, then delete it. Keep only *why* comments |
| **Mutable shared state** | Module-level mutables, singletons written from many places | Pass state explicitly; isolate mutation behind one owner |
