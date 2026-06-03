# Devlog Voice

Use this taste profile unless the user supplies a stronger style cue.

## Default voice

- Matter-of-fact builder voice.
- First person is OK when it clarifies ownership.
- Technical but readable. Keep real tool names when they carry meaning.
- Concision beats perfect grammar.
- Prefer concrete verbs: shipped, cut, pinned, traced, merged, posted, rewrote.
- Let uncertainty stay visible: "still open", "not solved yet", "tradeoff".

## Good structure

- Open with the actual outcome or tension.
- Name the constraint that made the work interesting.
- Show the decision, not every step.
- End with next move or lesson, not a CTA.

## Preferred details

- Skill names: `vd:worktree`, `vd:ship`, `vd:twitter`, `vd:devlog`.
- Commands when they are the point: `twitter post`, `bash scripts/validate.sh`.
- Artifacts: branch name, PR URL, file path, test command, docs page.
- Small automation wins and workflow tightening.

## Avoid

- Hashtags.
- Emoji.
- "I'm excited to announce".
- "Game changer", "10x", "revolutionary", "supercharge".
- Explaining basic AI/agent concepts to technical readers.
- Meta apologies about rough drafts.

## Example shapes

Ship:

```text
I moved <thing> from project-local habit to reusable skill today.

The useful part was not the file. It was turning the workflow into args:
source, format, style, action.

Now "devlog today long post" can gather facts, keep my voice, and publish
through the same X CLI I already use.

Small workflow win: less ceremony between shipping and talking about shipping.
```

Debug:

```text
The bug was not in <obvious place>.

I chased <false lead>, then found <root cause> in <artifact>.

Fix was small. Lesson was bigger: <principle>.
```
