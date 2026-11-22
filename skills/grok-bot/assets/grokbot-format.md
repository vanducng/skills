---
name: grokbot-format
description: Format every reply in this chat for a person reading on a phone in Grok Bot. Use for every answer that reports team status, a digest, a decision card, a question from the team, or the result of a request; it overrides any table or long-paragraph layout from other skills. Not for code the person asked to see.
---

# Grok Bot format

The person reads this chat on a phone, between other things. Each reply must be readable in one scroll and actionable without opening anything else.

## Shape

1. **First line: one bold headline** with a status dot and the time: `🟢|🟡|🔴 **<what> · <state in five words>** · HH:MM ICT`. 🟢 on track, 🟡 needs attention or an ETA moved, 🔴 down, blocked or late.
2. **Needs you**, right under it: `**Needs you:** none`, or one line per ask. Asks first, status after.
3. **Context before the card.** For each decision, 2-4 short lines in the message so the person can decide without asking:
   - `**1 · <short title>**` then: what it is and why it waits on him; the evidence (CI, review, QA, who asked, since when) with links; what changes if he says yes, and the risk or cost if he says no or waits.
   - Facts only from what the team or tools returned this turn; unknown is `?`.
4. **All decisions in ONE question card**, one page per decision, so the person taps through them with Next and submits once. Never one card per decision, and never stop after the first answer.
   - Each page: the question in plain words with its number (`1 · Merge repo#123?`), options `A`, `B`, `C` as `<action> → <what he will see>`, the recommended option marked as recommended with its reason (at most 12 words) in the option text, and a typed answer allowed.
   - Put the headline, Needs you and status lines in the message before the card.
   - Only if the card cannot be shown, fall back to text: `**1 · <question?>**`, then `- **A** <action> → <what he will see>` per option, then `✅ **Recommend A** · <why>`.
   - After submit, act on every page's answer. A tapped option is the person's choice; a typed answer is recorded as their exact words. A page left unanswered stays open: say which ones, and ask again later.
5. **Status as a short list**, one line per project or item: `🟢 **<name>** · <state> · <next step or ETA>`. Tables only for the Rigs and Inbox boards below (3-4 short columns).
6. **Last line, when anything waits and no card is shown:** `**Reply:** 1A 2B · "ok" takes every recommendation`. With a card, end with `Tap through the card, or type "ok" to take every recommendation.`

## Which shape

- **No rig or project named** ("what's up?", "status"): a brief across the org. Headline, Needs you, then one status line per rig (`🟢|🟡|🔴 **<rig>** · <state> · <what waits>`), then the context and one card for the decisions waiting on him. At most 12 status lines.
- **A rig or project named**: only that rig. Headline, its decisions with context and one card, then at most 6 status lines.
- **Long content** (a plan, a report, more than about 25 lines, anything with a table): put it in a Page (canvas) and send its card, with a 3-line summary and the decisions in the chat. Never paste a long document into the chat.
- **Relayed digests** (the 15-minute routine): show only items that need his decision or action, batched into one message with context and one card. Drop FYI-only items unless he asked for them.
- **Board** (the 08:30 and 18:00 briefs, and "what's up" with no rig named), in this order:
  1. Headline and Needs you.
  2. **Rigs**, one markdown table, worst first: `| Rig | State | Needs you |`, State as `🔴 blocked`, `🟡 attention`, `🟢 ok`; Needs you in at most six words, `-` when nothing.
  3. **Inbox**, one markdown table of replies and follow-ups he owes, oldest first: `| Where | From · about | Owed since | Link |`, Where as `💬 Slack`, `🎫 Jira`, `🐙 GitHub`, `✉️ Email`. Only items waiting on him; say `Inbox: clear` when none.
  4. Context and one card for the decisions.
  Tables stay at three or four short columns so they fit a phone; anything wider goes in a Page.

## Rules

- At most 12 lines outside cards. If more is true, give the top items and offer "say more for the rest".
- One idea per line. No paragraph longer than two lines.
- Bold only the headline, the item names and the options. Emoji only for the status dots and ✅ on the recommendation.
- Every PR, ticket, run or doc is a short link: `[repo#123](url)`. No bare URLs, no local file paths, no hashes unless asked.
- Times in ICT (GMT+7), `HH:MM`. Unknown is `?`.
- Plain words. Explain any team jargon in eight words or drop it. No em dashes.
- Code blocks only for a command the person will copy.
- When you pass on a seat's message, keep its facts and its options exactly; change only the layout to this shape.
