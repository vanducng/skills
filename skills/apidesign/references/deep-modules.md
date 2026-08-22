# Deep modules

A **deep module** has a small interface and a large body of responsibility. A **shallow module** has an interface that is not much simpler than the implementation - the caller still has to know the insides.

Use this vocabulary at design time. Banned near-synonyms in this skill: "thin wrapper" as praise, "god object" as the only opposite (a god object is wide *and* deep; shallowness is the usual API failure).

## Rules

1. **Push complexity down.** The caller should say *what*, not *how*. If every consumer repeats the same three setup calls, that sequence belongs inside the module.
2. **Do not split for file-size.** Two shallow files that leak the same invariants are worse than one deep module.
3. **Interface changes are the expensive ones.** Adding a helper behind a stable function is cheap. Adding a required parameter is not.
4. **One error strategy leaks less.** A module that sometimes throws, sometimes returns null, and sometimes returns `{error}` is shallow: the caller must learn the implementation.
5. **Test the interface, not the guts.** If tests cannot be written against the public surface, the module is not deep enough (or the surface is wrong).

## When to go shallow on purpose

Adapters at the edge (HTTP handlers, DB drivers, CLI flags) stay shallow so the deep module does not import the world. Say so in the design: "shallow adapter, deep core."
