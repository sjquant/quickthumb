"""Path transforms repaint device-resolution geometry through the common frame pipeline."""

import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from PIL import Image, ImageChops
from quickthumb import (
    AnimationSpec,
    Canvas,
    ExportPolicy,
    KeyframeSpec,
    LinearGradient,
    OpacityTrack,
    PathLayer,
    PngSequenceOptions,
    PositionTrack,
    RotationTrack,
    ScaleTrack,
    ScaleXTrack,
    ScaleYTrack,
    TimingSpec,
    canvas_json_schema,
)
from quickthumb import _export_video as video
from quickthumb.errors import RenderingError, ValidationError

D = "M2 20C2 2 38 2 38 20C38 38 2 38 2 20Z"


def track(kind, start, end):
    return kind(keyframes=[KeyframeSpec(time=0, value=start), KeyframeSpec(time=1, value=end)])


def motion(*tracks):
    return AnimationSpec.timeline(*tracks, timing=TimingSpec(duration=1), easing="linear")


@pytest.mark.parametrize("paint", ["thin", "dash", "gradient"])
@pytest.mark.parametrize("anchor", [(0, 0), (0.5, 0.5)])
def test_fourfold_scale_matches_large_authored_path(paint, anchor):
    """A 4x animated curve retains the pixels of a path authored at its final size."""
    # Given: a small source and an independently sized final-resolution reference
    style: dict[str, Any] = {"color": None, "stroke": "#E0487080", "stroke_width": 0.6}
    if paint == "dash":
        style.update(stroke_width=2, dash_array=(5, 3), line_cap="round")
    if paint == "gradient":
        style = {
            "color": None,
            "fill": LinearGradient(angle=0, stops=[("#FF000000", 0), ("#4060FFFF", 1)]),
        }
    small = Canvas(240, 240).path(
        D,
        (70, 70),
        40,
        40,
        view_box=(0, 0, 40, 40),
        anchor=anchor,
        animation=motion(track(ScaleTrack, 1, 4)),
        **style,
    )
    offset = (round(70 - 120 * anchor[0]), round(70 - 120 * anchor[1]))
    large = Canvas(240, 240).path(D, offset, 160, 160, view_box=(0, 0, 40, 40), **style)

    # When: sampling the settled transform, including JSON/schema reconstruction
    encoded = small.to_json()
    jsonschema.validate(json.loads(encoded), canvas_json_schema())
    actual = Canvas.from_json(encoded).render_frame(1)
    expected = large.render_frame(0)

    # Then: actual RGBA, including fine edges and translucent color, agrees exactly
    assert actual.getbbox() is not None
    assert actual.tobytes() == expected.tobytes()
    assert video._SlideAnimator(small, {}).frame_at(1).tobytes() == expected.tobytes()


@pytest.mark.parametrize("reflected", [False, True])
def test_translated_off_canvas_source_rotates_and_scales(reflected):
    """An off-canvas path moves into view with anisotropic rotation, reflection and alpha."""
    # Given: source ink is completely outside the original canvas
    sx = -4 if reflected else 4
    canvas = Canvas(240, 220).path(
        D,
        (-100, 70),
        40,
        40,
        "#F0804080",
        anchor=(0.5, 0.5),
        opacity=0.8,
        animation=motion(
            track(PositionTrack, (0, 0), (200, 0)),
            track(ScaleXTrack, 1, sx),
            track(ScaleYTrack, 1, 2),
            track(RotationTrack, 0, 30),
            track(OpacityTrack, 1, 0.5),
        ),
    )
    reference = Canvas(240, 220).path(
        D,
        (40, 50),
        160,
        80,
        "#F0804080",
        view_box=(0, 0, 40, 40),
        rotation=30,
        opacity=0.4,
    )

    # When: independently authored final geometry and the animated source are sampled
    actual = canvas.render_frame(1)
    expected = reference.render_frame(0)

    # Then: visible pixels are recovered and independently sized geometry agrees
    # This closed symmetric curve has identical reflected geometry.
    assert canvas.render_frame(0).getbbox() is None
    difference = ImageChops.difference(actual, expected).getchannel("A").tobytes()
    assert actual.getbbox() is not None
    assert sum(difference) / len(difference) < 0.1
    assert sum(value > 8 for value in difference) / len(difference) < 0.003
    assert max(actual.getchannel("A").tobytes()) == 51
    assert video._SlideAnimator(canvas, {}).frame_at(1).tobytes() == actual.tobytes()
    inspected = canvas.inspect_motion(target="video").slides[0].layers[0].final_state
    assert inspected["position"] == [100, 70]
    assert inspected["rotation"] == 30 and inspected["opacity"] == 0.4


