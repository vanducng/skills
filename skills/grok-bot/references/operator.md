# Operator side: messaging a Grok Bot bot from a shell

`scripts/grok-bot.mjs` lets an operator session (for example Pi codemode through bash) list the bots, send to one, wait for its reply and read its chat. It runs only on the Mac where the Grok Bot desktop app is signed in: it uses that app's own session through grok-bot-sdk.

## Setup, once per Mac

```bash
npm install --prefix ~/.cache/grok-bot-sdk github:RongleCat/grok-bot-sdk#42c75eb13f24630d1b689629502d4320c4219cdb
```

That commit is SDK 0.78.1. It was checked against desktop app 1.2.3. `GROK_BOT_SDK_DIR` overrides the install folder; it may also point at the package folder itself.

## Commands

All print JSON. Exit 0 means ok, 1 means an error (`{ok:false, error, message}`), 2 means usage.

| Command | What it does |
|---|---|
| `node scripts/grok-bot.mjs bots` | `{bots: [names], appVersion}` |
| `node scripts/grok-bot.mjs send <bot> "<text>"` | Sends with a fresh messageId. Prints `{messageId, after, delivery}`. |
| `node scripts/grok-bot.mjs wait <bot> --after <seq> [--message-id <id>]` | Waits for the bot's first finished message after `seq`. Prints `{reply: {seq, ts, from, text}}`. |
| `node scripts/grok-bot.mjs ask <bot> "<text>"` | `send` then `wait`, in one command. |
| `node scripts/grok-bot.mjs read <bot> [--limit 10] [--since <iso>] [--jsonl]` | The chat, oldest first. With `--jsonl`, one `{seq, ts, from, text}` per line; `from` is `bot` or `operator`. |

`wait` and `ask` poll every `--interval` seconds (default 12) for up to `--timeout` seconds (default 300). A bot usually answers in 2 to 3 minutes. On a timeout, run `read` later; the reply still lands in the chat.

## Rules

- **Every send has a messageId.** The script always passes one. A send without one is accepted, but the app never shows it in the chat and the bot never answers (checked with app 1.2.3). If you write your own SDK call, pass `messageId: crypto.randomUUID()`.
- **Never print the token.** The script never prints the desktop session's token, and it redacts every credential string from its output and error messages. Do not log `desktopCredentials()`.
- **Do not use `gbot`.** grok-bot-cli 0.12.5 fails on app 1.2.3 (upstream issue #171).
- **Send only what you were asked to send.** A draft for the operator stays a draft. Each send is a message in the person's chat.

## Testing

`evals/fake-sdk/` is a fake SDK with the real method shapes, and the evals and `scripts/grok-bot.test.mjs` run against it (`GROK_BOT_SDK_DIR=evals/fake-sdk`, state in `FAKE_GROK_STATE`). Like the real app, it never shows a send without a messageId. No test sends a real message. A live check is one `ask` on the operator's Mac, run by the operator.
