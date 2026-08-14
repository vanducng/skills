# Fact-check rules

Fact-check is a **read of pages the resume already pointed to**. It is not sourcing, not Recruiter, not Drive, and not a request that the candidate prove documents.

This skill does **not** implement a browser. It does **not** invent a third driver. It composes the two catalog browsers that already live in this repo, by name:

| Prefer | Catalog id | Lives at |
|---|---|---|
| 1 | `vd:ego-browser` | `skills/ego-browser/` |
| 2 | `vd:browser-profile` + `vd:agent-browser` | `skills/browser-profile/`, `skills/agent-browser/` |

Load that sibling `SKILL.md` before the first command. Hard rules below are copied from those skills — follow them; do not paraphrase them away.

`vd:browser` (Browserbase, `skills/browser/`) is **not** a third driver. Use it only if LinkedIn/GitHub anti-bot blocks the local profile. `vd:browser-trace` is optional read-only evidence on the same CDP port, not a driver.

## Extract, then open

From the resume text (and only from the resume text), collect:

- LinkedIn profile URL
- GitHub user or repo URLs
- Portfolio / personal site
- Blog / writing URLs
- Certificate or badge URLs (Credly, Databricks credentials, Snowflake achieve, Acclaim, vendor cert portals)

**Never invent a URL.** Never construct a LinkedIn slug, GitHub handle, blog, or badge URL from the candidate's name. If the resume has no URL for a channel, leave that column empty and treat that channel as unseen.

Open only extracted URLs. Record the verdict **with the source URL you actually opened**.

---

## Prefer `vd:ego-browser` (`skills/ego-browser/`)

Use when ego lite / the `ego-browser` CLI is available. An isolated task space inherits the operator's login (LinkedIn, GitHub).

Hard rules from that skill:

- Run as `ego-browser nodejs <<'EOF' ... EOF` (or a temp file if the worktree guard rejects heredocs). Do not import Playwright or launch another browser.
- One Bash invocation for the whole profile scan when possible. `taskSpaces.useOrCreate('screen <candidate> linkedin')` once; reuse that `task.id`.
- `browser.openOrReuseTab(url)` for each extracted URL (LinkedIn, GitHub, portfolio, blog). Never invent a URL.
- Prefer a stable profile URL over clicking through search UI.
- If login / captcha / SSO: `taskSpaces.handOff`, tell the operator what to do, wait for explicit confirmation, then `takeOver`. Do not `takeOver` automatically. Do not ask for passwords.
- After the scan, print JSON evidence (jobs, dates, licenses, GitHub repos). Do **not** `taskSpaces.complete(..., { keep: false })` until the operator confirms closing that space.
- Read `$HOME/.local/share/ego/ego-skills/SKILL.md` if helper names differ.

If the first real `ego-browser` command fails because the CLI is missing, fall through to `vd:agent-browser` + `vd:browser-profile`. Do not install a browser stack as part of this skill.

---

## Else `vd:agent-browser` + `vd:browser-profile`

Use when `vd:ego-browser` is not available and a persistent logged-in Chrome profile exists (`--browser-profile <name>`, e.g. `linkedin-work`).

Hard rules from those skills:

- Attach with `profile-attach.sh <name>` from `vd:browser-profile` (canonical). Never `agent-browser --profile` for this — that launches a separate Playwright browser with no shared login.
- Always `env -u AGENT_BROWSER_PROFILE` (or the attach wrapper). Then `eval 'navigator.userAgent'` must **not** contain `HeadlessChrome`. If it does, stop; you are on the wrong browser.
- Drive LinkedIn/GitHub with `open`, `snapshot -i`, `get text`, semantic `find`. After SPA nav, assert `get url` (do not trust `wait --url`).
- Confirm the profile identity with the operator if not already pinned (e.g. a `linkedin-work` profile). Wrong-account actions are hard to undo.
- Teardown: if **you** opened the profile Chrome, `profile-close.sh`. If you attached to a Chrome the human already had open, do **not** close their window — `agent-browser close` only.
- Screenshot paths must be positional and absolute. Never `har start <path>`.
- `vd:browser` (Browserbase) only if LinkedIn/GitHub anti-bot blocks the local profile.

```bash
# Resolve scripts from the vd:browser-profile skill root. No machine-specific path.
profile-attach.sh <name>    # env-sanitized connect + UA check
env -u AGENT_BROWSER_PROFILE agent-browser eval 'navigator.userAgent'
# must NOT contain HeadlessChrome
env -u AGENT_BROWSER_PROFILE agent-browser open "<extracted-url>"
env -u AGENT_BROWSER_PROFILE agent-browser snapshot -i
env -u AGENT_BROWSER_PROFILE agent-browser get url
```

---

## Public fetch still OK

Credly / `credentials.databricks.com` / `achieve.snowflake.com` badge URLs: HTTP fetch, no login. Verified only if the page loads and names this person / this cert. A 404 or a generic marketing page is Unverified, not a contradiction.

---

## If neither browser skill is runnable

Public fetch only. Mark login-walled LinkedIn as `Unverified`. Do not invent profile content. Do not ask the operator to paste a password. Tell them they can re-run with ego lite or a logged-in `--browser-profile <name>`.

