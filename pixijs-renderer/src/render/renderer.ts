import { Container, Graphics, Sprite, Texture } from "pixi.js";
import type {
  BackgroundLayer,
  CanvasModel,
  Layer,
  OutlineLayer,
  ShapeLayer,
} from "../ir/types";
import { parseColor, toPixiColor } from "../core/color";
import { applyAlignment, parseCoordinate } from "../core/coordinate";
import { linearGradientPixels, radialGradientPixels } from "../core/gradient";

/**
 * Build the Pixi display tree for one CanvasModel. Layers are appended in IR
 * order (painter's algorithm), matching quickthumb's raster pass. Returns a
 * Container the caller renders to its surface; unsupported layer types are
 * skipped so a partial scene still renders the layers we do support.
 */
export function buildScene(model: CanvasModel): Container {
  const root = new Container();
  for (const layer of model.layers) {
    const node = buildLayer(layer, model);
    if (node) root.addChild(node);
  }
  return root;
}

function buildLayer(layer: Layer, model: CanvasModel): Container | null {
  switch (layer.type) {
    case "background":
      return buildBackground(layer, model);
    case "shape":
      return buildShape(layer, model);
    case "outline":
      return buildOutline(layer, model);
    default:
      return null; // text/image/svg/group: staged for a later slice
  }
}

function buildBackground(layer: BackgroundLayer, model: CanvasModel): Container {
  const { width, height } = model;
  if (layer.gradient) {
    const pixels =
      layer.gradient.type === "linear"
        ? linearGradientPixels(width, height, layer.gradient.angle, layer.gradient.stops)
        : radialGradientPixels(width, height, layer.gradient.center, layer.gradient.stops);
    const sprite = new Sprite(textureFromPixels(pixels, width, height));
    sprite.alpha = layer.opacity;
    return sprite;
  }

  const g = new Graphics();
  if (layer.color != null) {
    const c = parseColor(layer.color);
    g.rect(0, 0, width, height).fill({ color: toPixiColor(c), alpha: (c.a / 255) * layer.opacity });
  }
  return g;
}

/** Upload a raw RGBA buffer through a 2D canvas so opaque pixels stay byte-exact. */
function textureFromPixels(pixels: Uint8Array, width: number, height: number): Texture {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d")!;
  const data = new Uint8ClampedArray(width * height * 4);
  data.set(pixels);
  ctx.putImageData(new ImageData(data, width, height), 0, 0);
  return Texture.from(canvas);
}

function buildShape(layer: ShapeLayer, model: CanvasModel): Container {
  const c = parseColor(layer.color);
  const fill = { color: toPixiColor(c), alpha: (c.a / 255) * layer.opacity };
  const w = layer.width;
  const h = layer.height;

  const g = new Graphics();
  switch (layer.shape) {
    case "rectangle":
      if (layer.border_radius > 0) g.roundRect(0, 0, w, h, layer.border_radius);
      else g.rect(0, 0, w, h);
      g.fill(fill);
      break;
    case "ellipse":
      g.ellipse(w / 2, h / 2, w / 2, h / 2).fill(fill);
      break;
    case "pill":
      g.roundRect(0, 0, w, h, Math.min(w, h) / 2).fill(fill);
      break;
    default:
      g.poly(polygonPoints(layer).flatMap(([px, py]) => [px * w, py * h])).fill(fill);
  }

  const x = parseCoordinate(layer.position[0], model.width);
  const y = parseCoordinate(layer.position[1], model.height);
  const placed = layer.align ? applyAlignment(x, y, w, h, layer.align) : { x, y };
  g.position.set(placed.x, placed.y);

  if (layer.rotation !== 0) {
    // Rotate about the shape's centre, like PIL's centred rotate().
    g.pivot.set(w / 2, h / 2);
    g.position.set(placed.x + w / 2, placed.y + h / 2);
    g.rotation = (layer.rotation * Math.PI) / 180;
  }
  return g;
}

/** Normalized 0..1 outline points for triangle/star/polygon (mirrors _shapes.py). */
function polygonPoints(layer: ShapeLayer): [number, number][] {
  if (layer.shape === "triangle") return [[0.5, 0], [1, 1], [0, 1]];
  if (layer.shape === "star") {
    const pts: [number, number][] = [];
    const spikes = layer.star_points;
    for (let i = 0; i < spikes * 2; i++) {
      const radius = i % 2 === 0 ? 0.5 : 0.5 * layer.inner_radius;
      const angle = -Math.PI / 2 + (i * Math.PI) / spikes;
      pts.push([0.5 + radius * Math.cos(angle), 0.5 + radius * Math.sin(angle)]);
    }
    return pts;
  }
  return layer.points ?? [];
}

function buildOutline(layer: OutlineLayer, model: CanvasModel): Container {
  const c = parseColor(layer.color);
  const fill = { color: toPixiColor(c), alpha: (c.a / 255) * layer.opacity };
  const wpx = layer.width;
  const x1 = layer.offset;
  const y1 = layer.offset;
  const x2 = model.width - layer.offset - 1;
  const y2 = model.height - layer.offset - 1;
  const fw = x2 - x1 + 1;
  const fh = y2 - y1 + 1;

  // The nested 1px rectangles of _render_outline_layer union into a frame band
  // of thickness `width`; draw it as four axis-aligned (AA-free) rects.
  const g = new Graphics();
  g.rect(x1, y1, fw, wpx);
  g.rect(x1, y2 - wpx + 1, fw, wpx);
  g.rect(x1, y1, wpx, fh);
  g.rect(x2 - wpx + 1, y1, wpx, fh);
  g.fill(fill);
  return g;
}
