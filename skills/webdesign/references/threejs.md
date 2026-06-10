# Three.js Reference

Use this reference only for explicit 3D, WebGL, WebGPU, GLTF/GLB, shader, particle, XR, game, product configurator, or canvas-scene work.

## When To Use Three.js

Use Three.js for:

- 3D scenes, product configurators, architecture, maps, scientific or data visualization.
- GLTF/GLB model loading.
- Particles, shaders, postprocessing, or GPU-driven effects.
- WebXR/VR/AR prototypes.
- Interactive canvas experiences where DOM/CSS is not enough.

Do not use Three.js for decorative background motion if CSS or a static asset would be cheaper, more accessible, and easier to maintain.

Sources:

- Three.js docs: https://threejs.org/docs/
- Examples: https://threejs.org/examples/

## Setup

Basic scene:

```ts
import * as THREE from 'three'

const scene = new THREE.Scene()
const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000)
camera.position.set(0, 1.5, 4)

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
renderer.setSize(width, height)

scene.add(new THREE.AmbientLight(0xffffff, 0.7))
const key = new THREE.DirectionalLight(0xffffff, 1.2)
key.position.set(3, 5, 4)
scene.add(key)
```

Rules:

- Set pixel ratio with a cap.
- Resize renderer and camera on container resize.
- Use `requestAnimationFrame` only while the scene is mounted/visible when possible.
- Dispose geometries, materials, textures, render targets, and controls on unmount.
- Provide fallback content when WebGL/WebGPU is unavailable.

## React Integration

If the project already uses React Three Fiber, use it. If not, do not add it for one tiny scene unless it simplifies lifecycle and component integration.

React scene checks:

- Canvas has stable dimensions and does not cause layout shift.
- Suspense/loading state is visible for model loads.
- Controls do not trap scroll/touch unexpectedly.
- Reduced motion disables or slows nonessential animation.
- State updates do not run every frame unless necessary.

## GLTF/GLB

Use GLB for web delivery when possible. Use `GLTFLoader` for glTF 2.0 assets.

Checklist:

- Put assets under the app's public/static asset path or import pipeline according to framework conventions.
- Compress meshes/textures where possible.
- Use KTX2/Basis or WebP/AVIF textures when the pipeline supports them.
- Handle loader progress and failure.
- Normalize model scale, center, and camera framing.
- Dispose image bitmaps/textures manually when models are removed.
- Avoid loading huge unoptimized source assets directly from design tools.

Source: https://threejs.org/docs/pages/GLTFLoader.html

## Camera And Controls

- Use `PerspectiveCamera` for most 3D scenes; `OrthographicCamera` for isometric/product/UI-like scenes.
- Fit camera to model bounds rather than guessing positions.
- Limit orbit/pan/zoom ranges so users cannot lose the subject.
- Keep controls accessible: provide reset view and non-pointer alternatives when the scene is central to the product.
- Do not let canvas gestures block page scroll on mobile unless the canvas is the primary experience.

## Materials And Lighting

- Use `MeshStandardMaterial` / `MeshPhysicalMaterial` for PBR assets.
- Use environment maps for product realism.
- Keep lights minimal and purposeful.
- Use color management correctly for the installed Three.js version.
- Avoid expensive real-time shadows unless the visual payoff matters.
- Bake lighting when assets are static and performance matters.

## Animation

- Use `AnimationMixer` for imported clips.
- Use time deltas, not frame counts.
- Pause when tab/canvas is hidden if possible.
- Keep UI animation separate from render-loop state.
- Avoid layout-affecting DOM updates from the render loop.

## Interaction

- Use raycasting for picking.
- Keep interactive objects large enough to hit on touch.
- Provide hover/selected/focus equivalents.
- Use pointer events carefully when overlaying DOM on canvas.
- Make critical actions available outside the canvas when accessibility matters.

## WebGPU

Three.js `WebGPURenderer` is the newer alternative to `WebGLRenderer`. Current docs say it tries WebGPU when supported and falls back to WebGL 2 otherwise.

Use WebGPU when:

- The app needs compute shaders or modern GPU features.
- Browser/runtime support is known.
- You have time to test fallbacks.

Prefer WebGL when:

- The scene is standard product/marketing/visualization work.
- Broad compatibility matters more than newer GPU features.
- Existing postprocessing/shader code is WebGL-specific.

Source: https://threejs.org/docs/pages/WebGPURenderer.html

## Performance

Check:

- Draw calls.
- Triangle count.
- Texture memory.
- Shader complexity.
- Postprocessing passes.
- Pixel ratio.
- Shadows.
- Animation loop work.

Tactics:

- Instance repeated meshes.
- Merge static geometry.
- Use LOD for complex models.
- Cap pixel ratio.
- Use compressed textures.
- Avoid unnecessary postprocessing.
- Use object pooling for particles and transient meshes.
- Dispose resources on route changes.

## Verification

Before handoff:

- Open in browser and confirm canvas is nonblank.
- Check desktop and mobile framing.
- Resize viewport and confirm camera/renderer update.
- Interact with controls/picking.
- Check console for WebGL/WebGPU warnings/errors.
- Confirm loading and error fallback states.
- Confirm reduced-motion behavior if animation is decorative.
- Capture screenshot or run Playwright canvas smoke check when practical.
