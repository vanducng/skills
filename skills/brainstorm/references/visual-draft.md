# Visual draft mode

A lightweight interactive layer for the subset of brainstorm questions where the user would understand a *picture* faster than a paragraph. Static HTML opened in the browser - no server, no event polling, no session state. Borrows the wireframe CSS vocabulary, drops the runtime machinery.

## When to use

**Yes** - the *content itself* is visual:
- "Which dashboard layout?" (sidebar vs topbar vs split)
- "Which signup flow shape?" (single-page vs wizard vs progressive disclosure)
- "Which card layout for the feed?"
- Side-by-side visual comparisons of two interface directions

**No** - text decisions dressed up as visuals:
- "Which auth strategy / database / message queue?" - text comparison table
- "What does 'success' mean here?" - clarifying question
- Anything in the data-engineering / devops / analytics disciplines - those decisions are text comparisons

If you can express the decision as A/B/C bullet points without losing fidelity, skip the visual draft. A question *about* a UI topic isn't automatically a visual question.

## Where to save (standardized artifact directory)

Use the active plan context (injected by session hooks) - **do not invent new directories**, especially not under hidden dotdirs:

- **Plan active:** `{plan_dir}/visuals/brainstorm-{slug}/comparison-{N}.html`
- **No plan:** write to the injected `Visuals:` path. Subdir: `brainstorm-{YYYYMMDD-HHMM}-{slug}/comparison-{N}.html`.

Increment `{N}` per iteration: `comparison-1.html`, `comparison-2.html`. Never overwrite - the trail of drafts is part of the brainstorm record.

## How to render

1. Read the bundled template at `<this-skill-dir>/assets/comparison-template.html`.
2. Copy it to the target path above. Fill the three placeholders:
   - `{{TITLE}}` - the visual question, e.g. "Which dashboard layout?"
   - `{{SUBTITLE}}` - one-sentence framing
   - `{{PANELS}}` - your A/B/C panel HTML, using ONLY the classes documented below
3. `open <path>` (macOS) / `xdg-open <path>` (Linux) to launch in the user's default browser.
4. Tell the user where to open the draft using an openable location, not just the basename:
   *"Visual draft at `[comparison-1.html](/absolute/path/to/comparison-1.html)` (`file:///absolute/path/to/comparison-1.html`). Take a look and reply with the letter you prefer - or describe what's off."*

## CSS vocabulary in the template

Use these classes - don't invent more, don't write inline styles:

| Class | Use for |
|---|---|
| `.options` + `.option[data-choice]` + `.letter` + `.content` | A/B/C lettered cards (conceptual choices) |
| `.cards` + `.card` + `.card-image` + `.card-body` | Richer cards with mockup bodies (visual designs) |
| `.mockup` + `.mockup-header` + `.mockup-body` | Wrapped wireframe (browser-chrome frame) |
| `.split` | Side-by-side mockup pair |
| `.pros-cons` + `.pros` / `.cons` | Tradeoff lists per option |
| `.mock-nav`, `.mock-sidebar`, `.mock-content` | Wireframe layout primitives |
| `.mock-button`, `.mock-input`, `.placeholder` | Wireframe element primitives |

The template handles theme tokens, dark-mode, responsive grid, and a cosmetic click-to-highlight (no event logging - the user replies in chat).

## Iteration

If the user requests changes after seeing the draft, write a **new file** (`comparison-2.html`) - don't overwrite. The diff between iterations is itself useful, and lets the brief reference "we considered layout v1 and rejected it because…".

## Handoff after pick

Once the user picks a direction, the visual draft has served its purpose - it bought a converging decision before any artifact got polished. After the brief is approved (Phase 6), point the user at the right specialist for the *final* artifact:

| Pick shape | Hand off to |
|---|---|
| Polished UI page (landing, dashboard, marketing) | `vd:opendesign` |
| Rendered system / data-flow / sequence diagram | `vd:diagram` |
| Editable whiteboard / architecture sketch | `vd:excalidraw` |

The brainstorm's job is to pick the direction. Materializing it is downstream.
