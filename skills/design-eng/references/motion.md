# Motion

Easing, springs, entry, blur, and stagger. The decision order is in `SKILL.md`.

## Custom curves

```css
--ease-out: cubic-bezier(0.23, 1, 0.32, 1);
--ease-in-out: cubic-bezier(0.77, 0, 0.175, 1);
--ease-drawer: cubic-bezier(0.32, 0.72, 0, 1);
```

`ease-in` starts slow. A dropdown with `ease-in` at 300ms feels slower than `ease-out` at the same 300ms, because the delay hits the frame the user is watching.

## Springs

Use springs for drag with momentum, gestures that can reverse mid-way, and decorative pointer tracking. CSS keyframes restart from zero when interrupted. A spring keeps its velocity.

Apple-style config is easier to reason about:

```js
{ type: "spring", duration: 0.5, bounce: 0.2 }
```

Physics config when you need it:

```js
{ type: "spring", mass: 1, stiffness: 100, damping: 10 }
```

Decorative pointer motion should go through `useSpring` (Motion or `framer-motion`, matching the package the file already imports). Writing `mouseX * 0.1` straight into a transform feels glued to the cursor.

```jsx
const springRotation = useSpring(mouseX * 0.1, {
  stiffness: 100,
  damping: 10,
});
```

Skip that on a functional chart. Decoration there makes the data harder to read.

## Perceived speed

- A faster spinner makes the same load feel faster.
- A 180ms select feels more responsive than a 400ms one.
- Once one tooltip is open, the next tooltip in the group is instant.

## Do not enter from scale(0)

```css
.entering {
  transform: scale(0.95);
  opacity: 0;
}
```

## Interruptible UI uses transitions

Toasts, toggles, and anything the user can retrigger need a transition, not a keyframe. Keyframes restart. Transitions retarget.

```css
.toast {
  transition: transform 400ms ease;
}
```

## Blur masks a bad crossfade

When two states overlap and still look like two objects, add `filter: blur(2px)` during the blend. Keep it under 20px. Heavy blur is expensive in Safari.

This is a mask between two states. Icon swaps use the `4px` blur in `vd:better-ui`, not this one.

## @starting-style

Prefer this over a `useEffect` that flips `mounted` after the first paint, when the browsers you support allow it.

```css
.toast {
  opacity: 1;
  transform: translateY(0);
  transition: opacity 400ms ease, transform 400ms ease;

  @starting-style {
    opacity: 0;
    transform: translateY(100%);
  }
}
```

Otherwise set `data-mounted` after mount and transition from the unmounted style.

## Asymmetric press and release

The press can be slow when the slowness is the decision. The release is always snappy.

```css
.overlay {
  transition: clip-path 200ms ease-out;
}

.button:active .overlay {
  transition: clip-path 2s linear;
}
```

## List stagger

30-80ms between items. Longer than that and the list feels late. Stagger is decorative. Do not block clicks while it runs. A page hero that staggers in chunks uses ~100ms from `vd:better-ui`, not this delay.

## Cohesion

Match the motion to the component. A playful control can bounce. A dense dashboard should be short and ease-out. Sonner is slightly slower than typical UI and uses `ease` instead of `ease-out` because the whole library is that quiet. Copy the mood, not the brand.

## Debugging

Play the motion at 2-5x duration, or in the browser Animations panel at low speed. Check that colors do not show two objects at once, that the origin is the trigger, and that opacity and transform finish together. For a drawer or swipe, test on a phone. The simulator is a fallback.
