# Unknowns to test in Grok Bot

Two facts need a real Grok Bot app, and no CLI or API reaches it. Each is UNVERIFIED in `SKILL.md` until the operator runs its test prompt and the answer is recorded here with the date and the app version (desktop and iOS separately).

## 1. Which markdown renders

Verified from Grok Bot's docs and app: headings, bulleted and numbered lists, bold, inline code, fenced code and links.

Test prompt (paste into any bot, as one message):

````
Repeat the text between the lines exactly, as markdown, with no comment.
---
A table:

| Option | Cost |
|---|---|
| A | none |
| B | 40 USD |

A nested list:
- Parent
  - Child
    - Grandchild

> A blockquote line.

~~Struck through~~ and a task list:
- [ ] open
- [x] done

Raw HTML: <b>bold?</b> line<br>break
---
````

Record, per element, on desktop and on iOS: renders, shows as raw text, or is dropped.

| Element | Desktop | iOS | Date, version |
|---|---|---|---|
| Table | UNVERIFIED | UNVERIFIED | |
| Nested list | UNVERIFIED | UNVERIFIED | |
| Blockquote | UNVERIFIED | UNVERIFIED | |
| Strikethrough, task list | UNVERIFIED | UNVERIFIED | |
| Raw HTML | UNVERIFIED | UNVERIFIED | |

When an element renders on both, move it to the verified list in `SKILL.md` rule 5 and drop its rule from `scripts/check-message.cjs`.

## 2. Can a tool raise a multiple-choice card

Grok Bot's own cards are approval, secure-secret and connect cards. Whether an MCP tool result can raise a card the person answers by tapping is not documented.

Test, with the OpenRig connector added and a team question waiting that has options (created with `rig queue create --human-questions-file`):

```
@<connector> What does the team need from me? Show me the first question.
```

Record: does Grok Bot show a tappable choice card, an approval card, or the options as text? If the person taps an option, which tool call does the bot make (it should be `rig_question_answer` with `choices`)?

| Result | Date, version |
|---|---|
| UNVERIFIED | |

Until this records a tappable card, the lettered text card in `SKILL.md` rule 2 is the interface.
