/**
 * TypeScript mirror of the quickthumb JSON IR (the `to_json()` output of
 * `quickthumb/models.py`). The renderer consumes this contract verbatim — it
 * does not invent a schema. Only the subset implemented by the current
 * static-render slice is fully typed; richer fields are kept permissive so
 * unimplemented layers round-trip without loss.
 *
 * Source of truth: quickthumb/models.py, quickthumb/transitions.py.
 */

export type HexColor = string; // "#RRGGBB" or "#RRGGBBAA"
/** Background colors may serialize as a hex string or an (r,g,b[,a]) tuple. */
export type ColorValue = HexColor | number[];

export type Coordinate = number | string; // px number or "NN%" / "-NN%"
export type Position = [Coordinate, Coordinate];

/** 9-way alignment enum value as serialized by `Align` in models.py. */
export type Align =
  | "center"
  | "top-left"
  | "top-center"
  | "top-right"
  | "left"
  | "right"
  | "bottom-left"
  | "bottom-center"
  | "bottom-right";

export type GradientStop = [HexColor, number];

export interface LinearGradient {
  type: "linear";
  angle: number;
  stops: GradientStop[];
}

export interface RadialGradient {
  type: "radial";
  stops: GradientStop[];
  center: [number, number];
}

export type Gradient = LinearGradient | RadialGradient;

export type BlendMode =
  | "multiply"
  | "overlay"
  | "screen"
  | "darken"
  | "lighten"
  | "normal";

export type FitMode = "cover" | "contain" | "fill";

export interface BackgroundLayer {
  type: "background";
  color?: ColorValue | null;
  gradient?: Gradient | null;
  image?: string | null;
  opacity: number;
  blend_mode?: BlendMode | null;
  fit?: FitMode | null;
  effects?: unknown[];
}

export type ShapeKind =
  | "rectangle"
  | "ellipse"
  | "pill"
  | "triangle"
  | "star"
  | "polygon";

export interface ShapeLayer {
  type: "shape";
  shape: ShapeKind;
  position: Position;
  width: number;
  height: number;
  color: HexColor;
  border_radius: number;
  opacity: number;
  rotation: number;
  align?: Align | null;
  points?: [number, number][] | null;
  star_points: number;
  inner_radius: number;
  effects?: unknown[];
  animation?: unknown;
}

export interface OutlineLayer {
  type: "outline";
  width: number;
  color: HexColor;
  offset: number;
  opacity: number;
}

/** Layers the current slice does not yet render are accepted but skipped. */
export interface UnsupportedLayer {
  type: "text" | "image" | "svg" | "group";
  [key: string]: unknown;
}

export type Layer =
  | BackgroundLayer
  | ShapeLayer
  | OutlineLayer
  | UnsupportedLayer;

export interface CanvasModel {
  width: number;
  height: number;
  layers: Layer[];
}

export interface DeckModel {
  width?: number;
  height?: number;
  theme?: Record<string, unknown>;
  transition?: Record<string, unknown>;
  slides: (CanvasModel & { transition?: Record<string, unknown> })[];
}
