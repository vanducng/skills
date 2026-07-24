---
name: copywriting
description: "Conversion copywriting formulas, headline templates, email copy patterns, landing page structures, CTA optimization, and writing style extraction. Use for high-converting copy, headlines, email campaigns, landing pages, social posts, product copy, CTA variants, or applying custom writing styles from an assets/writing-styles directory."
category: utilities
keywords: [copy, headlines, email, landing-page]
license: MIT
argument-hint: "[copy-type] [context]"
metadata:
  author: vanducng
  version: "1.0.0"
---

# Copywriting

Formulas, templates, patterns, and writing styles for high-converting copy.

## When to Use

- Writing headlines/subject lines, landing page copy, email campaigns
- Social posts, product descriptions, CTA optimization, A/B variations
- Applying custom writing styles from user documents

## Writing Styles

Load: `references/*.md` | Optional project catalog: `assets/writing-styles/`

**Extract styles from multi-format files:**
```bash
python3 <copywriting-skill-dir>/scripts/extract-writing-styles.py --list         # List files
python3 <copywriting-skill-dir>/scripts/extract-writing-styles.py --style <name> # Extract style
```

Set `COPYWRITING_STYLES_DIR=/path/to/writing-styles` to override discovery.

**Formats:** `.md` `.txt` `.pdf` `.docx` `.xlsx` `.pptx` `.jpg` `.png` `.mp4` (docs/media need `GEMINI_API_KEY`)

## Copy Formulas

Load: `references/copy-formulas.md`

| Formula | Structure | Best For |
|---------|-----------|----------|
| AIDA | Attention → Interest → Desire → Action | Landing pages, ads |
| PAS | Problem → Agitate → Solution | Email, sales pages |
| BAB | Before → After → Bridge | Testimonials, case studies |
| 4Ps | Promise → Picture → Proof → Push | Long-form sales |
| 4Us | Urgent + Unique + Useful + Ultra-specific | Headlines |
| FAB | Feature → Advantage → Benefit | Product descriptions |

## Headlines

Load: `references/headline-templates.md`

Patterns: "How to [X] without [Y]" • "[Number] ways to [benefit]" • "The secret to [outcome]" • "Why [belief] is wrong"

## Email Copy

Load: `references/email-copy.md`

Subject lines: Curiosity gap • Benefit-driven • Question • Urgency

## Landing Pages & CTAs

Load: `references/landing-page-copy.md` | `references/cta-patterns.md`

Hero: Headline (promise) → Subheadline (how) → CTA (action) → Social proof
CTAs: "Start [verb]ing" • "Get [benefit]" • "Yes, I want [benefit]"

## Workflows

| Workflow | Purpose | Use When |
|----------|---------|----------|
| `references/workflow-cro.md` | CRO optimization (25 principles) + plan creation workflow | Conversion optimization & CRO plan requests |
| `references/workflow-enhance.md` | Copy enhancement | Improving existing copy |
| `references/workflow-fast.md` | Quick copy generation | Simple, time-sensitive requests |
| `references/workflow-good.md` | Quality copy with research | High-stakes content |

## References

| File | Purpose |
|------|---------|
| `references/writing-styles.md` | 30 writing styles quick reference |
| `references/copy-formulas.md` | AIDA, PAS, BAB, 4Ps, FAB formulas |
| `references/headline-templates.md` | Headline patterns & templates |
| `references/email-copy.md` | Email copy patterns |
| `references/landing-page-copy.md` | Landing page structure |
| `references/cta-patterns.md` | CTA optimization |
| `references/power-words.md` | Power words by emotion |
| `references/social-media-copy.md` | Platform-specific copy |
| `scripts/extract-writing-styles.py` | Extract styles from multi-format files |
| `templates/copy-brief.md` | Creative brief template |

## Related Skills

Use `vd:opendesign` for rendered landing pages, email mockups, and visual artifacts.
Use `vd:marketing-design` for brand assets and social images.
Use `vd:devlog` for build-in-public engineering posts.

## Best Practices

1. Lead with benefit, not feature | 2. One CTA per piece
3. Specificity > vague claims | 4. Read aloud - if awkward, rewrite
5. Test headlines first | 6. Match copy to awareness level

## Outputs

Write copy into the current project's natural artifact location. If no convention
exists, use `artifacts/copywriting/<slug>.md` and include the brief, selected
formula, final copy, and optional variants.
