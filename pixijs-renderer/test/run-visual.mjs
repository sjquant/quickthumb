// Visual-diff harness: render every normalized fixture in headless Chromium via
// the built renderer, then compare the readback pixels to quickthumb's PNG.
//
// Acceptance follows SPEC §13: gradients / solid / outline must reproduce the
// PIL math to < ~1/255 mean absolute difference; anti-aliased shape edges are
// allowed a slightly looser bound. Thresholds are per-category below.
import { readFileSync, readdirSync, mkdirSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { preview } from "vite";
import { chromium } from "playwright";
import { PNG } from "pngjs";
import pixelmatch from "pixelmatch";

const HERE = dirname(fileURLToPath(import.meta.url));
const NORMALIZED = join(HERE, "normalized");
const REFS = join(HERE, "refs");
const OUT = join(HERE, "out");
mkdirSync(OUT, { recursive: true });

// Per-fixture mean-abs-diff ceilings (0..255 scale, averaged over RGBA). The
// SPEC §13 acceptance bar is mean < 1.0/255 for shapes/gradients/backgrounds;
// every fixture meets it, so 1.0 is the default. Solid fills and the
// axis-aligned outline are byte-exact, so they get a tight 0.1.
const DEFAULT_LIMIT = 1.0;
const THRESHOLDS = {
  bg_solid: 0.1,
  outline: 0.1,
};

function meanAbsDiff(a, b) {
  let sum = 0;
  for (let i = 0; i < a.length; i++) sum += Math.abs(a[i] - b[i]);
  return sum / a.length;
}

async function main() {
  const server = await preview({
    root: HERE + "/..",
    preview: { port: 4317, strictPort: true },
    logLevel: "warn",
  });
  const url = `http://localhost:4317`;

  // Use the browser pre-installed in this environment rather than downloading
  // one (PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD is set). Falls back to Playwright's
  // own resolution if the pinned path is absent.
  const execPath = process.env.QT_CHROMIUM ||
    "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
  const browser = await chromium.launch({
    executablePath: existsSync(execPath) ? execPath : undefined,
    args: [
      "--use-gl=angle",
      "--use-angle=swiftshader",
      "--enable-unsafe-swiftshader",
      "--ignore-gpu-blocklist",
    ],
  });
  const page = await browser.newPage();
  const pageErrors = [];
  page.on("pageerror", (e) => pageErrors.push(String(e)));
  await page.goto(url, { waitUntil: "load" });
  await page.waitForFunction(() => window.__qtReady === true, { timeout: 30000 });

  const names = readdirSync(NORMALIZED)
    .filter((f) => f.endsWith(".json"))
    .map((f) => f.replace(/\.json$/, ""))
    .sort();

  let failures = 0;
  const rows = [];
  for (const name of names) {
    const model = JSON.parse(readFileSync(join(NORMALIZED, `${name}.json`), "utf8"));
    const result = await page.evaluate((m) => window.__qtRender(m), model);
    const actual = Uint8ClampedArray.from(result.pixels);
    const { width, height } = result;

    const ref = PNG.sync.read(readFileSync(join(REFS, `${name}.png`)));
    if (ref.width !== width || ref.height !== height) {
      console.error(`✗ ${name}: size mismatch ref ${ref.width}x${ref.height} vs ${width}x${height}`);
      failures++;
      continue;
    }

    // Save the actual render for inspection.
    const actualPng = new PNG({ width, height });
    actualPng.data.set(actual);
    writeFileSync(join(OUT, `${name}.actual.png`), PNG.sync.write(actualPng));

    const diff = new PNG({ width, height });
    pixelmatch(actual, ref.data, diff.data, width, height, { threshold: 0.1 });
    writeFileSync(join(OUT, `${name}.diff.png`), PNG.sync.write(diff));

    const mad = meanAbsDiff(actual, ref.data);
    const limit = THRESHOLDS[name] ?? DEFAULT_LIMIT;
    const ok = mad <= limit;
    if (!ok) failures++;
    rows.push({ name, mad: mad.toFixed(3), limit, status: ok ? "PASS" : "FAIL" });
  }

  await browser.close();
  await server.close();

  console.log("\n  fixture                 mean|Δ|   limit   result");
  console.log("  " + "-".repeat(52));
  for (const r of rows) {
    console.log(
      `  ${r.name.padEnd(22)} ${r.mad.padStart(7)} ${String(r.limit).padStart(7)}   ${r.status}`,
    );
  }
  if (pageErrors.length) {
    console.error("\nPage errors:\n" + pageErrors.join("\n"));
  }
  console.log("");
  if (failures > 0) {
    console.error(`${failures} fixture(s) exceeded tolerance`);
    process.exit(1);
  }
  console.log(`All ${rows.length} fixtures within tolerance ✓`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
