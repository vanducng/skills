---
name: grok-bot
description: "Writes for a person who reads their OpenRig team in the Grok Bot app, and gives Grok Bot bots a skill for using the team's OpenRig MCP connector. Seat side: a short status, one decision card per question (lettered options, one recommendation), links instead of local paths, questions raised through the front door's question tools, and only markdown that renders in Grok Bot; scripts/check-message.cjs lints a draft. Bot side: assets/bot-skill.md is installed into Grok Bot's private skill library: list the team's questions, record only the person's exact words, hand work to the team, show status, never claim authority. Use when an intake or front-door seat writes to a person in Grok Bot, when the user says 'write this for Grok Bot', 'decision card', 'send the person a status in Grok Bot', 'install the OpenRig skill in Grok Bot', or 'teach the Grok Bot bot to use OpenRig'. Not for seat-to-seat messages, Slack or email drafts, or reports in the operator's own terminal (exec-brief)."
license: MIT
metadata:
  author: vanducng
  version: "0.1.0"
---

# grok-bot

The person reads the team on a phone, in Grok Bot, between other things. A message they cannot act on in one read costs a round trip; a path they cannot open or a table that does not render costs trust.

## Seat side: writing to the person

1. **Status first, short.** One to three sentences: what moved, what is blocked, what waits on them. No history and no process.
2. **One decision card per question.** Never fold two questions into one card. Exactly this shape, so the person can answer with one letter:

   ```
   **Decision 1: <one question>?**
   A. <option>
   B. <option>
   Recommendation: B, because <one reason>.
   ```

   Two to four options, lettered from A, and one recommendation naming one of them. End the message with "Reply with a letter, or in your own words."
3. **Links, not paths.** The person's phone opens `https://` links and nothing else. Link the PR, run or doc; drop worktree, log and cache paths, or say what they show.
4. **Raise each question through the front door too.** Create it with its options (`rig queue create --human-questions-file`, 1 to 4 questions, 2 to 4 options each, one `recommended`) so the bot can list and answer it with `rig_question_list` and `rig_question_answer`. The text card is what the person reads; the queue question is what records the answer.
5. **Only markdown that renders.** Verified in Grok Bot (desktop and iOS): headings, bulleted and numbered lists, bold, inline code, fenced code, links. UNVERIFIED, so do not use them until `references/unknowns.md` records an answer: tables, nested lists, blockquotes, raw HTML.
6. **Lint before sending:** `node scripts/check-message.cjs message.md` exits 0 when the draft follows rules 1 to 5 (`--json` for the findings). A draft that passes is sent as it is; do not rewrite a good draft.

## Bot side: the Grok Bot skill

`assets/bot-skill.md` is the skill a Grok Bot bot follows when it uses the team's OpenRig connector. The operator installs it: add the connector (Connect apps > Add a custom connector > Remote HTTPS, the front door's URL and its token header), then ask the bot to save `assets/bot-skill.md` as a private skill. The library is shared by every bot on the account, so the text names no team or seat.

When you act as that bot here (or in a test), follow `assets/bot-skill.md` exactly. Its core rule: an answer is the person's choice of an option they were shown, or their exact words; a reply that adds a condition or changes an option is recorded as their words, never as the nearest option.

## Unknowns

Two facts need the operator's Grok Bot and stay UNVERIFIED until answered: whether a tool result can raise a multiple-choice card (until then, the lettered text card is the interface), and which of tables, nested lists, blockquotes and HTML render. `references/unknowns.md` holds the test prompts and the place to record the answers.
