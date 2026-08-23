---
name: skill-creator
description: "Authors the CONTENT of a brand-new agent skill for any stack or agent runtime - turns a vague capability request into a routable SKILL.md with a trigger-rich description, hard rules, and a verification loop, and repairs a skill that never activates. Activates when the user says 'create a skill', 'write a skill for X', 'make this a skill', 'turn this into a skill', 'my skill never triggers', 'why doesn't my skill activate', or asks to extract a repeated workflow into something reusable. Owns authoring and routing repair; defers to vd:skill-management for scaffolding, vendoring, versioning and release mechanics, vd:skill-evolve for improving skills that already exist, vd:skill-audit for usage statistics, and vd:rule-miner for standing CLAUDE.md rules."
license: MIT
argument-hint: "[capability | --audit <name> | --extract] [--dir <skills-root>]"
metadata:
  author: vanducng
  version: "1.0.0"
---

# Skill Creator

> A skill is a **conditional prompt fragment**. It costs context every time it loads and earns its place only by making the agent behave better than the base model would.

## What this skill is - and isn't

| Skill | Question it answers | Output |
|---|---|---|
| **`vd:skill-creator`** (this) | "How do I author this capability so an agent reliably uses it?" | A validated `SKILL.md` (+ optional `references/`, `scripts/`) |
| `vd:skill-management` | "How do I scaffold, vendor, validate, and release skills?" | Lifecycle/CLI orchestration (delegates authoring here) |
| `vd:skill-evolve` | "How should *existing* skills change given this session?" | Edits to skills that already exist |
| `vd:skill-audit` | "Which skills actually get used?" | Usage report from session history |
| `vd:docs` | "How do I explain this to humans?" | Prose documentation |

Two boundaries worth holding:

- **New vs existing.** Authoring something that doesn't exist yet is this skill. Improving what already ships is `vd:skill-evolve`.
- **Content vs mechanics.** What goes *inside* `SKILL.md` is this skill. Moving, vendoring, versioning, and releasing it is `vd:skill-management`.

`vd:skill-management` also answers "create a skill" as the lifecycle entry point and hands authoring here (its `--create` mode). Either routing reaches the same place, so if that skill picked up the request first, continue rather than bouncing it back - then return to it for the scaffold-to-catalog mechanics once the content is written.

Skills instruct an **agent**; docs inform a **human**. If the artifact's reader is a person, write docs instead.

## The bar: does this deserve to be a skill?

Answer all four **yes** before writing anything.

1. **Recurrence** - will this be needed again, in a form worth reusing? A one-off belongs in the conversation.
2. **Non-obvious** - does it encode judgement, house rules, or a gotcha the base model gets wrong unaided? Restating `git commit -m` teaches nothing.
3. **Routable** - can you name the concrete phrases a user types when they want it? If you can't write the trigger list, the agent can't match it.
4. **Bounded** - is the domain narrow enough for firm rules? "Be a good engineer" is not a skill.

Fail any → say so and stop. **Not writing a skill is a valid, common outcome.** A catalog of 20 sharp skills beats 80 vague ones: every extra skill dilutes routing and taxes context.

## Hard rules

1. **Description is the router.** It is the *only* thing an agent sees when deciding whether to load the skill. It must state what the skill does AND the trigger phrases. Vague descriptions never fire - a perfect body behind a weak description is dead weight.
2. **Verify before claiming done.** Run the repo's validator and confirm the skill actually loads. "Wrote the file" is not "shipped."
3. **Prescribe, don't describe.** "Run X, then verify Y" beats "this skill is about X." Every section should change what the agent *does*.
4. **Portable by default.** No personal absolute paths, usernames, machine-specific locations, or assumed OS. Use `$HOME`, repo-relative paths, env vars, or documented overrides. A skill that only works on the author's laptop is broken.
5. **Earn every line.** Long skills get skimmed and their rules get dropped. Cut anything the base model already does correctly. The bar lives in [`references/writing-principles.md`](references/writing-principles.md) (two loads, no-op test, completion criteria, anti-staleness, length tracks failure risk).
6. **Name the runtime seams.** If a step depends on tooling that isn't universal (a specific CLI, an editor API, a subagent mechanism), say so and give the fallback.

## Workflow

### 1. Interrogate the request

Never write from a one-line prompt. Establish, asking the user when unclear:

- **Trigger phrases** - the literal words a user would type. Collect 4-8.
- **Concrete task** - one real example end to end, with the expected output.
- **Failure mode without the skill** - what does the agent get wrong today? This becomes the hard rules. *If nothing goes wrong today, the skill is unnecessary.*
- **Scope edges** - what is explicitly NOT this skill's job, and which skill owns that instead.
- **Verification** - how does anyone know the skill worked?

Can't answer "what goes wrong without it?" → return to the bar above.

### 2. Locate the target and learn local convention

Skill roots differ by agent and project. Detect rather than assume, and **resolve in this order** - a project-local root always wins over a global one, so the skill lands where the user is working:

1. explicit `--dir <path>`
2. a root declared by the repo (`AGENTS.md`, `CONTRIBUTING.md`, a manifest)
3. project-local: `./skills`, `./.agents/skills`, `./.claude/skills`
4. runtime-global fallbacks: `$HOME/.factory/skills`, `$HOME/.claude/skills`, `$HOME/.agents/skills`

```bash
for d in ./skills ./.agents/skills ./.claude/skills \
         "$HOME/.factory/skills" "$HOME/.claude/skills" "$HOME/.agents/skills"; do
  [ -d "$d" ] && echo "candidate: $d"
done
```

If several candidates exist at the *same* precedence level, **ask** rather than guess - writing a project skill into a global root (or the reverse) is silently wrong and hard to notice later.

If the root is a git repo or ships helper scripts, **its conventions win over this skill's defaults**:

```bash
ls scripts/ 2>/dev/null                      # new-skill.sh, validate.sh, check-*.sh
```

Read any `AGENTS.md` / `CONTRIBUTING.md` / `CLAUDE.md` at that root **in full** - naming, privacy, validation, and catalog-sync rules are often stated far down the file, and a missed one fails the repo's own gates.

Read 2-3 existing skills in that root and match their frontmatter fields, heading depth, and voice. A skill that looks foreign to its catalog is harder to trust and maintain. Prefer a provided scaffold (`scripts/new-skill.sh <name>`) over hand-creating the directory.

### 3. Write the description (highest-leverage step)

Spend real effort here - it decides whether the skill ever runs.

**Shape:** `<what it does + for what stack/context> + Activates when <situations>, <file/path signals>, or when the user says '<phrase>', '<phrase>'.`

| | Example | Why |
|---|---|---|
| Bad | `"Helps with testing."` | No trigger, no scope. Never routes. |
| Bad | `"The best skill for all your database needs!"` | Marketing, not matching. |
| Good | `"Writes and fixes Pest tests in Laravel repos. Activates when editing tests/**, when a test fails after a code change, or when the user says 'write a test', 'fix the failing test', 'add coverage'."` | Names stack, file signal, and literal phrases. |

Rules:
- Third person, declarative. No "you" or "I".
- Include the **stack or domain** so it doesn't collide with sibling skills.
- Include **negative scope** when a neighbour is easily confused: `"Do not use for <X> - that's <other-skill>."`
- Quote trigger phrases verbatim as users type them, not as you'd phrase them.

### 4. Write the body

Default skeleton - drop any section that would be filler:

```markdown
# <Name>

> One-line framing of the discipline.

## What this skill is - and isn't      # boundary table vs neighbours
## Hard rules                          # numbered, non-negotiable, each with a WHY
## Workflow                            # numbered steps, each with a verification
## <Domain reference>                   # tables/rubrics the agent applies
## Anti-patterns                        # concrete failure modes to avoid
## Rationalizations to catch            # two-column: "thought" vs "reality"
```

Guidance:
- **Tables over prose** for anything with cases. Agents apply them more reliably.
- **Every hard rule needs a reason.** Unjustified rules get rationalized away under pressure.
- **Include the failure mode, not just the instruction.** "Run the validator (a malformed frontmatter block silently disables the skill)" beats "run the validator."
- **Show one worked example** when the output shape matters.
- Keep the core under ~200 lines; push depth into `references/<topic>.md` and link it. Long context degrades rule-following.
- Add `scripts/` only for deterministic mechanics (validation, scaffolding) - never to wrap something the agent should reason about.

### 5. Verify - the step that gets skipped

Do not report success on file creation alone.

Run the repo's validator if one exists, and **let it fail loudly** - never mask the exit status with `|| true`, or a broken skill reports as shipped:

```bash
if [ -f scripts/validate.sh ]; then bash scripts/validate.sh; fi   # non-zero exit = do not ship
```

Then check by hand, since validators typically lint frontmatter and nothing else:

- [ ] Frontmatter parses; `name` is kebab-case and **equals the directory name** (a mismatch silently disables the skill in most loaders).
- [ ] `description` names both the capability and the trigger phrases.
- [ ] No personal paths anywhere in the skill, not just `SKILL.md`:
      `grep -rnE '/Users/[a-z]|/home/[a-z]|C:\\Users' <skill-dir>/`
- [ ] Every referenced file actually **resolves** - extracting the names is not enough, test each one:
      ```bash
      grep -rhoE '(references|scripts|assets)/[A-Za-z0-9._/-]+' <skill-dir>/ | sort -u |
        while read -r f; do [ -e "<skill-dir>/$f" ] || echo "MISSING: $f"; done
      ```
- [ ] Repo-specific gates pass (docs sync, path guards, catalog counts) - see the root's `AGENTS.md`.
- [ ] **Routing rehearsal**: read the description cold and ask *"would I load this for each trigger phrase, and NOT load it for a neighbour's task?"* Both directions matter - a description that over-triggers is as bad as one that never fires. Where the runtime can list or dry-run skill matching, use it; otherwise state plainly that routing is unverified rather than implying it was tested.

Ship only when all pass.

### 6. Sync the catalog

Many skill roots track a catalog, count, or index. A skill added without its catalog entry is invisible and counts as incomplete. Check the root's `AGENTS.md` for the required files and any `check-docs-*.sh` gate, then update them in the same change.

## `--audit <name>`: fix a skill that never fires

Diagnose in this order - the earliest failure wins, and it is almost always the description.

| Symptom | Likely cause | Fix |
|---|---|---|
| Never activates | Description lacks trigger phrases | Rewrite per §3 with literal user wording |
| Activates for the wrong tasks | Description too broad, or overlaps a sibling | Narrow scope; add explicit negative scope |
| Activates but ignored | Body is descriptive, not prescriptive | Convert prose to numbered rules + workflow |
| Rules dropped mid-task | Skill too long, or rules unjustified | Cut to essentials; attach a WHY to each rule |
| Works only for the author | Hardcoded paths or assumed local tooling | Parameterize; document the override |
| Loader rejects it | `name` ≠ directory, malformed frontmatter | Run the validator; fix frontmatter |

Report findings by severity, fix them, then re-run §5.

## `--extract`: turn a repeated conversation into a skill

When the user says *"we keep doing this"*: reconstruct the actual steps taken (don't idealize them), identify the corrections made along the way - those become hard rules - then apply §1's bar. Frequency alone doesn't justify a skill; frequency **plus** a non-obvious failure mode does.

## Anti-patterns

- **Description as marketing.** "The ultimate X skill!" Routing matches situations, not enthusiasm.
- **Restating the base model.** If the agent already does it correctly, the skill adds context cost and nothing else.
- **Kitchen-sink scope.** "backend-development" covering HTTP, DB, queues, and deploys can't hold firm rules. Split by decision boundary.
- **Untested shipping.** Declaring done without loading the skill or running the validator.
- **Copy-paste cargo cult.** Cloning another skill's headings when half don't apply. Structure serves content.
- **Silent overwrite.** Creating a skill whose name already exists, clobbering the original. Always check first.
- **Documentation cosplay.** Explaining a domain instead of directing an agent. Skills change behavior.

## Rationalizations to catch in yourself

| Thought | Reality |
|---|---|
| "I'll write the description last" | It's the highest-leverage part; drafting it first clarifies scope |
| "More detail makes it more reliable" | Past ~200 lines rule-following *degrades*; move depth to `references/` |
| "It's obviously useful" | If you can't name what breaks without it, it isn't |
| "Validator passed, so it works" | Validators lint frontmatter; they don't test routing |
| "I'll make it generic so it covers everything" | Generic skills route to nothing. Specific triggers fire |
| "The user asked for a skill, so I must write one" | Recommending against one is a valid, useful answer |

## Workflow position

```
repeated task / vague capability request
        ↓
vd:skill-creator  →  validate  →  catalog sync  →  review  →  ship
        ↑                                                       │
        └──────────── --audit when it doesn't fire ←─────────────┘
```