def test_sequence_and_spawn_preserve_sampled_path_pixels(tmp_path):
    """Serial and spawned PNG sequences consume identical unquantized moving-path frames."""
    # Given: fractional-time curved motion with a thin dashed translucent source
    canvas = Canvas(120, 100).path(
        D,
        (20, 15),
        25,
        25,
        None,
        view_box=(0, 0, 40, 40),
        stroke="#30C08090",
        stroke_width=1,
        dash_array=(4, 2),
        animation=motion(track(ScaleTrack, 1, 3), track(RotationTrack, 0, 35)),
    )
    frames = []

    # When: actual files are rendered by independent serial and spawned preparations
    for workers in (1, 2):
        result = canvas.export_png_sequence(
            tmp_path / f"frames-{workers}",
            options=PngSequenceOptions(fps=4, hold=0.25, workers=workers),
        )
        paths = sorted(Path(result.output_directory).glob("*.png"))
        decoded = []
        for path in paths:
            with Image.open(path) as image:
                decoded.append(image.tobytes())
        frames.append(decoded)

    # Then: each exported frame agrees with the instantaneous canonical observation
    assert result.frame_count == 5 and result.duration == 1.25
    assert frames[0] == frames[1]
    assert frames[0] == [canvas.render_frame(t).tobytes() for t in (0, 0.25, 0.5, 0.75, 1)]


def test_source_cache_reuses_paint_without_stale_content(monkeypatch):
    """A held geometry reuses painted pixels while opacity and later authored content stay fresh."""
    from quickthumb import _path_motion

    # Given: only opacity changes, so geometry can retain one painted source
    canvas = Canvas(100, 100).path(
        D,
        (20, 20),
        40,
        40,
        "#FF0000",
        animation=motion(track(OpacityTrack, 0.5, 1)),
    )
    painter = _path_motion.render_path
    paints = []

    def observe(*args):
        paints.append(args[1].color)
        return painter(*args)

    monkeypatch.setattr(_path_motion, "render_path", observe)
    prepared = video._SlideAnimator(canvas, {})

    # When: the same prepared geometry is observed repeatedly, then a new render starts
    first = prepared.frame_at(0.2)
    second = prepared.frame_at(0.4)
    assert paints == ["#FF0000"]
    layer = canvas.layers[0]
    assert isinstance(layer, PathLayer)
    layer.color = "#0000FF"
    changed = canvas.render_frame(0.4)

    # Then: opacity changes without repaint, and changed content never reuses stale ink
    assert max(first.getchannel("A").tobytes()) < max(second.getchannel("A").tobytes())
    pixel = changed.getpixel((40, 40))
    assert isinstance(pixel, tuple) and pixel[:3] == (0, 0, 255)
    assert paints == ["#FF0000", "#0000FF"]


def test_bounded_source_and_document_fallback_are_explicit(tmp_path):
    """Excessive visible source allocations fail and document targets report static path motion."""
    # Given: a visible path whose required 4x source surface exceeds its regional budget
    large = Canvas(1050, 1050).path(
        "M0 0H40V40H0Z",
        (0, 0),
        600,
        600,
        view_box=(0, 0, 40, 40),
        anchor=(0, 0),
        animation=motion(track(ScaleTrack, 1, 2)),
    )
    with pytest.raises(RenderingError, match="bounded visible-source"):
        large.render_frame(1)
    regional = Canvas(1050, 1050).path(
        D,
        (0, 0),
        600,
        600,
        anchor=(0, 0),
        animation=motion(track(ScaleTrack, 1, 2)),
    )
    assert regional.render_frame(1).getbbox() is not None
    canvas = Canvas(80, 80).path(
        D,
        (10, 10),
        40,
        40,
        animation=motion(track(ScaleTrack, 1, 2)),
    )

    # When: exporting a motion path to a document target with no timed source adapter
    result = canvas.export(tmp_path / "path.html")
    rows = result.capability_report

    # Then: the output is authored static, and strict policy preserves prior output
    assert any(row.feature == "scale" and row.fallback == "static" for row in rows)
    html = (tmp_path / "path.html").read_text()
    assert "data:image/png" in html and "data:image/svg" not in html
    destination = tmp_path / "path.svg"
    destination.write_text("keep")
    with pytest.raises(RenderingError):
        canvas.export(destination, policy=ExportPolicy(unsupported_motion="error"))
    assert destination.read_text() == "keep"
    with pytest.raises(ValidationError, match="parenting"):
        PathLayer.model_validate(
            {
                "type": "path",
                "d": D,
                "position": (0, 0),
                "width": 40,
                "height": 40,
                "parent": "controller",
            }
        )
