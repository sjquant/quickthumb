import type { ColorValue } from "../ir/types";

export interface Rgba {
  r: number;
  g: number;
  b: number;
  a: number; // 0..255
}

/**
 * Mirror of `EffectsEngine.parse_color` (quickthumb/_effects.py:16) plus the
 * tuple form a BackgroundLayer color may carry. Returns 8-bit channels with a
 * default alpha of 255. Unparseable values fall back to opaque black, matching
 * quickthumb's DEFAULT_TEXT_COLOR.
 */
export function parseColor(color: ColorValue): Rgba {
  if (Array.isArray(color)) {
    const [r, g, b, a] = color;
    return { r, g, b, a: a ?? 255 };
  }
  const hex = color.replace(/^#/, "");
  if (hex.length === 6 || hex.length === 8) {
    const r = parseInt(hex.slice(0, 2), 16);
    const g = parseInt(hex.slice(2, 4), 16);
    const b = parseInt(hex.slice(4, 6), 16);
    const a = hex.length === 8 ? parseInt(hex.slice(6, 8), 16) : 255;
    return { r, g, b, a };
  }
  return { r: 0, g: 0, b: 0, a: 255 };
}

/** Pack an Rgba into the 0xRRGGBB number Pixi expects for tints/fills. */
export function toPixiColor(c: Rgba): number {
  return (c.r << 16) | (c.g << 8) | c.b;
}
