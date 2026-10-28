"""Observe real HTML stage pixels with an explicitly selected, task-owned Chrome.

Run from the repository root with PYTHONPATH=. No browser/library installation is
performed. The JSON and PNGs are validation artifacts, not an export-policy API.
"""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from PIL import Image
from quickthumb import AnimationSpec, Canvas, Deck
from quickthumb._diff import DEFAULT_HASH_SIZE, _hamming_distance, _perceptual_hash_image
from quickthumb._svg_fidelity import _pixel_measurements, _visible_rgba
from quickthumb.transitions import Cut


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--chrome", type=Path, required=True, help="Chrome executable, never a profile"
    )
    parser.add_argument("--output", type=Path, required=True, help="New artifact directory")
    args = parser.parse_args()
    if not args.chrome.is_file() or shutil.which("node") is None:
        parser.error("an existing Chrome executable and Node with built-in WebSocket are required")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    cases = prepare_cases(output)
    request = output / "cases.json"
    request.write_text(json.dumps(cases, indent=2), encoding="utf-8")
    with (
        tempfile.TemporaryDirectory(prefix="quickthumb-html-chrome-") as profile,
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
                    raise RuntimeError("task-owned Chrome did not start; inspect chrome.log")
                time.sleep(0.05)
            port = int(port_file.read_text().splitlines()[0])
            captured = subprocess.run(
                ["node", str(Path(__file__).with_suffix(".mjs")), str(port), str(request)],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            (output / "driver.log").write_text(captured.stderr, encoding="utf-8")
            if captured.returncode:
                raise RuntimeError(f"Browser capture failed: {captured.stderr}")
            observation = json.loads(captured.stdout)
        finally:
            browser.terminate()
            try:
                browser.wait(timeout=5)
            except subprocess.TimeoutExpired:
                browser.kill()
                browser.wait(timeout=5)
    results = []
    for case, observed in zip(cases, observation["cases"], strict=True):
        with (
            Image.open(case["reference"]) as expected,
            Image.open(observed["screenshot"]) as actual,
        ):
            expected, actual = expected.convert("RGBA"), actual.convert("RGBA")
            metrics = compare(expected, actual, case["limits"])
            metrics["regions"] = [
                {
                    **region,
                    **compare(
                        expected.crop(region["box"]), actual.crop(region["box"]), region["limits"]
                    ),
                }
                for region in case["regions"]
            ]
            if any(region["verdict"] == "out_of_policy" for region in metrics["regions"]):
                metrics["verdict"] = "out_of_policy"
        results.append({**case, **observed, **metrics})
    report = {
        "scope": "fixture-specific HTML browser observations; no universal fidelity guarantee",
        "platform": platform.platform(),
        "browser": observation["browser"],
        "node": observation["node"],
        "cases": results,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for result in results:
        failed_regions = [
            row["name"] for row in result["regions"] if row["verdict"] == "out_of_policy"
        ]
        print(
            f"{result['name']}: {result['verdict']} pixel_ratio={result.get('pixel_diff_ratio')} "
            f"hash={result['hash_similarity']} failed_regions={failed_regions}"
        )
    unexpected = [row["name"] for row in results if row["verdict"] not in row["expected_verdicts"]]
    for row in results:
        if row.get("omit") and not any(
            region["name"] == row["omit"] and region["verdict"] == "out_of_policy"
            for region in row["regions"]
        ):
            unexpected.append(row["name"])
    if unexpected:
        raise SystemExit(f"HTML fidelity checks failed; inspect {output / 'report.json'}")


def prepare_cases(output: Path) -> list[dict]:
    def content(width: int, height: int) -> Canvas:
        return (
            Canvas(width, height)
            .background(color="#F8F7F3")
            .text(
                "Quickthumb",
                font="assets/fonts/Roboto-Regular.ttf",
                size=20,
                position=(12, 12),
                motion_key="text",
            )
            .shape("ellipse", (12, 55), 55, 32, "#159A8C", motion_key="native-shape")
            .image(
                "tests/fixtures/sample_image.jpg", (90, 55), width=55, height=40, motion_key="image"
            )
            .group(
                [
                    {
                        "type": "shape",
                        "shape": "rectangle",
                        "width": 45,
                        "height": 28,
                        "color": "#E75A40",
                    }
                ],
                position=(12, 110),
                id="masked",
                motion_key="mask",
                mask={"shape": "ellipse", "position": (12, 110), "width": 45, "height": 28},
            )
        )

    wide, tall = content(320, 180), content(180, 280)
    receipts = {"canvas.html": wide.export(output / "canvas.html")}
    receipts["deck.html"] = (
        Deck()
        .slide(wide, transition=Cut(duration=0.01))
        .slide(tall, transition=Cut(duration=0.01))
        .export(output / "deck.html")
    )
    animation = (
        Canvas(160, 100)
        .background(color="#000000")
        .shape(
            "rectangle",
            (20, 20),
            80,
            50,
            "#FF0000",
            animation=AnimationSpec.fade(duration=10, easing="linear", trigger="on_click"),
        )
    )
    receipts["animation.html"] = animation.export(output / "animation.html")
    receipts["negative.html"] = (
        Canvas(320, 180).background(color="#FF00FF").export(output / "negative.html")
    )
    # Eight percent permits edge/font rasterization differences in this small
    # mixed fixture. It is not a budget for arbitrary documents or environments.
    mixed = {"pixel_tolerance": 16, "max_different_pixel_ratio": 0.08, "min_hash_similarity": 0.94}
    exact_fade = {"pixel_tolerance": 1, "max_different_pixel_ratio": 0, "min_hash_similarity": 1}
    # Local hashes protect small features which a whole-stage average can miss.
    regions = [
        {
            "name": "text",
            "box": [12, 8, 140, 38],
            "limits": {
                "pixel_tolerance": 16,
                "max_different_pixel_ratio": 0.20,
                "min_hash_similarity": 0.95,
            },
        },
        {
            "name": "native-shape",
            "box": [12, 55, 67, 87],
            "limits": {
                "pixel_tolerance": 16,
                "max_different_pixel_ratio": 0.02,
                "min_hash_similarity": 0.98,
            },
        },
        {
            "name": "image",
            "box": [90, 55, 145, 95],
            "limits": {
                "pixel_tolerance": 0,
                "max_different_pixel_ratio": 0,
                "min_hash_similarity": 1,
            },
        },
        {"name": "mask", "box": [12, 110, 57, 138], "limits": exact_fade},
    ]
    cases = []
    for name, scene, document, slide, instant, limits, verdicts in [
        ("canvas-mixed", wide, "canvas.html", 0, None, mixed, ["exact", "tolerated"]),
        ("deck-wide", wide, "deck.html", 0, None, mixed, ["exact", "tolerated"]),
        ("deck-tall", tall, "deck.html", 1, None, mixed, ["exact", "tolerated"]),
        ("fade-initial", animation, "animation.html", 0, 0, exact_fade, ["exact", "tolerated"]),
        ("fade-midpoint", animation, "animation.html", 0, 5, exact_fade, ["exact", "tolerated"]),
        ("fade-settled", animation, "animation.html", 0, 10, exact_fade, ["exact", "tolerated"]),
        ("wrong-document-control", wide, "negative.html", 0, None, mixed, ["out_of_policy"]),
    ]:
        capture = scene.sample() if instant is None else scene.sample(time=instant, hold=0)
        reference = output / f"{name}-canonical.png"
        capture.frames[0].to_image().save(reference)
        cases.append(
            {
                "name": name,
                "url": (output / document).as_uri(),
                "slide": slide,
                "width": scene.width,
                "height": scene.height,
                "time": instant,
                "expects_embedded_font": document in {"canvas.html", "deck.html"},
                "reference": str(reference),
                "screenshot": str(output / f"{name}-browser.png"),
                "canonical_environment": capture.environment.model_dump(mode="json"),
                "capability_report": [
                    row.model_dump(mode="json") for row in receipts[document].capability_report
                ],
                "asset_manifest": [
                    row.model_dump(mode="json") for row in receipts[document].asset_manifest
                ],
                "regions": regions if instant is None else [],
                "limits": limits,
                "expected_verdicts": verdicts,
            }
        )
    for baseline in (cases[0], cases[2]):
        for region in regions:
            name = f"{baseline['name']}-missing-{region['name']}"
            cases.append(
                {
                    **baseline,
                    "name": name,
                    "omit": region["name"],
                    "screenshot": str(output / f"{name}-browser.png"),
                    "expected_verdicts": ["out_of_policy"],
                }
            )
    return cases


def compare(expected: Image.Image, actual: Image.Image, limits: dict) -> dict:
    expected, actual = _visible_rgba(expected), _visible_rgba(actual)
    similarity = (
        1
        - _hamming_distance(
            _perceptual_hash_image(expected, DEFAULT_HASH_SIZE),
            _perceptual_hash_image(actual, DEFAULT_HASH_SIZE),
        )
        / DEFAULT_HASH_SIZE**2
    )
    metrics = (
        _pixel_measurements(expected, actual, limits["pixel_tolerance"])
        if expected.size == actual.size
        else {}
    )
    accepted = (
        expected.size == actual.size
        and metrics["pixel_diff_ratio"] <= limits["max_different_pixel_ratio"]
        and similarity >= limits["min_hash_similarity"]
    )
    verdict = (
        ("exact" if metrics["max_channel_delta"] == 0 else "tolerated")
        if accepted
        else "out_of_policy"
    )
    return {
        "verdict": verdict,
        "actual_size": list(actual.size),
        "hash_similarity": similarity,
        **metrics,
    }


if __name__ == "__main__":
    main()
