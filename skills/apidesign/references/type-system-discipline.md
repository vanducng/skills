# Type system discipline (design-time)

The type checker is part of the contract. Use it so illegal combinations, mixed IDs, and unhandled variants fail at compile time, not in production. This is the typed-contract lens for `vd:apidesign`: freeze the model before you implement the surface.

TS and Go examples; ideas are language-agnostic.

## 1. Make illegal states unrepresentable

Do not encode variants as bool + nullable bags. Contradictory combos compile. Use tagged unions (TS) or a sum of structs (Go).

Wrong TS:

```ts
type Job = { done: boolean; doneAt?: Date };
```

Right TS:

```ts
type Job = { kind: "open" } | { kind: "done"; at: Date };
```

Wrong Go: `type Job struct { Done bool; DoneAt *time.Time }`.

Right Go:

```go
type JobOpen struct{}
type JobDone struct{ At time.Time } // Job is JobOpen | JobDone
```

If a comment must explain when a field combo is valid, the type is too loose.

## 2. Brand semantic primitives

`UserId` is not `OrderId`. `Cents` is not a generic `number`. Brand at construction; interiors take the branded type only.

Wrong TS:

```ts
function charge(userId: string, amount: number) {}
charge(orderId, dollars);
```

Right TS:

```ts
type UserId = string & { readonly __brand: "UserId" };
type Cents = number & { readonly __brand: "Cents" };
function charge(userId: UserId, amount: Cents) {}
```

Wrong Go: `func Charge(userID string, amount int) {}`.

Right Go:

```go
type UserID string
type Cents int
func Charge(userID UserID, amount Cents) {}
```

Parse once at the edge (`parseUserID`, `dollarsToCents`). Do not brand with a cast in the core.

## 3. Parse, do not validate, at boundaries

External JSON, query params, proto wire types, and DB rows are untyped until a parse function returns a rich internal type. Interior code trusts that type and does not re-check.

Wrong TS:

```ts
function apply(dto: unknown) {
  if (typeof (dto as any).userId !== "string") throw new Error("bad");
  // still a bag of strings deeper in
}
```

Right TS:

```ts
function parseCharge(raw: unknown): Charge {
  // zod/io-ts/manual: fail or return Charge { userId: UserId; amount: Cents }
}
function apply(c: Charge) { /* no shape checks */ }
```

Wrong Go:

```go
func Apply(m map[string]any) error {
    if _, ok := m["userId"].(string); !ok { return errBad }
    return nil
}
```

Right Go:

```go
func ParseCharge(raw json.RawMessage) (Charge, error) { /* ... */ }
func Apply(c Charge) error { /* trust Charge */ }
```

Wire DTOs stay at the handler. Domain types cross module boundaries.

## 4. Never lie to the compiler

`as any`, unchecked `as`, `interface{}` / `any` dumps, and `panic` type assertions silence errors. They do not fix the model. If the compiler cannot prove it, parse, narrow, or change the type.

Wrong TS: `const job = payload as Job`.

Right TS: `const job = parseJob(payload)` returns `Job | ParseError`.

Wrong Go: `v := raw.(JobDone)` panics; `_ = any(payload)` hides the model.

Right Go:

```go
done, ok := raw.(JobDone)
if !ok { return fmt.Errorf("not done") }
```

A buried cast is a future incident. Prefer a parse error over a lie.

## 5. Exhaustive variant handling

When the contract grows a variant, compilation must fail until every consumer handles it.

Wrong TS:

```ts
switch (job.kind) {
  case "open": return "open";
  case "done": return "done";
}
```

Right TS:

```ts
function label(job: Job): string {
  switch (job.kind) {
    case "open": return "open";
    case "done": return "done";
    default: {
      const _n: never = job;
      return _n;
    }
  }
}
```

Wrong Go: a `switch` on kind strings with a silent default.

Right Go: closed union + `exhaustive` (golangci-lint `exhaustive` on enums) or a type switch that returns an error on the unknown case, plus a test that fails when a new variant is added without a case.

If a new kind next month would compile everywhere, the match is not exhaustive.

## 6. Derive from authoritative schemas

Hand-mirrored types drift from OpenAPI, proto, GraphQL, and DB schema. Generate the wire types; map once into domain types.

Wrong TS: copy-paste an OpenAPI object into a `interface` and forget a field.

Right TS: `openapi-typescript` / `buf generate` -> `components["schemas"]["Charge"]`, then `parseCharge` into branded domain types.

Wrong Go: a hand-written struct that "matches" the proto.

Right Go: `protoc` / `oapi-codegen` / `sqlc` emit the DTO; domain types wrap or convert at the boundary.

The schema is the contract. Duplication is a second, unofficial contract.

## Design checklist

- [ ] Variants are sum types, not bool + optional bags.
- [ ] IDs and units are branded; primitives stay off domain functions.
- [ ] One parse per boundary; interiors take domain types.
- [ ] No `as any` / unchecked assertion / `interface{}` to quiet the checker.
- [ ] Switches are exhaustive (`never` / golangci `exhaustive`).
- [ ] Wire types are generated from OpenAPI, proto, or DB schema.

Adapted from cursor/plugins pstack principle-type-system-discipline (MIT).
