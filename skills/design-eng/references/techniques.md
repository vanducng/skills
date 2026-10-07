# Techniques

Transforms, clip-path, and drag. Use these after the decision framework says the motion belongs.

## translate percentages

`translateY(100%)` moves an element by its own height. Use it for drawers and toasts instead of a hardcoded pixel distance.

`scale()` scales the children too. On a button press, the label and icon shrink with the button. That is what you want.

`rotateX()` and `rotateY()` need `transform-style: preserve-3d` on the parent. Set `transform-origin` to the trigger for anything anchored.

## clip-path

`inset(top right bottom left)` eats in from each side.

```css
.hidden {
  clip-path: inset(0 100% 0 0);
}

.visible {
  clip-path: inset(0 0 0 0);
}
```

Tabs: duplicate the tab list, style the copy as active, and clip that copy to the active tab. Animate the clip. Per-tab color transitions never look this continuous.

Hold to delete: on `:active`, run the overlay from `inset(0 100% 0 0)` to `inset(0 0 0 0)` over 2s linear. On release, snap back in 200ms ease-out. Press scale still comes from `vd:better-ui`.

Image reveal on scroll: start at `inset(0 0 100% 0)`, animate to `inset(0 0 0 0)` when it enters. `IntersectionObserver`, or `useInView` with `{ once: true, margin: "-100px" }`.

Comparison slider: two stacked images. Clip the top one with `inset(0 50% 0 0)` and drive the right inset from the drag. No extra DOM.

## Drag

Dismiss on distance or on velocity. A flick should be enough.

```js
const velocity = Math.abs(swipeAmount) / timeTaken;
if (Math.abs(swipeAmount) >= SWIPE_THRESHOLD || velocity > 0.11) {
  dismiss();
}
```

Past the natural edge, damp the movement. More drag, less travel. Do not hit an invisible wall.

On pointer down, capture the pointer so the drag continues outside the element. Ignore further touch points until the gesture ends, or the element jumps to the new finger.
