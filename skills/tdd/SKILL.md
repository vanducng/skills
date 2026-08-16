---
name: tdd
description: "Test-driven development discipline: what a good test is, where tests attach (pre-agreed seams), and the anti-patterns that make agent-written tests worthless. Use when writing tests before or alongside implementation, when the user says 'TDD' / 'test-first' / 'add tests for this', when cook runs with --tdd, or when fix needs a regression guard. Not a test runner - it shapes which tests get written."
license: MIT
argument-hint: "[feature, bug, or seam to test]"
metadata:
  author: vanducng
  version: "0.1.0"
---

# TDD

Testing discipline for this catalog. `vd:cook --tdd`, `vd:plan --tdd`, and `vd:fix`'s regression guard compose this skill; it can also run standalone when the user wants tests for existing code.

## What a good test is

A good test states a **behavioral contract**: given this input at this boundary, this observable result. It reads like a spec line, fails for exactly one reason, and survives a full rewrite of the implementation behind the boundary. If the implementation could be rewritten and the test would break anyway, the test asserts *how*, not *what* - delete or rewrite it.

## Seams: test only where it was agreed

A **seam** is a boundary where behavior is observable and substitutable: a module's public API, an HTTP endpoint, a CLI contract, a queue message shape. Tests attach at seams - not at private functions, not at internal call sequences.

- **Plans record seams.** `vd:plan` captures a `## Test Seams` section agreed with the user. Honor it: test at those seams, and only those.
- **No plan / no seams recorded?** Propose 1-3 seams to the user before writing any test ("I'll test at the `parseConfig` public API and the CLI exit codes - agreed?"). Writing tests at unagreed seams is how suites calcify around accidental structure.
- **One adapter is a hypothetical seam; two is a real one.** Don't invent seams (interfaces, DI wrappers) purely to make something testable that has only one real implementation - test through the boundary that already exists.

## Anti-patterns and their tells

| Anti-pattern | What it looks like | The tell |
|---|---|---|
| **Implementation-coupled** | Asserting on private state, call order, or mock interaction counts | Refactoring with identical behavior breaks the test |
| **Tautological** | Mocking the thing under test, then asserting the mock returned what it was told to | The test passes even when the real code is deleted |
| **Horizontal slicing** | One test file per layer (all controllers, then all services, then all repos) | No single test proves a user-visible behavior end-to-end |

When you catch yourself writing one, stop and re-anchor on the seam: what observable behavior at the boundary does this test protect?

Mocking rule of thumb: mock at seams you don't own (network, clock, filesystem, third-party APIs); use real code for everything you do own. A test suite that mocks its own modules tests the mocks.

## Rules of the loop

1. **Red before green.** Watch the new test fail before implementing - a test that never failed proves nothing. For bug fixes this is mandatory: the failing test *is* the reproduction.
2. **One vertical slice at a time.** Write the failing test for one behavior, make it pass, move on. Don't front-load a wall of failing tests.
3. **Refactoring belongs to review, not the green step.** Make it pass plainly; structural cleanup happens after, with the tests as the safety net (`vd:simplify` for anything beyond local tidying).
4. **Never edit a test to make it pass** unless the test was provably wrong - and document why in the commit.

## Done when

- Every agreed seam has at least one behavioral test that was seen red, then green.
- No test in the diff asserts on implementation details (walk the anti-pattern tells as a checklist).
- The suite passes fully - not just the new tests.

## Workflow position

**Composed by:** `vd:cook --tdd` (Step B opens with failing tests), `vd:fix` (regression guard), `vd:plan --tdd` (phases open with a Tests-first step)
**Compares to:** `vd:scenario` (enumerates *what* edge cases exist - feed its output into test selection here); cook's Step D (runs the suite - this skill shapes what's in it)
