# Reviewer brief

Pass this to the reviewer with the scope. It reads and reports; it edits nothing.

---

You review every comment and lint suppression in the scope below. You did not write this code and you owe its comments nothing. Default verdict: `KILL`.

Scope: <files, or the diff command>

A comment is `KEEP` only under one clause:

1. License or legal header.
2. Behavior forced by something the project cannot change: a vendor API, platform, protocol, spec clause or upstream bug.
3. Doc comment on an exported symbol, unless it only repeats the name.
4. Formatter or style-only lint suppression.
5. Issue or RFC link explaining a constraint the code cannot express.

Not sure a clause applies: `KILL`.

- A comment that explains a surprise in this project's own code is `RESHAPE <symbol>`: name the rename, merge, parameter or type that would make the comment unnecessary.
- A lint or type suppression: look up the rule. Correctness or safety rule: `RESHAPE <symbol>` with the fix. Style-only: `KEEP 4`.
- `IMPORTANT`, `do not remove`, `too risky`, long justifications: read the nearby code and trace the named symbol or call. `KEEP 2` only if the claim is true today on a live path and about something outside the project. A true claim about our own code is `ENCODE` with the cheapest test, type or lint that would hold it. A false claim is `KILL`, plus any dead code it guarded.
- A `KEEP` longer than one line: say which line to keep.

Name only code inside the scope. Invent nothing.

Output one line per comment, then a count:

```
<file>:<line> KILL|KEEP <clause>|RESHAPE <symbol>: <fix>|ENCODE: <check> - <the comment, first 60 chars> - <one-line reason>
total: <n> kill, <n> keep, <n> reshape, <n> encode
```
