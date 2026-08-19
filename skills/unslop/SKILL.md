---
name: unslop
description: "Cut AI tells from prose and add a human voice - PR bodies, docs, READMEs, blog/devlog posts, release notes, review summaries, commit messages, any text a person will read. Use when the user says 'unslop', 'de-AI this', 'remove AI tells', 'humanize this', 'this sounds like AI', or as the final pass whenever another skill produces prose. Do not use for conversion copy structure (vd:copywriting), doc structure (vd:docs, incl. its site mode), or code slop (vd:code-refactor-review)."
license: MIT
argument-hint: "[file, text, or 'last message']"
metadata:
  author: vanducng
  version: "1.0.0"
  source: "adapted from cursor/plugins pstack/skills/unslop (MIT, Lauren Tan)"
---

# Unslop

> Remove the patterns that read as machine-made, then put a voice back in. Both halves are the job.

## What this skill is - and isn't

| Skill | Question it answers | Output |
|---|---|---|
| **`vd:unslop`** | **"Does this read like a human wrote it?"** | **Rewritten prose, meaning preserved** |
| `vd:copywriting` | "Does this convert?" | Formula-driven marketing copy |
| `vd:docs` (incl. `site`) | "Is this documented correctly?" | Structured docs / docs site |
| `vd:code-refactor-review` | "Is this *code* slop?" | Diff review report |
| `vd:simplify` | "Is this code hard to read?" | Behavior-preserving refactor |

Unslop edits **prose**. It changes wording and rhythm, never facts, claims, links, or code blocks.

## Hard rules

1. **Meaning is frozen.** Rewrite the sentence, never the claim. If a fact looks wrong, flag it - don't fix it silently. Why: an edit pass that changes meaning is a new draft nobody reviewed.
2. **Match the intended register.** A PR body, a launch tweet, and an incident report don't share a voice. Why: "human" is not one tone.
3. **Cut before you decorate.** Most fixes are deletions. Adding personality to filler still leaves filler.
4. **Self-audit before returning.** Ask "what still makes this obviously AI-generated?" and fix it. One pass is never enough.
5. **House dash rule.** No em dashes, no en dashes, no curly quotes. Plain `-` with spaces is the separator. Why: this catalog and its owner's global style ban them; the em dash is also the single strongest tell.

## Process

1. Scan against the pattern catalog below. Mark every hit.
2. Rewrite. Preserve meaning, match the register.
3. Add soul (next section).
4. Self-audit: "What makes this obviously AI generated?" Fix the remainder.

## Adding soul

Removing patterns is half the job. Sterile, voiceless text is just as obvious.

- **Have opinions.** React to facts instead of neutrally listing pros and cons.
- **Vary rhythm.** Short sentences. Then longer ones that take their time.
- **Acknowledge complexity.** "Impressive but also kind of unsettling" beats "impressive."
- **Use "I" when it fits.** First person isn't unprofessional.
- **Let some mess in.** Perfect structure looks machine-made.
- **Be specific.** Not "this is concerning" but "there's something unsettling about agents churning away at 3am."

## Pattern catalog

### Content

1. **Puffery.** "pivotal moment", "testament to", "evolving landscape", "setting the stage for". Cut it, state what happened.
2. **Name-dropping.** Listing outlets or tools without context. Pick one, say what it said.
3. **Superficial -ing phrases.** "highlighting...", "ensuring...", "showcasing...", "fostering...". Delete or expand with a real source.
4. **Promotional language.** "nestled", "vibrant", "breathtaking", "groundbreaking", "renowned", "must-visit". Use neutral description.
5. **Vague attributions.** "Experts believe", "Industry reports suggest". Name the source or delete.
6. **Formulaic challenges.** "Despite challenges... continues to thrive." Replace with specific facts.

### Language

7. **AI vocabulary.** Additionally, crucial, delve, enduring, enhance, fostering, garner, interplay, intricate, landscape (abstract), pivotal, showcase, tapestry, testament, underscore, vibrant. Use plain words.
8. **Fancy "is".** "serves as", "stands as", "boasts", "features". Say "is" or "has".
9. **"Not just X, but Y."** State the point directly.
10. **Rule of three.** Forcing ideas into triads. Use the natural number.
11. **Synonym cycling.** Protagonist, main character, central figure in one paragraph. Pick one, repeat it.
12. **False ranges.** "from X to Y" where X and Y aren't on a scale. List the items.

### Style

13. **Em/en dashes and curly quotes.** Banned (Hard rule 5). End the sentence, use a comma, or use plain `-`.
14. **Colon as mid-sentence connector.** Fine before a list or example, not as a crutch. Rewrite so the point stands alone.
15. **Boldface overuse.** Don't bold every proper noun or acronym.
16. **Inline-header restating lists.** "**Performance:** Performance improved..." - convert to prose. A bold lead-in followed by genuinely new detail is fine.
17. **Title Case Headings.** Use sentence case.
18. **Decorative emojis** in headings and bullets. Remove.

### Communication artifacts

19. **Chatbot phrases.** "I hope this helps!", "Let me know if...", "Certainly!", "Found the smoking gun!" Remove.
20. **Cutoff disclaimers.** "While specific details are limited..." Find the source or remove.
21. **Sycophancy.** "Great question! You're absolutely right!" Respond directly.

### Filler

22. **Filler phrases.** "In order to" → "To". "Due to the fact that" → "Because". "It is important to note that" → delete.
23. **Hedging stacks.** "could potentially possibly be argued" → "may".
24. **Generic conclusions.** "The future looks bright." State the plan or the fact.

### Jargon

25. **Abstract metaphor nouns.** Substrate, wedge, vector, locus, nexus, primitive (noun), harness (metaphor), bedrock, modality, paradigm, north star, flywheel, endgame. Pick the concrete word: "substrate" → "base", "wedge in" → "add", "endgame" → "the last phase".

### Plain speech

26. **Say what it does, not how it feels.** "SQL you can read" names a feeling. Name the mechanism or number: "`.toSQL()` returns the exact string sent to the database". If the sentence could appear unchanged in another project's docs, it says nothing - cut it.
27. **One idea per sentence.** If the reader backtracks to parse it, split it.
28. **Active voice.** "queries are validated" → "the compiler validates queries". Passive only when the actor is unknown or truly irrelevant.
29. **Cut adverbs or use a stronger verb.** "significantly improves" → the measured delta.
30. **Prefer the plain word.** "utilize" → "use", "leverage" → "use", "facilitate" → "help", "numerous" → "many".

## Workflow position

**Typically follows:** any prose-producing skill - `vd:devlog`, `vd:ship` (PR bodies), `vd:docs` (incl. `site`), `vd:journal`, `vd:show-off`, `vd:copywriting`, `vd:code-review` summaries
**Compares to:** `vd:copywriting` owns conversion structure; unslop owns de-AI voice. Run copywriting first, unslop last.

## Rationalizations to catch

| Thought | Reality |
|---|---|
| "It's just a PR body, skip the pass" | PR bodies are the most-read prose you ship. Two minutes. |
| "The draft is already concise" | Concise slop is still slop. Check the catalog, especially 7, 13, 19. |
| "I'll add personality by adding words" | Rule 3. Most fixes are deletions. |
| "The em dash reads fine here" | Hard rule 5. No exceptions - it is the number-one tell. |
| "Rewriting might change the meaning slightly" | Then you are drafting, not unslopping. Hard rule 1 - flag, don't drift. |
