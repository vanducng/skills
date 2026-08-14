# Fact-check rules

Fact-check is a **read of public pages the resume already pointed to**. It is not sourcing, not Recruiter, and not a request that the candidate prove documents.

## Extract, then open

From the resume text (and only from the resume text), collect:

- LinkedIn profile URL
- GitHub user or repo URLs
- Portfolio / personal site
- Certificate or badge URLs (Credly, Databricks credentials, Snowflake achieve, Acclaim, vendor cert portals)

Open those URLs. Use a browser if the page needs one; otherwise fetch the public page. **Never construct a LinkedIn slug, GitHub handle, or badge URL from the candidate's name.**

If the resume has no URL for a channel, leave that column empty and treat that channel as unseen.

## Verdicts

| `Fact_check` | Meaning | Typical `FactIntegrity_10` |
|---|---|---|
| `Verified` | Public page(s) match employer, title, dates, and stack on the material claims | 9–10 |
| `Partial` | At least one solid match (e.g. GitHub shows the claimed stack; LinkedIn matches employers) but another channel is missing or thin | 6–8 |
| `Unverified` | No usable public page, or pages exist but show too little to confirm | 3–5 |
| `Contradicted` | A public page **disagrees** on employer, title, dates, or stack in a way that is not a naming variant | 0 + Layer 1 knockout #5 |

Naming variants ("Acme Inc." vs "Acme") and month-level date fuzz are `Soft mismatch` on `Timeline_consistency`, not `Contradicted`.

`Timeline_consistency`: `Holds` | `Soft mismatch` | `Breaks`. `Breaks` plus a material employer/title/date/stack clash → `Contradicted`.

## Certificates

| Evidence | `Certs_verified` | Notes |
|---|---|---|
| Working badge URL (Credly, Databricks credentials, Snowflake achieve, etc.) that loads and names this person / this cert | List the cert + the URL | |
| Clearly listed on **that person's** LinkedIn Licenses & certifications | List the cert + the LinkedIn URL | |
| Named on the resume with no public proof | — | Put it in `Certs_unverified` |
| LinkedIn profile loads but Licenses is empty or hidden | — | **Not a contradiction.** Public LinkedIn often hides licenses |

`Certs_claimed` is the resume's list, verbatim enough to recognize. `Cert_notes` explains the gap.

**Never ask the candidate to show a cert ID or badge.** If they claimed SnowPro / AWS / Databricks with no public proof, write a *technical* probe instead, for example:

- Snowflake: roles vs warehouses vs clones in a dbt promotion path; Time Travel vs Fail-safe; what breaks if a warehouse is suspended mid-query
- Databricks: Delta `OPTIMIZE` / `ZORDER` vs liquid clustering; when a job cluster beats an all-purpose cluster
- AWS: IAM role vs user for a Lambda that writes to S3; what CloudWatch shows when a timeout is a VPC/ENI issue

Put that probe in `Cert_notes` and, if the row is P1/P2/waiver, in `Screen_questions`.

## What is not a contradiction

- No LinkedIn URL on the resume
- LinkedIn exists but Licenses is hidden
- GitHub is empty or private (that is Unverified / Partial, and it may lower `Extras_10` or `Pipelines_25` if the resume leaned on those repos)
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

Those belong to HR. `Location_10` and knockout #4 already captured what the *resume* said.
