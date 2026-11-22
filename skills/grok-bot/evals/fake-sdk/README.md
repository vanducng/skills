# fake grok-bot-sdk

The grok-bot evals and `scripts/grok-bot.test.mjs` load this instead of the real SDK (`GROK_BOT_SDK_DIR=<this dir>`). It
has the real client's method shapes, logs every call to `$FAKE_GROK_STATE`, and, like the real app, never shows a send
that has no messageId in the chat. `sendMessage`'s `messageId` is optional in the real SDK's types; that is the trap.
