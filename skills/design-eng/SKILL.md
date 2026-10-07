---
name: design-eng
description: "Decides whether UI motion should exist, then picks easing, duration, origin, and gesture behavior. Covers frequency limits, springs, popover origin, tooltips, clip-path reveals, drag dismissal, and reduced motion. Activates when adding a transition, popover, drawer, toast, or drag gesture, or when the user says 'design engineering', 'should this animate', 'easing', 'spring', 'popover origin', or 'emil'. Do not use for concentric radius, surface shadows, the 0.96 press scale, or icon cross-fades - that is vd:better-ui. Do not use for design-system choice, page implementation, or accessibility audits - that is vd:uiuxdesign."
license: MIT
metadata:
  author: vanducng
  version: "1.0.0"
  upstream: emilkowalski/skills@emil-design-eng
---

# Design engineering

> Motion decisions from Emil Kowalski's design-engineering notes (MIT). Unseen details compound. Keyboard actions never animate.

Do the task. Do not open with a philosophy recap.

## What this skill is, and is not

| This skill | Not this skill |
| --- | --- |
| Should this animate, and with which easing, duration, and origin | Exact polish numbers (`vd:better-ui`) |
| Popovers, tooltips, toasts, drawers, clip-path, drag | Design-system choice, tokens, page build (`vd:uiuxdesign`) |
| A Before / After / Why review table | Posting that table on a PR (`vd:code-review`) |

When `vd:better-ui` already names an exact value, use that value.

| Interaction | Use |
| --- | --- |
| Press scale | `0.96` from `vd:better-ui`, not `0.97` |
| Icon cross-fade | scale `0.25`, blur `4px`, bounce `0` from `vd:better-ui` |
| Page-level stagger | ~100ms from `vd:better-ui` |
| List stagger | 30-80ms, in [motion.md](references/motion.md) |
| Crossfade mask | `blur(2px)` here, not the icon blur |

## Hard rules

1. Answer "should this animate?" before writing a curve. Frequency decides. A keyboard shortcut or command palette never animates.
2. Never use `ease-in` on UI. It delays the first frame, which is the moment the user is watching. Never use `transition: all`.
3. Never enter from `scale(0)`. Start at `scale(0.95)` or higher, with opacity.
4. Popovers scale from the trigger. Modals stay `transform-origin: center`.
5. UI motion stays under 300ms. A deliberate hold (hold-to-delete) is the exception, and its release is still fast.
6. Animate `transform` and `opacity`. Reduced motion keeps opacity and color, and drops movement.

## Decision framework

Answer in order. Recipes live in [motion.md](references/motion.md), [components.md](references/components.md), [techniques.md](references/techniques.md), and [performance.md](references/performance.md).

### 1. Should this animate at all?

| Frequency | Decision |
| --- | --- |
| 100+ times/day (keyboard shortcuts, command palette) | No animation |
| Tens of times/day (hover, list navigation) | Remove it, or cut it to almost nothing |
| Occasional (modals, drawers, toasts) | Standard animation |
| Rare or first-time (onboarding, celebration) | Delight is allowed |

Raycast opens and closes with no animation. That is the right call for something used hundreds of times a day.

### 2. What is the purpose?

Valid purposes: spatial consistency, state indication, explanation, feedback, or hiding a jump. "It looks cool" is not a purpose when the user will see it often.

### 3. What easing?

| Situation | Easing |
| --- | --- |
| Entering or exiting | ease-out. Custom: `cubic-bezier(0.23, 1, 0.32, 1)` |
| Moving or morphing on screen | ease-in-out. Custom: `cubic-bezier(0.77, 0, 0.175, 1)` |
| Hover or color | `ease` |
| Constant motion (marquee, progress) | `linear` |
| Drawer | `cubic-bezier(0.32, 0.72, 0, 1)` |
| Anything else | ease-out |

Built-in CSS easings are too weak. Pick a stronger curve from [easing.dev](https://easing.dev/) or [easings.co](https://easings.co/). Do not invent one.

### 4. How fast?

| Element | Duration |
| --- | --- |
| Button press | 100-160ms |
| Tooltips, small popovers | 125-200ms |
| Dropdowns, selects | 150-250ms |
| Modals, drawers | 200-500ms, and still prefer under 300ms for the UI part |
| Marketing or explanation | Longer is allowed |

A faster spinner makes the same load feel faster. After the first tooltip is open, later tooltips in that group are instant: no delay, no animation.

Springs are for drag, gestures that get interrupted, and decorative mouse-tracking. Not for a banking chart. Prefer `{ type: "spring", duration: 0.5, bounce: 0.2 }`. Keep bounce in `0.1-0.3` when you use it. Most UI gets bounce `0`.

## Review format

One markdown table. One row per issue. Never a stack of "Before:" / "After:" lines.

| Before | After | Why |
| --- | --- | --- |
| `transition: all 300ms` | `transition: transform 200ms ease-out` | Name the properties |
| `transform: scale(0)` | `transform: scale(0.95); opacity: 0` | Nothing appears from nothing |
| `ease-in` on a dropdown | custom ease-out | `ease-in` feels late |
| No `:active` scale | press scale from `vd:better-ui` (`0.96`) | The control has to answer the press |
| `transform-origin: center` on a popover | `var(--transform-origin)` | Scale from the trigger. Modals stay centered |

## Checklist

| Issue | Fix |
| --- | --- |
| `transition: all` | Name the properties |
| `scale(0)` entrance | `scale(0.95)` plus opacity `0` |
| `ease-in` on UI | ease-out or the custom curve above |
| Popover origin centered | Trigger origin. Modals stay centered |
| Animation on a keyboard action | Remove it |
| UI duration over 300ms | 150-250ms, unless the slowness is the decision (hold-to-delete) |
| Hover motion with no pointer query | `@media (hover: hover) and (pointer: fine)` |
| Keyframes on something triggered rapidly | CSS transition, so it can reverse mid-way |
| Framer Motion `x` / `y` while the page is loading | `transform: "translateX()"` so it stays on the compositor |
| Enter and exit share one duration | Exit faster. Release is the snappy half |
| A group appears in one frame | Stagger 30-80ms. Do not block input while it plays |
