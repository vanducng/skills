# Fact-check rules

Fact-check is a **read of pages the resume already pointed to**. It is not sourcing, not Recruiter, not Drive, and not a request that the candidate prove documents.

This skill does **not** implement a browser. It composes catalog skills. Load the chosen skill's `SKILL.md` and follow that skill's contract (task spaces, attach, teardown). Canonical IDs: `vd:ego-browser`, `vd:browser-profile`, `vd:agent-browser`, `vd:browser-trace`, `vd:browser`.

## Extract, then open

From the resume text (and only from the resume text), collect:

- LinkedIn profile URL
- GitHub user or repo URLs
- Portfolio / personal site
- Blog / writing URLs
- Certificate or badge URLs (Credly, Databricks credentials, Snowflake achieve, Acclaim, vendor cert portals)

**Never construct a LinkedIn slug, GitHub handle, blog, or badge URL from the candidate's name.** If the resume has no URL for a channel, leave that column empty and treat that channel as unseen.

Open only extracted URLs. Record the verdict **with the source URL you actually opened**.

## Transport ladder

Pick the first row that applies. Do not skip down to Browserbase because it feels easier.

| Order | Use when | Load | Do | Do not |
|---|---|---|---|---|
| 1 | `ego-browser` is on `PATH`, or `$HOME/.local/share/ego/ego-skills/SKILL.md` exists (ego lite runtime) | `vd:ego-browser` | Isolated task space; reuse the user's login; open each extracted URL; read the live page | Write a `.js` file under the skill; import Playwright; close the space without asking |
| 2 | Else, operator passed `--browser-profile <name>` or already has that Chrome open | `vd:browser-profile` then `vd:agent-browser` | `profile-attach.sh <name>` (connect + UA check). Drive with `agent-browser` **connect** mode. Optional `vd:browser-trace` on the same deterministic port | `agent-browser --profile` — that launches a separate Playwright browser with **no** saved logins |
| 3 | URL host is a public badge page | Plain HTTP fetch | `curl` / `fetch` Credly, `credentials.databricks.com`, `achieve.snowflake.com` (and similar badge hosts) | Open a browser just to load a public badge |
| 4 | Local logged-in Chrome hits CAPTCHA, Cloudflare, empty anti-bot, or 403/429 on LinkedIn/GitHub | `vd:browser` | Escalate **that URL only** to Browserbase cloud | Use Browserbase as the default driver; use it for file transfer |
| 5 | No browser skill is available | Public fetch | Fetch what is public. If LinkedIn (or another page) is login-walled, mark that channel `Unverified` and say so | Ask the operator to paste a password; invent a session |

If ego-browser's first real command fails because the CLI is missing, fall through to row 2, then 5. Do not install a browser stack as part of this skill.

### Row 1 — `vd:ego-browser`

Read `vd:ego-browser` before the first command. One task space for the whole screen (`resume-screen fact-check`). `taskSpaces.useOrCreate` once; reuse that `task.id`. One Bash invocation should open the extracted URLs, read them, and print structured evidence.

Follow that skill's lifecycle: do not call `taskSpaces.complete` in the scan invocation. After the workbook is written, ask whether to close the ego space. Silence is not confirmation. Never close a user-owned space.

Hand off only if LinkedIn/GitHub presents a captcha or a login the session does not already have — then tell the operator what to do in *their* window. Do not ask for a password. Resume after they confirm.

### Row 2 — `vd:browser-profile` + `vd:agent-browser` connect

The operator logs into LinkedIn and GitHub **once** in a named Chrome (`vd:browser-profile`). Login survives across runs. This skill only attaches.

```bash
# Resolve the browser-profile scripts dir the same way that skill does
# (skill root / scripts). Do not hardcode a machine-specific path.
profile-list.sh                              # confirm <name> exists
# If Chrome is not open: profile-open.sh <name>
# Then ask the operator to confirm they are logged into LinkedIn/GitHub
# in that window. Never ask for a password.
profile-attach.sh <name>                     # env-sanitized connect + UA check
# UA must NOT contain HeadlessChrome — if it does, stop (wrong browser)
```

Then drive **that** Chrome:

```bash
env -u AGENT_BROWSER_PROFILE agent-browser open "<extracted-url>"
env -u AGENT_BROWSER_PROFILE agent-browser snapshot -i
# read jobs / dates / Licenses, or GitHub repos / languages / recency
```

`profile-attach.sh` is the only sanctioned attach. A shell-rc `AGENT_BROWSER_PROFILE` silently redirects successful commands at a Playwright browser with empty cookies — that is why every call is `env -u AGENT_BROWSER_PROFILE`.

**Never** `agent-browser --profile …` for fact-check. That flag launches a separate Playwright-owned browser. It does not share the operator's LinkedIn/GitHub cookies.

Optional evidence: `vd:browser-trace` as a second CDP client on the profile's deterministic port (see `vd:browser-profile` — `9300 + cksum(name) % 100`). Write traces under the injected `Reports:` path when present. Trace does not drive the page.

Teardown (from `vd:agent-browser`): if **you** opened the profile Chrome, `profile-close.sh <name>` when the screen is done. If the operator already had it open, do not close their window — `agent-browser close` to drop the daemon session only.

### Row 3 — public badge fetch

No login. `GET` the extracted badge URL. Verified only if the page loads and names this person / this cert. A 404 or a generic marketing page is Unverified, not a contradiction.

### Row 4 — Browserbase escalation

Load `vd:browser`. Use it only after the local logged-in profile is blocked by anti-bot on LinkedIn or GitHub. Still open only extracted URLs. Still no Drive, no Recruiter search.

### Row 5 — no browser

Public `GET`. GitHub user pages and badge URLs often work. LinkedIn almost always login-walls anonymous fetch — that is `Unverified` for the LinkedIn channel, **not** `Contradicted`. Tell the operator they can re-run with ego lite or a logged-in `--browser-profile <name>`. Do not collect a password.

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

Put the source URL next to the evidence (`Certs_verified`, `Notes`, or the LinkedIn/GitHub/Portfolio columns). Never write a URL you did not extract and open.

## Certificates

| Evidence | `Certs_verified` | Notes |
|---|---|---|
| Working badge URL (Credly, Databricks credentials, Snowflake achieve, etc.) that loads and names this person / this cert | List the cert + the URL | Prefer HTTP fetch (row 3) |
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
