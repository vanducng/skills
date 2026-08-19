# Technical writing

Shared prose standard for `vd:docs` (internal `./docs`) and `vd:tech-docs` (public Starlight sites). Goal: a tired engineer understands the page on the first read.

This file owns structure and style. `vd:unslop` owns removing AI tells and is the final pass.

Three rules sit above the rest:

| Rule | Do | Don't |
| --- | --- | --- |
| Cut idle words | "to", "use", "help", "do" | "in order to", "utilize", "facilitate", "perform" |
| Name the real thing | file, flag, command, symbol | synonym or paraphrase of the same thing |
| Rules serve the reader | rewrite if the sentence sounds machine-made | follow every rule and still ship sludge |

## Diataxis routing

One page, one mode. Action vs understanding, then learning vs work.

| Mode | Answers | Action or understanding | Learning or work | Voice |
| --- | --- | --- | --- | --- |
| Tutorial | How do I learn by doing this once? | Action | Learning | Teacher. Open with what the reader builds. Every step shows a result. Cut explanation to one clause plus a link. |
| How-to | How do I reach this goal at work? | Action | Work | Competent peer. Task in the title. Action only. Forks allowed: "If you need X, do Y." |
| Reference | What is this, exactly? | Understanding | Work | Dry facts. Options, limits, errors. Mirror the thing described. No instruction, no opinion. |
| Explanation | Why is it this way? | Understanding | Learning | One bounded topic. Context, trade-offs, history. Opinion lives here only. |

Do not mix modes. Split and link instead. No reference tables inside a tutorial. No hand-holding inside reference. No arguing inside a how-to.

### Map our doc types

| Artifact | Owner | Mode | Why |
| --- | --- | --- | --- |
| `docs/development-guidelines.md` | `vd:docs` | How-to + reference split | Procedures (setup, contribute) are how-to. Naming and layout tables are reference. Keep them in separate sections. |
| `docs/system-architecture.md` | `vd:docs` | Explanation | Components and boundaries answer why the system is shaped this way. |
| `docs/tech-stack.md` | `vd:docs` | Reference | Languages, versions, libraries. Facts only. Cite lockfiles. |
| `docs/deployment.md` | `vd:docs` | How-to | Environments, deploy, rollback. Numbered sequences. |
| `docs/decisions/` ADRs | `vd:docs` | Explanation | Why we chose this. Status can change; the record stays. |
| Getting started | `vd:tech-docs` | Tutorial | First success path. Visible output after each step. |
| Guides | `vd:tech-docs` | How-to | Named by the task the reader already has. |
| Reference pages | `vd:tech-docs` | Reference | Commands, flags, config keys, errors. |

README is a hub, not a fifth mode. Point at the right page. Do not teach, list every flag, and argue architecture on one page.

## Sentence rules (Google developer style)

| Rule | Do | Don't |
| --- | --- | --- |
| Tense | Present. "Will" only for events that happen later. | "The service will check the token" when it already does. |
| Person | Second person: "you". Tutorials may use "we" in steps. | "The user should..." |
| Voice | Active: "the compiler checks". | "is checked" unless the actor is unknown. |
| Instructions | Imperative. One instruction per sentence. | "should be done", "simply click" |
| Condition | Condition first: "To delete the file, run..." | Instruction first, then the if. |
| Lists | Numbered only for sequences. Bullets otherwise. Introduce with a full sentence. Parallel items. | Numbered dumps of unrelated facts. |
| Headings | Sentence case. Task = verb phrase. Concept = noun phrase. One h1. No skipped levels. | "Overview Of The API" |
| Links | Link text names the destination. | "click here" |
| UI and code | Code font for symbols. Bold for UI labels. Serial commas. | "etc." |

Never "simply", "easy", or "quickly" in a procedure. If it were simple, the reader would not be here.

## Instruction rules (simplified technical English)

| Rule | Apply |
| --- | --- |
| Imperative for procedures | "Install the package." Not "the package must be installed." |
| One topic per paragraph | New idea, new paragraph. |
| One thought per sentence | Split two instructions. Split two claims. |
| Length | Procedure sentences about 20 words. Other sentences about 25. |
| Articles stay | "Remove the backup file", not "Remove backup file". |
| One word, one job | If "check" means inspect, do not also use it for constrain. |
| No synonym cycling | Pick "start" or "initiate". Keep the one you pick. |
| Warning before the step | "If the count exceeds the budget, CI fails." |
| Avoid dangling -ing | Participles take too many jobs. Prefer a finite verb. |

The codebase is the word list. Write the real symbol. Do not invent jargon.

## Global English

| Rule | Apply |
| --- | --- |
| No idioms | No "out of the box", "under the hood", "on the fly". |
| No untranslatable humor | Skip jokes, puns, and cultural asides. |
| Short sentences | One clause unless the extra clause is the condition or consequence. |
| No stacked modifiers | "the script that checks the import budget", not "the proto import budget check script". |
| Place "only" and "not" next to the word they change | "fails only on growth" vs "only fails on growth". |
| One referent for "it", "they", "this" | Repeat the noun when in doubt. Never let "this" point at a whole clause. |
| Keep structure words | Keep "that" when it stops a misread. Repeat the article: "the client and the host". |
| No slashes for logic | "a, b, or both", not "and/or". |
| Punctuation | Periods, not semicolons. Plain hyphen "-", never an em dash or en dash. Straight quotes only. |

## Review checklist

Run this before you ship a page:

1. One Diataxis mode per page (or clearly split sections). Modes meet only via links.
2. Every claim a reader can check has a path, version, or command.
3. Every instruction is an imperative with its condition in front.
4. No sentence carries two instructions or two thoughts.
5. Present tense, second person, active voice unless the actor is unknown.
6. Numbered lists only for sequences. Headings are sentence case.
7. Each concept has one name. No synonym cycling.
8. No idioms, stacked noun strings, or ambiguous "this" / "it".
9. No em dashes, en dashes, or curly quotes. Idle words are gone.
10. Counts, trees, and command output are true at this commit.
11. Public pages (`vd:tech-docs`) have no private hosts, customers, or secrets.
12. `vd:unslop` has not run yet: run it last, then re-check items 9 and 10.

Adapted from cursor/plugins pstack technical-writing (MIT).
