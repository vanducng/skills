# Auth strategies

Three strategies cover local web apps. The config's `auth.strategy` picks one; each defines what to do when `status` reports `logged-out`.

## oauth-interactive

For apps whose only login is an external IdP (Google/Microsoft OAuth, SSO) — password login disabled, bot-challenged consent screens make scripting the IdP a dead end. The persistent profile **is** the auth mechanism.

- **Recover from logged-out:** run `profile-open.sh <profile>` yourself, then ask the human (once) to complete the login in the opened window. Re-run `status` to confirm. Never script the IdP form.
- **Why it stays logged in:** apps that call `Auth::login($user, true)` (Laravel) set a remember-me cookie measured in months; the profile keeps it plus the IdP session.
- **`loginUrlPattern` must include the IdP origin** — a logged-out probe lands on `accounts.google.com`, not your app's `/login`:

```json
"loginUrlPattern": "/login|accounts\\.google\\.com"
```

- 2FA/TOTP on the test account: keep the secret in gopass (`gopass show -o <path>/totp`) so the one-time login stays one prompt.

## form

For apps with a scriptable login form and deterministic dev-seeded users (the seeded creds are usually public in the repo's README/seeders — that's the only case `credentials.source: "inline"` is acceptable; otherwise `"gopass"` or `"env"`).

```bash
BP=$HOME/.claude/skills/browser-profile/scripts
"$BP/profile-attach.sh" <profile>
browse open http://localhost:8082/login
browse snapshot
browse fill <email-ref> "admin@example.com" --no-press-enter
browse fill <password-ref> "dev-seeded-only"      # Enter on the last field submits
sleep 2 && browse get url                          # guard: landed past the login route
```

`browse fill` **presses Enter by default** — without `--no-press-enter` on the email field you submit a half-filled form. Fill the password last.

## token-inject

For SPA + token APIs (JWT in localStorage). Fastest and fully deterministic — but do it **in-page**, not by writing localStorage alone:

```bash
browse eval "fetch('/api/v1/auth/login', {
  method: 'POST',
  credentials: 'include',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({email: 'admin@example.com', password: 'dev-seeded-only'})
}).then(r => r.json()).then(d => { localStorage.setItem('hi-token', d.token); return 'ok'; })"
browse open http://localhost:8082/
```

- The in-page `fetch` with `credentials: 'include'` lets the browser apply `Set-Cookie` natively — including **httpOnly** cookies that `document.cookie`/localStorage injection can never set. Skipping this leaves half-authenticated state for any endpoint that reads the cookie.
- **Always re-inject at the start of every run** — short-lived JWTs (8h is common) pass URL-based probes (guards check token *presence*) while being expired. That's why `status` skips probing for this strategy and reports `inject-required`.
- CSP: CDP `Runtime.evaluate` (what `browse eval` uses) is not subject to page CSP; the in-page `fetch` is subject to `connect-src`, which same-origin calls satisfy.
- The probe page must be loaded on the app origin before `localStorage.setItem` — localStorage is origin-scoped. Same reason the config standardizes ONE origin (the prod-like reverse-proxy port beats the Vite dev port: same-origin cookies work there).
