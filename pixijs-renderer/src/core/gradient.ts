import type { GradientStop } from "../ir/types";
import { parseColor } from "./color";

/**
 * 256-entry RGBA lookup table, a direct port of
 * `EffectsEngine._create_gradient_lut` (quickthumb/_effects.py:169): stops are
 * sorted by position, the table clamps below the first stop and above the last,
 * and interpolates each channel (including alpha) linearly between adjacent
 * stops. Index i corresponds to gradient parameter i/255.
 */
export function buildGradientLut(stops: GradientStop[]): Uint8Array {
  const parsed = stops
    .map(([color, pos]) => ({ c: parseColor(color), pos }))
    .sort((a, b) => a.pos - b.pos);

  const lut = new Uint8Array(256 * 4);
  const first = parsed[0];
  const last = parsed[parsed.length - 1];

  for (let i = 0; i < 256; i++) {
    const pos = i / 255;
    let r: number, g: number, b: number, a: number;
    if (pos <= first.pos) {
      ({ r, g, b, a } = first.c);
    } else if (pos >= last.pos) {
      ({ r, g, b, a } = last.c);
    } else {
      // Default to the last stop's color (matches the Python fallback) before
      // the interpolation loop overwrites it for the bracketing segment.
      ({ r, g, b, a } = last.c);
      for (let j = 0; j < parsed.length - 1; j++) {
        const s1 = parsed[j];
        const s2 = parsed[j + 1];
        if (s1.pos <= pos && pos <= s2.pos) {
          const ratio = s2.pos !== s1.pos ? (pos - s1.pos) / (s2.pos - s1.pos) : 0;
          r = Math.trunc(s1.c.r + (s2.c.r - s1.c.r) * ratio);
          g = Math.trunc(s1.c.g + (s2.c.g - s1.c.g) * ratio);
          b = Math.trunc(s1.c.b + (s2.c.b - s1.c.b) * ratio);
          a = Math.trunc(s1.c.a + (s2.c.a - s1.c.a) * ratio);
          break;
        }
      }
    }
    lut[i * 4] = r;
    lut[i * 4 + 1] = g;
    lut[i * 4 + 2] = b;
    lut[i * 4 + 3] = a;
  }
  return lut;
}

function sampleLut(lut: Uint8Array, g: number, out: Uint8Array, o: number): void {
  let idx = Math.round(g * 255);
  if (idx < 0) idx = 0;
  else if (idx > 255) idx = 255;
  out[o] = lut[idx * 4];
  out[o + 1] = lut[idx * 4 + 1];
  out[o + 2] = lut[idx * 4 + 2];
  out[o + 3] = lut[idx * 4 + 3];
}

/**
 * Linear-gradient pixel buffer reproducing `create_linear_gradient`
 * (quickthumb/_effects.py:216). Empirically pinned against PIL:
 *
 *   g(p) = 0.5 + dot(p - center, (cosθ, sinθ)) / D
 *   center = ((w-1)/2, (h-1)/2),  D = ceil(sqrt(w² + h²))
 *
 * angle 0 = left→right, screen coords (x right+, y down+). The box only ever
 * shows the centre slice of the full 0..1 ramp — never the whole range.
 */
export function linearGradientPixels(
  w: number,
  h: number,
  angle: number,
  stops: GradientStop[],
): Uint8Array {
  const lut = buildGradientLut(stops);
  const out = new Uint8Array(w * h * 4);
  const rad = (angle * Math.PI) / 180;
  const dx = Math.cos(rad);
  const dy = Math.sin(rad);
  const cx = (w - 1) / 2;
  const cy = (h - 1) / 2;
  const D = Math.ceil(Math.sqrt(w * w + h * h));
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const g = 0.5 + ((x - cx) * dx + (y - cy) * dy) / D;
      sampleLut(lut, g, out, (y * w + x) * 4);
    }
  }
  return out;
}

/**
 * Radial-gradient pixel buffer reproducing `create_radial_gradient`
 * (quickthumb/_effects.py:243). PIL's `radial_gradient` reaches white at the
 * corner of its source box (distance 128·√2 from centre), so the normalising
 * radius is `maxDist · √2`. The crop offset uses `int(center_px)` exactly as the
 * source does, which is why distances are measured from the truncated centre.
 *
 *   maxDist = max distance from centre to the four corners
 *   g(p)    = clamp( dist(p+0.5, trunc(center_px)) / (maxDist · √2), 0, 1 )
 */
export function radialGradientPixels(
  w: number,
  h: number,
  center: [number, number],
  stops: GradientStop[],
): Uint8Array {
  const lut = buildGradientLut(stops);
  const out = new Uint8Array(w * h * 4);
  const cxp = w * center[0];
  const cyp = h * center[1];
  const maxDist = Math.max(
    Math.hypot(cxp, cyp),
    Math.hypot(w - cxp, cyp),
    Math.hypot(cxp, h - cyp),
    Math.hypot(w - cxp, h - cyp),
  );
  const denom = maxDist * Math.SQRT2;
  const icx = Math.trunc(cxp);
  const icy = Math.trunc(cyp);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const dist = Math.hypot(x + 0.5 - icx, y + 0.5 - icy);
      const g = Math.min(dist / denom, 1);
      sampleLut(lut, g, out, (y * w + x) * 4);
    }
  }
  return out;
}
