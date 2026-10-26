"""Closed-form spring clocks through documents, inspection and rendered output."""

import json
from io import BytesIO
from pathlib import Path
from typing import cast
from zipfile import ZipFile

import jsonschema
import pytest
from PIL import Image, ImageChops
from PIL.GifImagePlugin import GifImageFile
from quickthumb import (
    AnimationSpec,
    Canvas,
    ExportPolicy,
    KeyframeSpec,
    PositionTrack,
    SpringEasing,
    TimingSpec,
    canvas_json_schema,
)
from quickthumb.errors import RenderingError, ValidationError
from quickthumb.models import ImageLayer, TextLayer
from quickthumb.motion import easing_value, inspect_motion, validate_export


@pytest.mark.parametrize(
    ("damping", "midpoint"),
    [(10, 1.0745905665950333), (20, 0.9595723180054871), (30, 0.826595349759536)],
)
def test_spring_response_regimes(damping, midpoint):
    """A unit step has its analytic midpoint in each damping regime and exact endpoints."""
    # Given: springs with identical response rates, expressed at two mass scales
    curve = SpringEasing(stiffness=100, damping=damping, mass=1)
    scaled = SpringEasing(stiffness=200, damping=2 * damping, mass=2)

    # When: querying times directly without a prior frame
    actual = [easing_value(curve, time) for time in (1, 0.5, 0, 0.5)]

    # Then: critical damping does not overshoot, and proportional physical parameters agree
    assert actual == pytest.approx([1, midpoint, 0, midpoint])
    assert easing_value(scaled.model_dump(), 0.5) == pytest.approx(midpoint)


def spring_scene(*, keyframe=False) -> Canvas:
    spring = SpringEasing()
    return (
        Canvas(96, 96)
        .background(color="#000000")
        .shape(
            "rectangle",
            (5, 5),
            8,
            8,
            "#FFFFFF",
            animation=AnimationSpec.timeline(
                PositionTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value=(0, 0), easing=spring if keyframe else None),
                        KeyframeSpec(time=1, value=(40, 0)),
                    ]
                ),
                easing=None if keyframe else spring,
                timing=TimingSpec(duration=1),
            ),
        )
    )


@pytest.mark.parametrize("keyframe", [False, True])
def test_spring_json_seek_and_sequential_export(keyframe):
    """An authored spring survives JSON and produces the same sought and encoded GIF frames."""
    # Given: a spring on the full animation or its first keyframe interval
    scene = spring_scene(keyframe=keyframe)
    document = scene.to_json()
    jsonschema.validate(json.loads(document), canvas_json_schema())
    restored = Canvas.from_json(document)

    # When: decoding a sequential export after seeking in reverse order
    sought = {index: restored.render_frame(index / 10) for index in reversed(range(11))}
    elapsed = 0
    with cast(GifImageFile, Image.open(BytesIO(restored.to_gif(fps=10, hold=0.1)))) as gif:
        for index in range(gif.n_frames):
            gif.seek(index)
            # Then: the encoded frame's displayed time selects the same canonical pixels
            assert gif.convert("RGBA").tobytes() == sought[round(elapsed / 100)].tobytes()
            elapsed += gif.info["duration"]
    assert elapsed == 1100
    assert sought[10].getpixel((45, 5)) == (255, 255, 255, 255)


@pytest.mark.parametrize("preset", [False, True])
def test_spring_inspection_and_document_fallback(tmp_path, preset):
    """HTML and PPTX declare static spring fallback while inspection reports the actual curve."""
    # Given: a spring-authored document and strict policy
    scene = (
        Canvas(96, 96).shape(
            "rectangle",
            (5, 5),
            8,
            8,
            "#FFFFFF",
            animation=AnimationSpec.slide(
                from_="left", distance=40, duration=1, easing=SpringEasing()
            ),
        )
        if preset
        else spring_scene()
    )
    strict = ExportPolicy(unsupported_motion="error")

    # When: inspecting the spring and exporting document formats
    report = inspect_motion(scene, fps=2)
    assert any(item.feature == "spring" for item in report.capabilities)
    layer = next(layer for layer in report.slides[0].layers if layer.events)
    assert layer.samples[1]["position"][0] > layer.final_state["position"][0]
    for target in ("html", "pptx"):
        diagnostic = next(
            item for item in validate_export(scene, target) if item.feature == "spring"
        )
        assert diagnostic.fallback == "static"
        with pytest.raises(RenderingError, match="export policy"):
            scene.export(tmp_path / f"strict.{target}", policy=strict)
        assert not (tmp_path / f"strict.{target}").exists()

    # Then: document output does not substitute a different animation clock
    assert "@keyframes qt-" not in scene.to_html()
    with ZipFile(BytesIO(scene.to_pptx())) as archive:
        assert b"<p:timing" not in archive.read("ppt/slides/slide1.xml")


def test_spring_example_snapshot():
    """The three damping regimes render their documented intermediate positions."""
    from examples.spring_motion import build_scene

    # Given: a committed midpoint image of the example
    with Image.open(Path(__file__).parent / "snapshots/spring_motion.png") as expected:
        # When/Then: rendering the example midpoint reproduces its RGBA pixels
        assert build_scene().render_frame(0.5).tobytes() == expected.convert("RGBA").tobytes()


def test_invalid_spring_response_is_rejected_before_compilation():
    """Finite spring inputs that overflow their response rates are rejected at authoring time."""
    # Given: finite inputs whose ratio overflows
    with pytest.raises(ValidationError, match="response rates"):
        SpringEasing(stiffness=1e308, mass=1e-308)


def test_logo_wordmark_entrance_overshoots_then_holds_authored_layout():
    """The application example moves real image/text ink and encodes its settled hold."""
    from examples.spring_entrance import build_scene

    scene = Canvas.from_json(build_scene().to_json())
    background = Image.new("RGB", (640, 240), "#F8F7F3")
    assert ImageChops.difference(scene.render_frame(0).convert("RGB"), background).getbbox() is None
    authored = build_scene()
    authored.layers = [
        layer.model_copy(update={"animation": None})
        if isinstance(layer, (ImageLayer, TextLayer))
        else layer
        for layer in authored.layers
    ]
    overshoot, settled = scene.render_frame(0.6), scene.render_frame(1.5)
    assert (
        settled.tobytes() == authored.render_frame(0).tobytes() == scene.render_frame(2).tobytes()
    )

    def ink_bounds(frame, box):
        crop = frame.convert("RGB").crop(box)
        mask = ImageChops.difference(crop, background.crop(box)).convert("L")
        bounds = mask.point(lambda value: 255 if value > 8 else 0).getbbox()
        assert bounds is not None
        return bounds

    regions = [(0, 0, 175, 240), (175, 0, 640, 240)]
    for box in regions:
        assert ink_bounds(overshoot, box)[0] > ink_bounds(settled, box)[0]

    elapsed, decoded_overshoot = 0, None
    with cast(GifImageFile, Image.open(BytesIO(scene.to_gif(fps=20, hold=0.5)))) as gif:
        for index in range(gif.n_frames):
            gif.seek(index)
            delay = gif.info["duration"]
            if elapsed <= 600 < elapsed + delay:
                decoded_overshoot = gif.convert("RGBA")
            elapsed += delay
        final = gif.convert("RGBA")
    assert elapsed == 2000 and decoded_overshoot is not None
    for box in regions:
        assert ink_bounds(decoded_overshoot, box) == pytest.approx(
            ink_bounds(overshoot, box), abs=1
        )
        assert ink_bounds(final, box) == pytest.approx(ink_bounds(settled, box), abs=1)
