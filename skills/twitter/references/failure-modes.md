# Failure modes — twitter skill runbook

When the skill misbehaves, classify by error code/text first, then apply the matching recipe below.

## Quick triage

```
twitter doctor          # always run this first
```

`doctor` covers gopass entries, cookie shape, twikit version pin, and live network reachability with class-specific remediation hints.

---

## Error 226 — "looks like it might be automated"

**What it means.** X's anti-automation system flagged the request. Triggered by:
- Many writes in a short window (the 3-tweet thread smoke trips this reliably).
- Fresh login from an unusual IP.
- Repeated identical tweets.

**Fix.**
1. Wait 10–15 minutes and retry the same single call.
2. If it persists: rerun under the browser fallback — `twitter --use-browser fetch ...`. (Browser-side `post` is deferred to v2; for writes during a 226 incident, post via Dia manually.)
3. If 226 persists across the whole session: cool the account for a few hours; X's heuristic decays.

---

## 401 Unauthorized

**What it means.** `auth_token` or `ct0` is no longer valid. `auth_token` rotates ~quarterly; force-logouts also kill it.

**Fix.**
1. `twitter import-from-dia` — re-extract from the local Dia browser.
2. Or `twitter login` if Dia isn't available (gopass must hold username/password/TOTP seed).
3. `twitter doctor` to confirm the new cookies pass the network reachability check.

---

## 429 Too many requests

**What it means.** Per-endpoint rate ceiling hit. Read endpoints (~150/15min on `get_user_tweets`) are the usual culprits.

**Fix.**
1. Read the `x-rate-limit-reset` header (`doctor` parses it for you and prints minutes remaining).
2. Wait. There's no backoff escape — twikit will raise again until the window resets.
3. If you're hitting 429 frequently from normal use, lower the `--count` defaults or batch fewer reads.

---

## Account locked / verification challenge

**What it means.** X demands a captcha or email/phone verification — usually after suspicious activity. twikit can't complete this; the only fix is the GUI.

**Fix.**
1. Open `https://x.com` in Dia, log in, complete the challenge.
2. Once the challenge clears, `twitter import-from-dia` to refresh cookies.
3. `twitter doctor`.

---

## Twikit transaction-init failure

**Symptom.** `Couldn't get KEY_BYTE indices` or any error mentioning `ondemand.s` / `transaction`.

**What it means.** X rotated its main bundle format. The vendored patch in `scripts/lib/_twikit_patch.py` is now stale.

**Fix.**
1. The router's auto-fallback should already have kicked in (`twitter` prints `falling back to browser` to stderr).
2. To restore the fast path: refresh the patch.
   - Curl `https://x.com/`, find the new `,N:"ondemand.s"` token shape.
   - Adjust the regexes in `_twikit_patch.py` if needed.
   - Track upstream community fixes at https://github.com/d60/twikit/issues/408 and https://github.com/iSarabjitDhiman/XClientTransaction.
3. Re-run the phase-3 unit tests + write smoke gate (`tests/test_twikit_patch.py`, then `post → fetch → delete` round-trip).

---

## Selector-fragility (browser fallback only)

**Symptom.** `BrowserUnavailable: agent-browser failed: ... selector ... not found`.

**Fix.** X's DOM changes monthly. The browser fallback pins to `data-testid` attributes:
- `tweet`
- `tweetText`
- `tweetTextarea_0` (compose)
- `tweetButton`

If any of those drift, update `scripts/lib/browser_fallback.py`.

---

## When all else fails

`twitter doctor --offline` to confirm gopass health independent of network. Then re-import cookies, restart the agent-browser session (`agent-browser --session twitter close`), retry.
