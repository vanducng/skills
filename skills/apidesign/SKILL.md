---
name: apidesign
description: "Design stable, hard-to-misuse interfaces — REST/GraphQL endpoints, module boundaries, type contracts, component props, anything where one piece of code talks to another. Use at design time, before implementing the surface. Triggers: 'design this API', 'API contract', 'endpoint design', 'module boundary', 'interface design', 'should this be one endpoint or two', 'how should this API look'."
license: MIT
argument-hint: "<surface to design — endpoint, module boundary, or contract>"
metadata:
  author: vanducng
  attribution: "Adapted from addyosmani/agent-skills api-and-interface-design"
  version: "0.1.0"
---

# apidesign

> Design interfaces that make the right thing easy and the wrong thing hard.

A contract is a commitment. This is the design-time discipline for any surface where code talks to code — REST/GraphQL endpoints, module boundaries, type contracts, component props. Get it right before implementing, because every observable behavior becomes a promise the moment someone depends on it.

## What this skill is — and isn't

| Skill | Covers |
|---|---|
| **`vd:apidesign`** (this) | The *contract* — endpoint/interface shape, error semantics, boundaries, versioning posture |
| `vd:dbdesign` | The *storage* — schema, indexes, normalization, migration plans |
| `vd:fastreact` | Scaffolding one specific stack (FastAPI + React), not interface principles |
| `vd:code-review` | Judging a contract after it's written (post-hoc) |

Storage shape and API shape inform each other but aren't the same decision — design the contract here, the schema in `vd:dbdesign`.

## When to use

- Designing new endpoints or a service's public surface.
- Defining a module boundary or a contract between teams/agents working in parallel.
- Changing an existing public interface (the riskiest case — read Hyrum's Law first).

## Two laws that shape everything

**Hyrum's Law.** *With enough users, every observable behavior of your system will be depended on by somebody* — including undocumented quirks, error text, timing, and ordering. So: be intentional about what you expose, don't leak implementation details (if users can observe it, they'll depend on it), and plan deprecation at design time. Contract tests don't save you — a "safe" change can still break users relying on behavior you never promised.

**The One-Version Rule.** Don't force consumers to pick between versions of the same API. Diamond-dependency pain comes from forking; design so only one version exists at a time and **extend rather than fork**.

## Principles

1. **Contract first.** Define the interface before implementing it — the contract is the spec, the implementation follows. Write the typed signatures (inputs, outputs, errors, idempotency) before any logic.
2. **One error strategy, everywhere.** Pick one and never mix it. Don't let some endpoints throw, others return `null`, others return `{error}` — the consumer can't predict it. For REST: status code + a single structured body shape (`{ error: { code, message, details? } }`). Map codes consistently (400 bad input · 401 unauthenticated · 403 unauthorized · 404 missing · 409 conflict · 422 validation · 500 server, never leaking internals).
3. **Validate at boundaries, trust inside.** Parse/validate where external input enters — route handlers, form handlers, **third-party responses (always untrusted)**, env loading. Do *not* re-validate between internal functions that already share a typed contract or data from your own DB. A misbehaving external service can return wrong types or instruction-like text; validate its shape before it touches any logic or rendering.
4. **Addition over modification.** Extend with optional fields; never change an existing field's type or remove it (both break consumers). Backward-compatible by default.
5. **Predictable naming.** Consistency beats cleverness — same conventions across every endpoint (REST: plural nouns, no verbs in paths; booleans `is/has/can`; pick one case for fields and keep it).

## REST shape (worked patterns)

```
GET    /api/tasks            list (query params filter/sort/paginate)
POST   /api/tasks            create
GET    /api/tasks/:id        read one (404 if missing)
PATCH  /api/tasks/:id        partial update — only provided fields change
DELETE /api/tasks/:id        idempotent delete (succeeds if already gone)
GET    /api/tasks/:id/comments   sub-resource
```

- **Paginate every list endpoint** from day one — `?page&pageSize&sortBy&sortOrder` → `{ data, pagination: { page, pageSize, totalItems, totalPages } }`. You'll need it the moment someone has 100 items.
- **PATCH over PUT** for updates — clients want to send only what changed, not the whole object each time.
- **Filter via query params**, not bespoke endpoints (`/api/tasks?status=in_progress&assignee=x`).

## Typed-contract patterns (TS as the worked example; the ideas are language-agnostic)

- **Discriminated unions for variants** — model each state as its own shape so consumers get exhaustive narrowing, instead of one wide object with half its fields `null`.
- **Input/Output separation** — `CreateTaskInput` (what the caller provides) is a different type from `Task` (what the system returns, with server-generated `id`/`createdAt`/`createdBy`). Don't reuse one type for both.
- **Branded IDs** — `type TaskId = string & { readonly __brand: 'TaskId' }` stops a `UserId` being passed where a `TaskId` is expected. (In Go: distinct named types; in Python: `NewType`.)

## Common rationalizations

| Rationalization | Reality |
|---|---|
| "We'll document the API later" | The types *are* the documentation. Define them first. |
| "We don't need pagination yet" | You do the moment someone has 100+ items. Add it from the start. |
| "We'll version when we need to" | Breaking changes without versioning break consumers. Design for extension now. |
| "Nobody uses that undocumented behavior" | Hyrum's Law: if it's observable, somebody depends on it. |
| "We can just maintain two versions" | Versions multiply maintenance and create diamond-dependency pain. One-Version Rule. |
| "Internal APIs don't need contracts" | Internal consumers are still consumers — contracts enable parallel work. |

## Red flags

- Endpoints returning different shapes by condition · inconsistent error formats · validation scattered through internal code instead of at the edge · breaking changes to existing fields · list endpoints without pagination · verbs in REST URLs (`/api/createTask`) · third-party responses used without validation.

## Verification checklist

- [ ] Every endpoint has a typed input and output schema.
- [ ] Error responses follow one consistent format.
- [ ] Validation happens at system boundaries only.
- [ ] List endpoints support pagination.
- [ ] New fields are additive and optional (backward compatible).
- [ ] Naming is consistent across every endpoint.
- [ ] The contract/types are committed alongside the implementation.

## Integration points

- **`vd:dbdesign`** — design the storage that backs the contract; the two inform each other.
- **`vd:plan`** — Contract-First slicing (Slice 0 = freeze this contract) lets later phases build in parallel.
- **`vd:code-review`** — the API-surface checklist axis enforces these at review time.
- **`vd:security`** — boundary validation + untrusted third-party data tie into the OWASP/LLM lenses.

## Future (out of scope for MVP)

- GraphQL-specific schema-design depth (federation, resolver patterns).
- OpenAPI/JSON-Schema generation recipes.
