---
name: twitter
description: Read and post on X/Twitter from the CLI — fetch tweets, timelines, and search; post tweets, replies, threads, and media. Cookie-based auth via twikit, bootstrapped from the local Dia browser session, secrets stored in gopass. Auto-falls back to agent-browser when twikit hits internal-API drift or X's "looks automated" Error 226. Use whenever the user asks to read a tweet/profile/search, post/reply/thread, delete a tweet, or run `twitter doctor` / `import-from-dia` / `login` to manage credentials.
keywords: [twitter, x, social, tweet, twikit, dia, gopass]
license: MIT
version: 0.1.0
metadata:
  author: vanducng
---

# twitter

Personal CLI for reading and writing on X/Twitter. Wraps a patched twikit primary path with an agent-browser fallback router for resilience.

## Quick start

```bash
twitter import-from-dia        # one-time: pull cookies from Dia (macOS)
twitter doctor                 # confirm setup
twitter fetch https://x.com/jack/status/2049336710572728783
twitter post "hello from twitter skill"
```

## Verbs

| Verb | Example |
|---|---|
| `import-from-dia` | `twitter import-from-dia [--profile NAME] [--dry-run]` |
| `login` | `twitter login` (gopass-backed; needs `credentials` + `totp` entries) |
| `doctor` | `twitter doctor [--offline]` |
| `fetch` | `twitter fetch https://x.com/<u>/status/<id>` · `twitter fetch @jack --count 10` · `twitter fetch search:claude --count 5` |
| `timeline` | `twitter timeline latest --count 20` · `twitter timeline home` · `twitter timeline user:@jack` |
| `post` | `twitter post "text" [--media a.jpg b.jpg] [--long] [--community ID] [--share-with-followers]` |
| `reply` | `twitter reply <url\|id> "text" [--media path...]` |
| `thread` | `twitter thread "a" "b" "c"` |
| `delete` | `twitter delete <url\|id>` |

Global flag `--use-browser` forces the agent-browser fallback for `fetch` / `post`.

## Failure modes

See [`references/failure-modes.md`](references/failure-modes.md) for the runbook covering Error 226, 401, 429, account-lock, transaction-init drift, and selector fragility. `twitter doctor` produces class-specific remediation hints inline.

## Credentials

All secrets live in gopass under `personal/x-twitter/`:

| Path | Format | Set by |
|---|---|---|
| `cookies` | `{"auth_token": "...", "ct0": "..."}` | `twitter import-from-dia` (or `twitter login`) |
| `totp` | base32 TOTP seed (raw secret, not the live code) | manual: `gopass insert personal/x-twitter/totp` |
| `credentials` | line 1 = password; then `username:` / `email:` keys | manual: `gopass insert -m personal/x-twitter/credentials` |

`import-from-dia` only writes `cookies`. `login` reads all three.

## Maintenance

- **twikit pin.** `twikit==2.3.3`. Upstream breaks every 6–12 weeks; pin holds the wire-protocol surface stable.
- **Cookie rotation.** `auth_token` rotates ~quarterly. Rerun `twitter import-from-dia` when `doctor` reports 401.
- **Browser fallback selectors.** `lib/browser_fallback.py` pins `data-testid='tweet'/'tweetText'/'User-Name'` for fetch and `data-testid='tweetTextarea_0'/'tweetButton'` for post (post is deferred to v2). X's DOM changes monthly; refresh selectors when fallback `BrowserUnavailable` errors mention "selector not found".

### Refreshing the twikit transaction patch

`lib/_twikit_patch.py` vendors three monkey-patches over twikit 2.3.3:

1. `PatchedClientTransaction.get_indices` — locates the bundle hash via the new `,N:"ondemand.s"` manifest token (replaces the broken upstream regex).
2. Tolerant `User.__init__` — uses `.get()` everywhere; survives `legacy['entities']['description']['urls']` being absent on accounts using the new `core` shape.
3. Minimal `Client.get_tweet_by_id` — skips the brittle reply-cursor parse.

**When to refresh:** `twitter doctor` reports `transaction-init failed` or any verb raises `Couldn't get KEY_BYTE indices` after cookies are confirmed valid.

**How:**
1. Open `https://x.com/` in a browser, view source, search for `,N:"ondemand.s"` (note leading comma + trailing structure). If shape changed, update `ON_DEMAND_FILE_REGEX` / `ON_DEMAND_HASH_PATTERN` in `_twikit_patch.py`.
2. Check upstream first — community usually posts a fix within ~1 week of a break: [twikit#408](https://github.com/d60/twikit/issues/408) and [iSarabjitDhiman/XClientTransaction](https://github.com/iSarabjitDhiman/XClientTransaction).
3. Verify with `python3 -m pytest scripts/tests/test_twikit_patch.py` then run `scripts/tests/integration_smoke.sh` (post → fetch → delete round-trip).
4. If the patch can't be salvaged, `TWITTER_USE_BROWSER=1` is the escape hatch for triage; reads still work via the browser fallback.

## Layout

```
twitter/
├── SKILL.md
├── references/failure-modes.md
└── scripts/
    ├── twitter                    # bash dispatcher
    ├── cmd_*.py                   # one per verb
    ├── lib/
    │   ├── _twikit_patch.py       # vendored upstream fixes
    │   ├── auth.py                # gopass + cookie tempfile
    │   ├── browser_fallback.py    # agent-browser implementations
    │   ├── dia_cookies.py         # macOS keychain → AES → SQLite
    │   ├── formatters.py          # tweet → dict / markdown
    │   ├── media.py               # upload validation + dispatch
    │   ├── paths.py               # gopass path constants
    │   ├── router.py              # twikit ↔ browser dispatcher
    │   ├── twikit_client.py       # async client factory + patch
    │   └── url_parser.py          # tweet URL / @handle / search:
    └── tests/                     # unit + integration smoke
```

## Tests

```bash
PY="$([ -x "$HOME/.claude/skills/.venv/bin/python3" ] && echo "$HOME/.claude/skills/.venv/bin/python3" || echo python3)"
"$PY" -m pytest scripts/tests/ -q          # unit (51 tests); fallback python3 needs: pip install --user -r scripts/requirements.txt
scripts/tests/integration_smoke.sh          # live (post → fetch → delete)
```
