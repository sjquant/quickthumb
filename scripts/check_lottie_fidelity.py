"""Compare exported vectors with a local lottie-web SVG and Canvas player.

Developer-only: requires an explicitly supplied Chrome and player bundle, Node,
jsonschema, and quickthumb[lottie]. No downloads or product policy changes.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import jsonschema
from PIL import Image
from quickthumb import LottieOptions
from scripts.check_html_fidelity import compare

LIMITS = {
    "pixel_tolerance": 32,
    "max_different_pixel_ratio": 0.08,
    "min_hash_similarity": 0.93,
}
FIXTURES = {
    "static": [0],
    "paths": [0],
    "motion": [0, 0.125, 0.5, 1, 1.5],
    "parenting": [0, 0.25, 0.5, 1, 1.25],
    "trim": [0, 0.25, 0.5, 1, 1.5],
    "text": [0],
    "morph": [0, 0.25, 0.5, 1, 1.5, 2],
    "intro": [0, 0.25, 0.5, 1, 1.5, 2, 2.25],
    "trim_multi": [0, 0.25, 0.5, 0.75, 1, 1.25],
}


def prepare_cases(output: Path, renderers: tuple[str, ...] = ("svg",)) -> list[dict]:
    schema_path = Path(__file__).resolve().parents[1] / "tests/fixtures/lottie/schema-1.0.1.json"
    schema = json.loads(schema_path.read_text())
    cases = []
    for name, seconds in FIXTURES.items():
        canvas = importlib.import_module(f"examples.lottie_{name}").build_canvas()
        payload_path = output / f"{name}.lot"
        receipt = canvas.export(payload_path, animation=LottieOptions(fps=24, hold=0.5))
        payload = json.loads(payload_path.read_text())
        jsonschema.validate(payload, schema)
        (output / f"{name}-receipt.json").write_text(receipt.model_dump_json(indent=2))
        for index, second in enumerate(seconds):
            reference = canvas.render_frame(second)
            reference_path = output / f"{name}-{index}-reference.png"
            reference.save(reference_path)
            # Compare ink as well as the whole frame: small scenes must not pass
            # simply because most canvas pixels are transparent.
            ink = reference.getbbox()
            regions = [list(ink)] if ink else []
            if name == "intro":
                regions = [[25, 25, 400, 85], [60, 100, 220, 280], [270, 95, 450, 275]]
            elif name == "trim_multi":
                regions = [[40, 40, 700, 240], [40, 320, 440, 560], [500, 320, 860, 560]]
            for renderer in renderers:
                case = {
                    "name": f"{name}-{index}-{renderer}",
                    "payload": str(payload_path),
                    "width": canvas.width,
                    "height": canvas.height,
                    "renderer": renderer,
                    "frame": second * 24,
                    "reference": str(reference_path),
                    "regions": regions,
                    "limits": LIMITS,
                    "control": None,
                }
                if name == "trim_multi" and second == 0:
                    # Both translucent contours cover this interior point.
                    # A second paint would make alpha about 192 instead of 128.
                    case["probes"] = [
                        {
                            "point": [220, 360],
                            "rgba": list(reference.getpixel((220, 360))),
                            "tolerance": 2,
                        }
                    ]
                cases.append(case)
                if index == len(seconds) - 1:
                    cases.append({**case, "name": case["name"] + "-blank", "control": "blank"})
                    if len(seconds) > 1:
                        cases.append(
                            {**case, "name": case["name"] + "-frozen", "control": "frozen"}
                        )
    return cases


def assess(case: dict, actual: Image.Image) -> dict:
    with Image.open(case["reference"]) as source:
        expected = source.convert("RGBA")
    actual = actual.convert("RGBA")
    result = compare(expected, actual, case["limits"])
    result["regions"] = [
        {"box": box, **compare(expected.crop(box), actual.crop(box), case["limits"])}
        for box in case["regions"]
    ]
    matched = result["verdict"] != "out_of_policy" and all(
        region["verdict"] != "out_of_policy" for region in result["regions"]
    )
    result["probes"] = []
    for probe in case.get("probes", []):
        observed = actual.getpixel(tuple(probe["point"]))
        delta = max(abs(a - b) for a, b in zip(observed, probe["rgba"], strict=True))
        accepted = delta <= probe["tolerance"]
        result["probes"].append({**probe, "observed": list(observed), "passed": accepted})
        matched = matched and accepted
    result["passed"] = not matched if case["control"] else matched
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chrome", type=Path, required=True)
    parser.add_argument("--player", type=Path, required=True, help="Local lottie-web player JS")
    parser.add_argument("--output", type=Path, required=True, help="New artifact directory")
    parser.add_argument("--renderer", choices=("svg", "canvas"), action="append")
    args = parser.parse_args()
    if not args.chrome.is_file() or not args.player.is_file() or shutil.which("node") is None:
        parser.error("existing Chrome, player bundle and Node are required")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    cases = prepare_cases(output, tuple(args.renderer or ["svg"]))
    request = output / "cases.json"
    request.write_text(json.dumps({"player": str(args.player.resolve()), "cases": cases}))
    with (
        tempfile.TemporaryDirectory(prefix="quickthumb-lottie-chrome-") as profile,
        (output / "chrome.log").open("w") as log,
    ):
        browser = subprocess.Popen(
            [
                str(args.chrome.resolve()),
                "--headless=new",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-background-networking",
                "--disable-component-update",
                "--force-color-profile=srgb",
                "--remote-debugging-address=127.0.0.1",
                "--remote-debugging-port=0",
                f"--user-data-dir={profile}",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=log,
        )
        try:
            port_file = Path(profile) / "DevToolsActivePort"
            deadline = time.monotonic() + 15
            while not port_file.is_file():
                if browser.poll() is not None or time.monotonic() > deadline:
                    detail = (output / "chrome.log").read_text(errors="replace")[-8000:]
                    raise RuntimeError(f"Chrome did not start; chrome.log tail:\n{detail}")
                time.sleep(0.05)
            captured = subprocess.run(
                [
                    "node",
                    str(Path(__file__).with_suffix(".mjs")),
                    port_file.read_text().splitlines()[0],
                    str(request),
                ],
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
            (output / "driver.log").write_text(captured.stderr)
            if captured.returncode:
                raise RuntimeError(f"Player capture failed: {captured.stderr}")
            observation = json.loads(captured.stdout)
        finally:
            browser.terminate()
            try:
                browser.wait(timeout=5)
            except subprocess.TimeoutExpired:
                browser.kill()
                browser.wait(timeout=5)
    results = []
    for case, observed in zip(cases, observation.pop("cases"), strict=True):
        if observed["name"] != case["name"]:
            raise RuntimeError("Capture order mismatch")
        with Image.open(observed["screenshot"]) as actual:
            results.append({**case, **observed, **assess(case, actual)})
    report = {
        **observation,
        "player_sha256": hashlib.sha256(args.player.read_bytes()).hexdigest(),
        "schema_sha256": hashlib.sha256(
            (
                Path(__file__).resolve().parents[1] / "tests/fixtures/lottie/schema-1.0.1.json"
            ).read_bytes()
        ).hexdigest(),
        "cases": results,
        "passed": all(row["passed"] for row in results),
    }
    (output / "report.json").write_text(json.dumps(report, indent=2))
    print(f"{sum(row['passed'] for row in results)}/{len(results)} observations passed: {output}")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
