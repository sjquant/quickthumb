# quickthumb · PixiJS v8 renderer

A GPU renderer (PixiJS v8, WebGPU-preferred / WebGL2-fallback) that consumes the
**quickthumb JSON IR** — the exact output of `Canvas.to_json()` / `Deck.to_json()`
— and draws it on a single canvas. See [`SPEC.md`](./SPEC.md) for the full v1
requirements and design.

This is **not** a replacement for quickthumb's PIL raster / SVG / PPTX / PDF
exporters. It is an additional, web-native backend whose purpose is machine-to-
machine visual consistency plus shader effects that CSS and PPTX can't express.

## Status — verified static-render slice (P1 core)

The riskiest claim in the spec is that a GPU renderer can reproduce PIL's
fidelity math closely enough to pass a pixel diff against quickthumb's own
output. This slice proves that end-to-end, with an automated harness:

| Layer / feature | Status | mean &#124;Δ&#124; vs quickthumb PNG |
| --- | --- | --- |
| `background` — solid color | ✅ byte-exact | 0.000 |
| `background` — linear gradient (any angle, multi-stop, alpha) | ✅ | 0.11–0.13 |
| `background` — radial gradient (centered / off-center) | ✅ | 0.19–0.49 |
| `shape` — rectangle, rounded-rect, ellipse, pill, triangle, star, polygon | ✅ | 0.20 |
| `shape` — opacity, alignment (9-way), rotation | ✅ | 0.05 |
| `outline` — inset border | ✅ byte-exact | 0.000 |
| realistic composite slide | ✅ | 0.26 |

All nine fixtures clear the **SPEC §13 acceptance bar (mean abs diff < 1.0/255)**;
solid fills and the axis-aligned outline are byte-exact. `text`, `image`, `svg`,
and `group` layers, per-layer animations, and slide transitions are the staged
next slices (SPEC §6–§8) — those layer types are accepted by the IR parser and
skipped rather than rendered incorrectly.

### Why the gradients match

PIL's gradient math was pinned **empirically against PIL itself**, not guessed:

- **Linear** (`src/core/gradient.ts`): `g = clamp(0.5 + dot(p − center, (cosθ, sinθ)) / D, 0, 1)`
  with `center = ((w−1)/2, (h−1)/2)` and `D = ceil(√(w²+h²))`. The box shows the
  *centre slice* of the ramp, never the full 0–1 range — the most common way to
  get gradients wrong. Mirrors `EffectsEngine.create_linear_gradient`.
- **Radial**: PIL's `radial_gradient` reaches white at the *corner* of its source
  box, so the normalising radius is `maxDist · √2`, and the crop offset uses the
  truncated centre `int(center_px)` exactly as the source does. Mirrors
  `create_radial_gradient`.
- The 256-entry color LUT is a direct port of `_create_gradient_lut` (sorted
  stops, end-clamping, per-channel + alpha interpolation).

## Architecture

```
src/
  ir/types.ts          TypeScript mirror of the quickthumb IR (models.py)
  core/color.ts        parse_color (#RRGGBB / #RRGGBBAA / tuple)
  core/coordinate.ts   parse_coordinate (% + px) and apply_alignment (9-way)
  core/gradient.ts     PIL-faithful linear/radial gradient + LUT  ← centerpiece
  render/renderer.ts   IR → Pixi scene graph (background / shape / outline)
  index.ts             public API + off-screen render-to-pixels
  harness.ts           browser hook (window.__qtRender) + interactive demo
test/
  fixtures/*.json      authored IR fixtures
  generate_refs.py     quickthumb → reference PNG + normalized (defaulted) IR
  run-visual.mjs       headless-Chromium render → pixel diff vs the PNG
```

The renderer and quickthumb consume the **same normalized IR**: the reference
generator round-trips each fixture through `Canvas.from_json(...).to_json()` so
both sides see identical, fully-defaulted fields and the only differences the
harness measures are rendering differences.

## Running it

Requirements: Node ≥ 20, and `uv` with the quickthumb project (for ground-truth
PNGs). A Chromium for Playwright is auto-detected from `/opt/pw-browsers`; set
`QT_CHROMIUM=/path/to/chrome` to override.

```bash
npm install
npm test          # generate refs → build → headless render → pixel diff
npm run dev       # interactive demo at http://localhost:5173
```

`npm test` runs the full chain; individual steps are `npm run refs`,
`npm run build`, and `npm run test:visual`. Rendered output and diff images for
each fixture are written to `test/out/` for inspection.

## Public API (current)

```ts
import { getApp, renderModelToPixels, buildScene } from "./src/index";

const app = await getApp();
const { width, height, pixels } = await renderModelToPixels(app, canvasModel);
// or, to attach to the DOM:
app.stage.addChild(buildScene(canvasModel));
```

The `new Deck(el, json, opts)` viewer API in SPEC §12 lands with the
transition/animation slices.
