# Components

Press, popovers, tooltips, and the rules that made Sonner feel finished.

## Press

Every pressable control needs an `:active` scale. The number is `0.96` from `vd:better-ui`, on `transform` only, 100-160ms ease-out. Do not also animate color, shadow, and padding on that press.

## Popovers

Scale from the trigger. `transform-origin: center` is wrong for almost every popover.

```css
.popover {
  transform-origin: var(--transform-origin);
}
```

Modals are the exception. They are not anchored, so they stay centered.

## Tooltips

Delay the first tooltip so a stray hover does not flash it. Once one tooltip in the group is open, the next opens with no delay and no animation.

```css
.tooltip {
  transition: transform 125ms ease-out, opacity 125ms ease-out;
  transform-origin: var(--transform-origin);
}

.tooltip[data-starting-style],
.tooltip[data-ending-style] {
  opacity: 0;
  transform: scale(0.97);
}

.tooltip[data-instant] {
  transition-duration: 0ms;
}
```

The `0.97` here is the tooltip's enter scale, not the button press scale.

## Loved components

These change how you build a reusable component. They do not ask you to rename it.

1. Adoption should be one mount and one call. No required provider, no setup hook, unless the framework forces it.
2. The default easing, duration, and look have to be good. Most callers never pass options.
3. Hide the edge cases. Pause timers while the tab is hidden. Keep hover across gaps in a stack. Capture the pointer during drag. Ignore extra touch points after the drag starts.
4. Dynamic UI uses transitions, not keyframes, so a second trigger can reverse the first.
5. Enter and exit opacity has to agree with the height change. There is no formula. Slow it down and adjust until the two read as one motion.

Review the motion slowed down in the same session. You will see origin and overlap bugs that full speed hides.
