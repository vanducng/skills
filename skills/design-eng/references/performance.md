# Performance and motion access

## Only transform and opacity

`padding`, `margin`, `height`, and `width` run layout and paint. `transform` and `opacity` can stay on the compositor.

## Do not animate inherited variables

Setting `--swipe-amount` on a parent restyles every child. Write `transform` on the element that moves.

```js
element.style.transform = `translateY(${distance}px)`;
```

## Framer Motion shorthand is on the main thread

`x`, `y`, and `scale` on `motion` use `requestAnimationFrame`. Under load they drop frames. The full transform string stays on the compositor:

```jsx
<motion.div animate={{ transform: "translateX(100px)" }} />
```

CSS animations also stay smooth while the page is loading. Use CSS for a predetermined animation. Use JS when the gesture has to retarget. The Web Animations API is the middle path: JS control, compositor playback.

```js
element.animate(
  [{ clipPath: "inset(0 0 100% 0)" }, { clipPath: "inset(0 0 0 0)" }],
  {
    duration: 1000,
    fill: "forwards",
    easing: "cubic-bezier(0.77, 0, 0.175, 1)",
  },
);
```

## Reduced motion

Reduced motion means less movement, not a frozen UI. Keep opacity and color when they carry the state change. Drop travel.

```css
@media (prefers-reduced-motion: reduce) {
  .element {
    animation: fade 0.2s ease;
  }
}
```

```jsx
const shouldReduceMotion = useReducedMotion();
const closedX = shouldReduceMotion ? 0 : "-100%";
```

A full accessibility audit is `vd:uiuxdesign`. This file only covers motion.

## Hover on touch

Touch fires hover on tap. Gate hover motion:

```css
@media (hover: hover) and (pointer: fine) {
  .element:hover {
    transform: scale(1.05);
  }
}
```
