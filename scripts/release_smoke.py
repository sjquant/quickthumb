#!/usr/bin/env python3
"""Bounded, offline installed-wheel smoke. Run from outside the source checkout.

Only stdlib and the selected quickthumb installation are needed. The core profile
requires extras to be genuinely absent; full requires all four release extras,
FFmpeg and ffprobe. report.json records failures as well as successful checks.
These geometry checks are deliberately not a typography/visual-fidelity suite.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.resources
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

OPTIONAL = {"pdf": "reportlab", "pptx": "pptx", "svg": "cairosvg", "cli": "typer"}
SIZE = (128, 96)
RED = (255, 0, 0)
BLUE = (0, 0, 255)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def expect_guidance(action, guidance):
    try:
        action()
    except Exception as error:
        require(guidance.lower() in str(error).lower(), f"Unhelpful error: {error}")
        return str(error)
    raise AssertionError(f"Expected failure mentioning {guidance}")


def fixtures():
    from quickthumb import Canvas, Deck, transitions

    canvas = (
        Canvas(*SIZE).background(color="#0000ff").shape("rectangle", (32, 24), 64, 48, "#ff0000")
    )
    second = (
        Canvas(*SIZE).background(color="#00ff00").shape("rectangle", (32, 24), 64, 48, "#0000ff")
    )
    return canvas, Deck(*SIZE, transition=transitions.Cut(advance_after=0.4)).slide(
        canvas, duration=0.4
    ).slide(second, duration=0.4)


def assert_pixels(image, center=RED, background=BLUE, tolerance=0):
    require(image.size == SIZE, f"Wrong dimensions: {image.size}")
    rgb = image.convert("RGB")
    for position, expected in (((64, 48), center), ((4, 4), background)):
        actual = rgb.getpixel(position)
        require(
            all(abs(a - b) <= tolerance for a, b in zip(actual, expected, strict=True)),
            f"Wrong pixels at {position}: {actual}, expected {expected}",
        )


def assert_svg(path):
    require(path.is_file() and path.stat().st_size > 0, f"Missing SVG output: {path}")
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    require(root.tag == "{http://www.w3.org/2000/svg}svg", "Invalid SVG root")
    require(len(root) > 0, "Empty SVG")
    require(root.attrib.get("width") == str(SIZE[0]), "SVG width")
    require(root.attrib.get("height") == str(SIZE[1]), "SVG height")


def check_documents(output):
    from PIL import Image
    from quickthumb import GifOptions

    canvas, deck = fixtures()
    details = {}
    for name, document, count in (("canvas", canvas, 1), ("deck", deck, 2)):
        require(document.validate().valid, f"{name} validation failed")
        still = document.sample()
        require(len(still.frames) == count, f"{name} still frame count")
        assert_pixels(still.frames[0].to_image())
        (output / f"{name}-sample.json").write_text(still.model_dump_json(), encoding="utf-8")
        for extension in ("png", "svg", "html", "gif"):
            if name == "deck" and extension == "svg":
                details["deck.svg"] = {
                    "unsupported_guidance": expect_guidance(
                        lambda document=document: document.export(output / "deck.svg"),
                        "Render slides individually",
                    )
                }
                for index, slide in enumerate(document.slides):
                    result = slide.export(output / f"deck-slide-{index}.svg")
                    paths = [Path(path) for path in result.written_paths]
                    require(len(paths) == 1, "SVG page count")
                    assert_svg(paths[0])
                continue
            result = document.export(
                output / f"{name}.{extension}",
                animation=GifOptions(fps=10) if extension == "gif" else None,
            )
            paths = [Path(path) for path in result.written_paths]
            require(
                paths and all(path.is_file() and path.stat().st_size for path in paths),
                f"{name}.{extension} missing output",
            )
            details[f"{name}.{extension}"] = result.model_dump(mode="json")
            if extension == "png":
                require(len(paths) == count, "Raster page count")
                for index, path in enumerate(paths):
                    with Image.open(path) as image:
                        assert_pixels(
                            image,
                            RED if index == 0 else BLUE,
                            BLUE if index == 0 else (0, 255, 0),
                        )
                        require(
                            image.convert("RGBA").tobytes() == still.frames[index].to_bytes(),
                            "PNG differs from canonical settled sample",
                        )
            elif extension == "svg":
                require(len(paths) == count, "SVG page count")
                for path in paths:
                    assert_svg(path)
            elif extension == "html":
                html = paths[0].read_text(encoding="utf-8")
                require("<!doctype html>" in html.lower(), "Missing packaged HTML template")
                require("{{" not in html, "Unexpanded HTML template")
                require(html.count('class="qt-stage"') == count, "HTML stage count")
                for resource in ("base.css", "timeline.js"):
                    content = (
                        importlib.resources.files("quickthumb.html")
                        .joinpath(resource)
                        .read_text(encoding="utf-8")
                    )
                    require(content.strip() in html, f"Missing embedded {resource}")
                runtime = "deck_runtime.js" if name == "deck" else "canvas_runtime.js"
                content = (
                    importlib.resources.files("quickthumb.html")
                    .joinpath(runtime)
                    .read_text(encoding="utf-8")
                )
                require(
                    content.replace("{{ responsive }}", "true").strip() in html,
                    f"Missing embedded {runtime}",
                )
            else:
                with Image.open(paths[0]) as image:
                    assert_pixels(image)
                    duration = 0
                    frame_count = getattr(image, "n_frames", 1)
                    for index in range(frame_count):
                        image.seek(index)
                        duration += image.info.get("duration", 0)
                    expected = 800 if name == "deck" else 3000
                    require(abs(duration - expected) <= 20, f"GIF timing: {duration} != {expected}")
                    if name == "deck":
                        require(frame_count >= 2, "Deck GIF lost slide change")
                        assert_pixels(image, BLUE, (0, 255, 0))
    sampled = deck.sample(time=[0.1, 0.5])
    require(abs(sampled.duration - 0.8) < 1e-6, "Deck canonical duration")
    require([frame.time for frame in sampled.frames] == [0.1, 0.5], "Sample timestamps")
    assert_pixels(sampled.frames[0].to_image())
    assert_pixels(sampled.frames[1].to_image(), BLUE, (0, 255, 0))
    return details


def core_guidance(output, svg):
    """Each optional export without its extra must fail with the install hint."""
    from quickthumb import Canvas

    canvas, _ = fixtures()
    messages = {}
    for extra in ("pdf", "pptx"):
        messages[extra] = expect_guidance(
            lambda extra=extra: canvas.export(output / f"missing.{extra}"),
            f"quickthumb[{extra}]",
        )
    messages["svg"] = expect_guidance(
        lambda: Canvas(*SIZE).svg(str(svg), (0, 0)).sample(), "quickthumb[svg]"
    )
    return messages


def check_profile(profile, output):
    availability = {
        extra: importlib.util.find_spec(module) is not None for extra, module in OPTIONAL.items()
    }
    require(
        all(value == (profile == "full") for value in availability.values()),
        f"{profile} needs {'present' if profile == 'full' else 'absent'} extras: {availability}",
    )
    svg = output / "input.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="128" height="96">'
        '<rect width="128" height="96" fill="red"/></svg>',
        encoding="utf-8",
    )
    from quickthumb import Canvas

    entrypoint = Path(sys.executable).parent / (
        "quickthumb.exe" if os.name == "nt" else "quickthumb"
    )
    require(entrypoint.is_file(), "Installed quickthumb console entry point is missing")
    if profile == "core":
        messages = core_guidance(output, svg)
        cli = subprocess.run(
            [str(entrypoint)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        require(cli.returncode != 0 and "quickthumb[cli]" in cli.stderr, "Missing CLI guidance")
        messages["cli"] = cli.stderr.strip()
        return {"availability": availability, "guidance": messages}
    image = Canvas(*SIZE).svg(str(svg), (0, 0)).sample().frames[0].to_image()
    assert_pixels(image, RED, RED)
    cli = subprocess.run(
        [str(entrypoint), "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    require(cli.returncode == 0 and "Usage" in cli.stdout, f"CLI failed: {cli.stderr}")
    return {"availability": availability, "svg_rasterization": True, "cli_help": True}


def check_missing_ffmpeg(output):
    env = os.environ.copy()
    with tempfile.TemporaryDirectory() as directory:
        env.update(PATH=directory, QUICKTHUMB_FFMPEG=str(Path(directory) / "does-not-exist"))
        code = (
            "from quickthumb import Canvas; "
            f"Canvas(128,96).background(color='#ff0000').export({str(output / 'missing.mp4')!r})"
        )
        result = subprocess.run(
            [sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=30
        )
    require(
        result.returncode != 0
        and "install ffmpeg" in result.stderr.lower()
        and "QUICKTHUMB_FFMPEG" in result.stderr,
        "Missing actionable FFmpeg guidance",
    )
    return {"isolated_process": True, "guidance": result.stderr.splitlines()[-1]}


def check_full(output):
    from quickthumb import VideoOptions

    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg is None or ffprobe is None:
        raise AssertionError("Full smoke requires ffmpeg and ffprobe on PATH")
    results = {}
    for name, document, pages in (("canvas", fixtures()[0], 1), ("deck", fixtures()[1], 2)):
        for extension in ("pdf", "pptx", "mp4", "webm"):
            path = output / f"{name}.{extension}"
            document.export(
                path, animation=VideoOptions(fps=10) if extension in ("mp4", "webm") else None
            )
            data = path.read_bytes()
            if extension == "pdf":
                require(
                    data.startswith(b"%PDF-") and b"%%EOF" in data[-1024:], "Invalid PDF envelope"
                )
                import re

                require(len(re.findall(rb"/Type\s*/Page\b", data)) == pages, "PDF page count")
                results[f"{name}.pdf"] = {"coverage": "signature, EOF, page count", "pages": pages}
            elif extension == "pptx":
                with zipfile.ZipFile(path) as archive:
                    require(archive.testzip() is None, "Corrupt PPTX ZIP")
                    slides = [
                        item
                        for item in archive.namelist()
                        if item.startswith("ppt/slides/slide") and item.endswith(".xml")
                    ]
                    require(len(slides) == pages, "PPTX slide count")
                    for slide in slides:
                        root = ET.fromstring(archive.read(slide))
                        require(
                            len(
                                root.findall(
                                    ".//{http://schemas.openxmlformats.org/presentationml/2006/main}sp"
                                )
                            )
                            >= 1,
                            "PPTX lost native geometry",
                        )
                results[f"{name}.pptx"] = {
                    "coverage": "ZIP integrity, slide XML, native shape",
                    "slides": pages,
                }
            else:
                probe = subprocess.run(
                    [
                        ffprobe,
                        "-v",
                        "error",
                        "-show_streams",
                        "-show_format",
                        "-of",
                        "json",
                        str(path),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                info = json.loads(probe.stdout)
                stream = next(item for item in info["streams"] if item["codec_type"] == "video")
                require((stream["width"], stream["height"]) == SIZE, "Video dimensions")
                require(
                    stream["codec_name"] == ("h264" if extension == "mp4" else "vp9"), "Video codec"
                )
                expected = 0.8 if name == "deck" else 3.0
                require(abs(float(info["format"]["duration"]) - expected) <= 0.15, "Video duration")
                raw = subprocess.run(
                    [
                        ffmpeg,
                        "-v",
                        "error",
                        "-i",
                        str(path),
                        "-f",
                        "rawvideo",
                        "-pix_fmt",
                        "rgb24",
                        "-",
                    ],
                    check=True,
                    capture_output=True,
                    timeout=30,
                ).stdout
                frame_bytes = SIZE[0] * SIZE[1] * 3
                require(
                    len(raw) % frame_bytes == 0 and len(raw) >= frame_bytes, "Undecodable video"
                )
                require(
                    abs(len(raw) // frame_bytes - round(expected * 10)) <= 1, "Video frame count"
                )
                from PIL import Image

                assert_pixels(Image.frombytes("RGB", SIZE, raw[:frame_bytes]), tolerance=15)
                if name == "deck":
                    assert_pixels(
                        Image.frombytes("RGB", SIZE, raw[-frame_bytes:]),
                        BLUE,
                        (0, 255, 0),
                        tolerance=15,
                    )
                results[f"{name}.{extension}"] = {
                    "codec": stream["codec_name"],
                    "duration": info["format"]["duration"],
                    "decoded_frames": len(raw) // frame_bytes,
                }
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("core", "full"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "profile": args.profile,
        "coverage": "bounded geometry/structure smoke, not full visual fidelity",
        "checks": [],
        "python": sys.version,
    }
    import quickthumb

    assert quickthumb.__file__ is not None
    report.update(
        package_path=str(Path(quickthumb.__file__).resolve()),
        version=importlib.metadata.version("quickthumb"),
    )
    checks = [
        ("profile_dependencies", lambda: check_profile(args.profile, output)),
        ("canonical_exports", lambda: check_documents(output)),
        ("missing_ffmpeg", lambda: check_missing_ffmpeg(output)),
    ]
    if args.profile == "full":
        checks.append(("full_exports", lambda: check_full(output)))
    for name, check in checks:
        try:
            detail = check()
            report["checks"].append({"name": name, "status": "passed", "detail": detail})
        except Exception as error:
            report["checks"].append(
                {"name": name, "status": "failed", "error": f"{type(error).__name__}: {error}"}
            )
    report["status"] = (
        "passed" if all(check["status"] == "passed" for check in report["checks"]) else "failed"
    )
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "report": str(output / "report.json")}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
