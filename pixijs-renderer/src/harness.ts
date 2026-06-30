import { Application } from "pixi.js";
import type { CanvasModel } from "./ir/types";
import { buildScene } from "./render/renderer";
import { getApp, renderModelToPixels } from "./index";

declare global {
  interface Window {
    __qtRender: (
      model: CanvasModel,
    ) => Promise<{ width: number; height: number; pixels: number[] }>;
    __qtReady: boolean;
  }
}

// Pixel-readback hook used by test/run-visual.mjs.
window.__qtRender = async (model: CanvasModel) => {
  const app = await getApp();
  const { width, height, pixels } = await renderModelToPixels(app, model);
  return { width, height, pixels: Array.from(pixels) };
};
window.__qtReady = true;

// Visible demo: render any model dropped on the page (or a built-in sample) to a
// DOM canvas so `npm run dev` shows the renderer working interactively.
async function demo(): Promise<void> {
  const sample: CanvasModel = {
    width: 480,
    height: 270,
    layers: [
      {
        type: "background",
        gradient: { type: "linear", angle: 135, stops: [["#1e3a8a", 0], ["#9333ea", 1]] },
        opacity: 1,
      },
      {
        type: "shape",
        shape: "pill",
        position: ["50%", "50%"],
        width: 220,
        height: 64,
        color: "#fbbf24",
        border_radius: 0,
        opacity: 1,
        rotation: 0,
        align: "center",
        star_points: 5,
        inner_radius: 0.5,
      },
      { type: "outline", width: 6, color: "#ffffff", offset: 12, opacity: 1 },
    ],
  };

  const app = new Application();
  await app.init({ width: sample.width, height: sample.height, antialias: true, backgroundAlpha: 0 });
  document.getElementById("stage")?.appendChild(app.canvas);
  app.stage.addChild(buildScene(sample));
}

void demo();
