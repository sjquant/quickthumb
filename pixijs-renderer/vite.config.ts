import { defineConfig } from "vite";

// Single-page build: the demo / test harness entry is index.html, which mounts
// the renderer and exposes window.__qtRender for the visual-diff harness.
export default defineConfig({
  base: "./",
  build: {
    outDir: "dist",
    target: "es2022",
    sourcemap: true,
  },
});