---

## What to read on the live page

| Source | Read | Record |
|---|---|---|
| LinkedIn | Headline, current/past jobs (employer, title, dates), Licenses & Certifications | Match vs resume. Licenses hidden/empty → not a contradiction |
| GitHub | Pinned/recent repos, languages, last-commit recency, README claims | Stack and activity vs resume. Empty/private → Unverified/Partial, not Contradicted |
| Portfolio | Project list, dates, stack, employer names if present | Same comparison |
| Blog | Posts that support (or undermine) claimed expertise | Recency and topic vs resume; absence of a blog URL is unseen |
| Badge URL | Cert name, holder name, issue/expiry, issuer | Verified only if it loads and matches |

Compare employer, title, dates, and stack. Naming variants ("Acme Inc." vs "Acme") and month-level date fuzz are `Soft mismatch` on `Timeline_consistency`, not `Contradicted`.

## Verdicts

| `Fact_check` | Meaning | Typical `FactIntegrity_10` |
|---|---|---|
| `Verified` | Opened page(s) match employer, title, dates, and stack on the material claims | 9–10 |
| `Partial` | At least one solid match (e.g. GitHub shows the claimed stack; LinkedIn matches employers) but another channel is missing, thin, or login-walled | 6–8 |
| `Unverified` | No usable page, login wall without a session, or pages show too little to confirm | 3–5 |
| `Contradicted` | An opened page **disagrees** on employer, title, dates, or stack in a way that is not a naming variant | 0 + Layer 1 knockout #5 |

`Timeline_consistency`: `Holds` | `Soft mismatch` | `Breaks`. `Breaks` plus a material employer/title/date/stack clash → `Contradicted`.

A login wall is Unverified. A loaded LinkedIn that lists a different employer for the same dates is Contradicted.

Put the source URL next to the evidence (`Certs_verified`, `Notes`, or the LinkedIn/GitHub/Portfolio columns). Never write a URL you did not extract and open. Never invent profile content to fill a login wall.

## Certificates

| Evidence | `Certs_verified` | Notes |
|---|---|---|
| Working badge URL (Credly, Databricks credentials, Snowflake achieve, etc.) that loads and names this person / this cert | List the cert + the URL | HTTP fetch — no login |
| Clearly listed on **that person's** LinkedIn Licenses & certifications (logged-in read counts) | List the cert + the LinkedIn URL | |
| Named on the resume with no public proof | — | Put it in `Certs_unverified` |
| LinkedIn profile loads but Licenses is empty or hidden | — | **Not a contradiction.** Public and even logged-in LinkedIn often hide licenses |

`Certs_claimed` is the resume's list, verbatim enough to recognize. `Cert_notes` explains the gap.

**Never ask the candidate — or the operator — to show a cert ID or badge.** If they claimed SnowPro / AWS / Databricks with no public proof, write a *technical* probe instead, for example:

- Snowflake: roles vs warehouses vs clones in a dbt promotion path; Time Travel vs Fail-safe; what breaks if a warehouse is suspended mid-query
- Databricks: Delta `OPTIMIZE` / `ZORDER` vs liquid clustering; when a job cluster beats an all-purpose cluster
- AWS: IAM role vs user for a Lambda that writes to S3; what CloudWatch shows when a timeout is a VPC/ENI issue

Put that probe in `Cert_notes` and, if the row is P1/P2/waiver, in `Screen_questions`.

## What is not a contradiction

- No LinkedIn URL on the resume
- LinkedIn exists but Licenses is hidden
- LinkedIn (or another page) is login-walled and no browser session was available
- GitHub is empty or private (Unverified / Partial; may lower `Extras_10` or `Pipelines_25` if the resume leaned on those repos)
- A cert claimed without a badge
- Title flavor ("Data Engineer" vs "Software Engineer, Data") when the employer and dates match and the work reads the same

## What is a contradiction (knockout #5)

- LinkedIn current/past employer does not include a resume employer for the same dates (not a subsidiary rename)
- LinkedIn title for those dates is a different occupation (e.g. SWE / support / analyst) while the resume rewrites it as data/platform engineering
- GitHub activity or pinned work is a different stack than the one the resume treats as core, in a way that cannot be "also used X"
- Dates on LinkedIn make a claimed tenure impossible

A resume mill (same stack paragraph on every job, bullets that read like the JD) is `Claim_feasibility=Stretched` and usually `Startup_fit=Low`. It is **not** automatic `Contradicted` unless the employers or titles fail the checks above.

## Screen questions — keep HR out

`Screen_questions` is a meeting list for P1, P2, and waiver rows only (3–5 items). Allowed: architecture, debugging, ownership, tradeoffs, claimed stack depth.

Never include:

- Hybrid / onsite / relocation
- Timezone or working hours
- Salary, band, or "would you take $X"
- Visa / work authorization
- "Please send cert IDs"
- "Paste your LinkedIn password" / any credential request

Those belong to HR (or are forbidden). `Location_10` and knockout #4 already captured what the *resume* said.
