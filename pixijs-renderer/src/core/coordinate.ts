import type { Align, Coordinate } from "../ir/types";

/**
 * Mirror of `parse_coordinate` (quickthumb/_base.py:38): an int passes through;
 * a "NN%" string resolves against the given canvas dimension. quickthumb floors
 * via Python int(), so we truncate toward zero too.
 */
export function parseCoordinate(value: Coordinate, dimension: number): number {
  if (typeof value === "number") return value;
  const pct = parseFloat(value.replace(/%$/, ""));
  return Math.trunc((dimension * pct) / 100);
}

const HORIZONTAL: Record<Align, "left" | "center" | "right"> = {
  center: "center",
  "top-left": "left",
  "top-center": "center",
  "top-right": "right",
  left: "left",
  right: "right",
  "bottom-left": "left",
  "bottom-center": "center",
  "bottom-right": "right",
};

const VERTICAL: Record<Align, "top" | "middle" | "bottom"> = {
  center: "middle",
  "top-left": "top",
  "top-center": "top",
  "top-right": "top",
  left: "middle",
  right: "middle",
  "bottom-left": "bottom",
  "bottom-center": "bottom",
  "bottom-right": "bottom",
};

/**
 * Mirror of `apply_alignment` (quickthumb/_base.py:73). Shifts an (x, y) anchor
 * so a box of `size` is aligned around it. Uses floor division for the centered
 * case exactly as Python's `width // 2` does.
 */
export function applyAlignment(
  x: number,
  y: number,
  width: number,
  height: number,
  align: Align,
): { x: number; y: number } {
  const h = HORIZONTAL[align];
  const v = VERTICAL[align];
  if (h === "center") x = x - Math.floor(width / 2);
  else if (h === "right") x = x - width;
  if (v === "middle") y = y - Math.floor(height / 2);
  else if (v === "bottom") y = y - height;
  return { x, y };
}
