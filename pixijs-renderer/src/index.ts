import { Application, RenderTexture } from "pixi.js";
import type { CanvasModel } from "./ir/types";
import { buildScene } from "./render/renderer";

export { buildScene };
export * from "./ir/types";
export {
  linearGradientPixels,
  radialGradientPixels,
  buildGradientLut,
} from "./core/gradient";

export interface RenderedPixels {
  width: number;
  height: number;
  /** RGBA, unpremultiplied, top-left origin. */
  pixels: Uint8ClampedArray;
}

/**
 * Render a CanvasModel off-screen at 1:1 resolution and read back its pixels.
 * The deterministic RenderTexture path (fixed w×h, no devicePixelRatio) is what
 * the visual-diff harness compares against quickthumb's PNG output.
 */
export async function renderModelToPixels(
  app: Application,
  model: CanvasModel,
): Promise<RenderedPixels> {
  const scene = buildScene(model);
  const rt = RenderTexture.create({ width: model.width, height: model.height, resolution: 1 });
  app.renderer.render({ container: scene, target: rt, clear: true });
  const pixels = app.renderer.extract.pixels(rt).pixels as Uint8ClampedArray;
  scene.destroy({ children: true });
  rt.destroy(true);
  return { width: model.width, height: model.height, pixels };
}

let sharedApp: Application | null = null;

/** Lazily create a 1:1, antialiased, transparent off-screen Pixi application. */
export async function getApp(): Promise<Application> {
  if (sharedApp) return sharedApp;
  const app = new Application();
  await app.init({
    width: 16,
    height: 16,
    resolution: 1,
    autoDensity: false,
    antialias: true,
    backgroundAlpha: 0,
    preference: "webgl",
  });
  sharedApp = app;
  return app;
}
