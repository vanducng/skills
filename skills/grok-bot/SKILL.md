---
name: grok-bot
description: "Grok Bot and an OpenRig team. Seat side: write for a person reading in Grok Bot (a short status, one decision card per question with lettered options and one recommendation, links not local paths, only markdown that renders; scripts/check-message.cjs lints a draft). Bot side: two Grok Bot library skills, assets/bot-skill.md for the OpenRig connector (record only the person's exact words, never claim authority) and assets/grokbot-format.md for the layout of every reply. Operator side: scripts/grok-bot.mjs lists bots, sends with a messageId, waits for the reply and reads the chat from a shell. Use when the user says 'write this for Grok Bot', 'decision card', 'install the OpenRig skill in Grok Bot', 'message the bot', 'ask the bot from the terminal', 'read the Grok Bot chat' or 'list my Grok Bot bots'. Not for seat-to-seat messages, Slack or email drafts, or terminal reports (exec-brief)."
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

`assets/grokbot-format.md`, approved by the operator, is the second library skill: the layout of every bot reply (status headline, what needs the person, all decisions in one question card). Install it the same way; keep its text as approved.

When you act as that bot here (or in a test), follow `assets/bot-skill.md` exactly. Its core rule: an answer is the person's choice of an option they were shown, or their exact words; a reply that adds a condition or changes an option is recorded as their words, never as the nearest option.

## Operator side: messaging a bot from a shell

On the operator's Mac (the Grok Bot desktop app signed in), `scripts/grok-bot.mjs` lists bots, sends, waits for the reply and reads the chat, through grok-bot-sdk and the app's own session. For example: `node scripts/grok-bot.mjs ask Atlas "What is waiting on me?"`, or `read Atlas --since <iso> --jsonl`. Setup, every command and its output: `references/operator.md`.

- Every send has a messageId (the script makes one): a send without one is accepted but never shows in the chat.
- Never print the token; never use `gbot` (it fails on the current app).
- Send only what you were asked to send; a draft stays a draft.

## Unknowns

Two facts need the operator's Grok Bot and stay UNVERIFIED until answered: whether a tool result can raise a multiple-choice card (until then, the lettered text card is the interface), and which of tables, nested lists, blockquotes and HTML render. `references/unknowns.md` holds the test prompts and the place to record the answers.
