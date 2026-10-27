"""Bounded path correspondence shares canonical clocks and adaptive stroke/fill painting."""

import base64
import json

import jsonschema
import pytest
from PIL import Image, ImageSequence
from quickthumb import (
    AnimationSpec,
    Canvas,
    ExportPolicy,
    GifOptions,
    ImageSequenceOptions,
    KeyframeSpec,
    LinearGradient,
    OpacityTrack,
    PathLayer,
    PathMorphTrack,
    ScaleTrack,
    TimingSpec,
    canvas_json_schema,
)
from quickthumb import _export_video as video
from quickthumb.errors import RenderingError, ValidationError
from quickthumb.motion import compile_timeline

from tests.test_path_motion import motion, track

A = "M10 10H50V50H10Z"
B = "M20 20H60V60H20Z"
MID = "M15 15H55V55H15Z"


def scene(data=A, animation=None, **style):
    return Canvas(180, 160).path(
        data,
        (10, 10),
        140,
        120,
        None,
        view_box=(0, 0, 80, 80),
        fill=LinearGradient(angle=20, stops=[("#FF604080", 0), ("#3060FFFF", 1)]),
        stroke="#C0E0FF90",
        stroke_width=1.5,
        animation=animation,
        **style,
    )


def test_sampled_morph_matches_independent_geometry():
    """Samples retain authored endpoints and paint an independently authored midpoint."""
    # Given: a translated closed contour, including JSON/schema reconstruction
    animation = motion(track(PathMorphTrack, A, B))
    canvas = scene(animation=animation)
    encoded = canvas.to_json()
    jsonschema.validate(json.loads(encoded), canvas_json_schema())
    canvas = Canvas.from_json(encoded)
    prepared = video._SlideAnimator(canvas, {})

    # When: direct and retained painters revisit endpoints and the midpoint
    for instant, data in ((0, A), (0.5, MID), (1, B), (0.5, MID), (0, A)):
        expected = scene(data).render_frame(0)
        actual = canvas.render_frame(instant)

        # Then: complete translucent RGBA agrees with independent static geometry
        assert actual.tobytes() == expected.tobytes()
        assert prepared.frame_at(instant).tobytes() == expected.tobytes()
    inspected = canvas.inspect_motion(fps=2).slides[0].layers[0]
    assert inspected.initial_state["path_morph"] == A
    assert inspected.final_state["path_morph"] == B
    assert inspected.static_state["path_morph"] == A
    assert canvas.inspect_motion(fps=2).slides[0].layers[0] == inspected
    assert isinstance(canvas.layers[0], PathLayer) and canvas.layers[0].d == A


def test_closed_start_alignment_preserves_holes():
    """Equivalent closed contours retain nested fill when authored start vertices differ."""
    # Given: an outer square and a hole, each target authored from its opposite corner
    first = A + " M20 20H40V40H20Z"
    last = "M50 50H10V10H50Z M40 40H20V20H40Z"
    canvas = scene(first, motion(track(PathMorphTrack, first, last)))

    # When/Then: cyclic correspondence retains the actual hole and closing stroke joins
    expected = scene(first).render_frame(0)
    assert canvas.render_frame(0.5).tobytes() == expected.tobytes()
    assert compile_timeline(canvas.layers[0].animation).sample(1).path_morph == last


def test_open_morph_and_local_hold_clock():
    """Open paths retain direction while delayed holds and easing use local time."""
    # Given: an authored open curve before a delayed morph with an outgoing hold
    first, middle, last = "M0 20H40", "M0 30H40", "M0 50H40"
    phase = PathMorphTrack(
        keyframes=[
            KeyframeSpec(time=0, value=first, hold=True),
            KeyframeSpec(time=0.5, value=middle, easing="ease_in"),
            KeyframeSpec(time=1, value=last),
        ]
    )
    animation = AnimationSpec.timeline(
        phase, timing=TimingSpec(start=1, duration=1), easing="linear"
    )
    canvas = scene("M0 10H40", animation)

    # When/Then: the authored source, exact hold boundary, and eased midpoint paint as authored
    for instant, data in (
        (0, "M0 10H40"),
        (1.25, first),
        (1.5, middle),
        (1.75, "M0 35H40"),
        (2, last),
    ):
        assert canvas.render_frame(instant).tobytes() == scene(data).render_frame(0).tobytes()
    assert compile_timeline(animation).sample(1.5).path_morph == middle


def test_curved_endpoints_repaint_at_device_density():
    """A transformed morph retains exact target curve pixels at the final device density."""
    # Given: compatible open quadratics with simultaneous scale and opacity tracks
    first, last = "M0 20Q20 0 40 20", "M0 20Q20 40 40 20"
    animation = motion(
        track(PathMorphTrack, first, last), track(ScaleTrack, 1, 3), track(OpacityTrack, 1, 0.5)
    )
    canvas = Canvas(240, 180).path(
        first,
        (10, 10),
        60,
        45,
        None,
        view_box=(0, 0, 40, 40),
        stroke="#30C08090",
        stroke_width=0.7,
        anchor=(0, 0),
        animation=animation,
    )
    reference = Canvas(240, 180).path(
        last,
        (10, 10),
        180,
        135,
        None,
        view_box=(0, 0, 40, 40),
        stroke="#30C08090",
        stroke_width=0.7,
        opacity=0.5,
    )

    # When/Then: the settled target stays an authored quadratic through adaptive painting
    assert canvas.render_frame(1).tobytes() == reference.render_frame(0).tobytes()
    assert compile_timeline(animation).sample(0).path_morph == first
    assert compile_timeline(animation).sample(1).path_morph == last
    assert canvas.render_frame(0.5).getbbox() is not None


@pytest.mark.parametrize(
    ("first", "last", "reason"),
    [
        (A, 42, "SVG d strings"),
        (A, "M0 0" + " ".join(f"L{x} 0" for x in range(1, 257)), "256-point"),
        (A, " ".join(f"M{x} 0h1v1h-1Z" for x in range(0, 51, 3)), "4096 sampled"),
        (A, B + " M65 65H75V75H65Z", "contour count"),
        (A, "M20 20H60V60H20", "closedness"),
        (A, "M20 20V60H60V20Z", "winding"),
        (A + " M20 20H30V30H20Z", A + " M60 60H70V70H60Z", "nesting"),
        (A, "M10 10L10 10", "degenerate"),
        (A, "M0 0L40 40L0 40L40 0Z", "signed area"),
        (A, "M0 0H40V40H0Z M40 0H60V20H40Z", "ambiguous"),
        ("M0 0H10V10", "M0 0H1000V1000", "1/4 local unit"),
    ],
)
def test_incompatible_morphs_fail_before_render(first, last, reason):
    """Unsupported topology, degenerate contours and insufficient accuracy fail admission."""
    # Given/When/Then: typed keyframes reject the incompatible pair before any frame or export
    with pytest.raises(ValidationError, match=reason):
        track(PathMorphTrack, first, last)


def test_constant_morph_refuses_retraced_edges():
    """A constant morph track still rejects an adjacent edge that retraces the same segment."""
    # Given/When/Then: single-key geometry receives topology admission without requiring an interval
    with pytest.raises(ValidationError, match="overlapping adjacent edges"):
        PathMorphTrack(keyframes=[KeyframeSpec(time=0, value="M0 0H40H0")])


def test_sampled_topology_change_is_explicit():
    """Moving contours fail explicitly when their sampled intermediate boundaries touch."""
    # Given: disjoint squares exchanging positions with unchanged authored endpoint topology
    first = "M0 0H10V10H0Z M30 0H40V10H30Z"
    last = "M30 0H40V10H30Z M0 0H10V10H0Z"
    canvas = scene(first, motion(track(PathMorphTrack, first, last)))

    # When/Then: ambiguous sampled geometry is refused before it reaches the painter
    with pytest.raises(RenderingError, match="ambiguous"):
        canvas.render_frame(0.5)


def test_non_path_rejects_morph_and_documents_report_static(tmp_path):
    """Morph is Path-only and document targets retain declared authored-static output."""
    # Given: a valid typed morph and a pre-existing strict export destination
    animation = motion(track(PathMorphTrack, A, B))
    with pytest.raises(ValidationError, match="PathLayer"):
        Canvas(100, 100).shape("rectangle", (0, 0), 40, 40, "#123456", animation=animation)
    canvas = scene(animation=animation)

    # When/Then: document targets report actual static fallback and reject strict publication safely
    for target in ("html", "pptx"):
        assert any(
            row.feature == "path_morph" and row.fallback == "static"
            for row in canvas.validate_export(target)
        )
    destination = tmp_path / "morph.html"
    destination.write_text("keep")
    with pytest.raises(RenderingError):
        canvas.export(destination, policy=ExportPolicy(unsupported_motion="error"))
    assert destination.read_text() == "keep"
    html = canvas.to_html()
    assert "data:image/png" in html and "path_morph" not in html


def test_morph_canonical_gif_and_worker_sequence(tmp_path):
    """Decoded GIF timing and serial/worker PNGs retain distinct canonical morph frames."""
    # Given: four visible translated phases plus the exact authored target
    canvas = scene(animation=motion(track(PathMorphTrack, A, B)))
    expected = [canvas.render_frame(t).tobytes() for t in (0, 0.25, 0.5, 0.75, 1)]
    assert len(set(expected)) == 5
    for frame, pixels in zip(
        canvas.sample(time=[0, 0.25, 0.5, 0.75, 1]).frames, expected, strict=True
    ):
        matte = Image.new("RGBA", (180, 160), "#000000")
        matte.alpha_composite(Image.frombytes("RGBA", matte.size, pixels))
        assert base64.b64decode(frame.data) == matte.tobytes()

    # When: actual serial and spawned-worker PNGs and a real encoded GIF are decoded
    for workers in (1, 2):
        directory = tmp_path / f"png-{workers}"
        canvas.export_image_sequence(
            directory, options=ImageSequenceOptions(fps=4, hold=0.25, workers=workers)
        )
        decoded = []
        for path in sorted(directory.glob("*.png")):
            with Image.open(path) as image:
                decoded.append(image.convert("RGBA").tobytes())
        assert decoded == expected
    output = tmp_path / "morph.gif"
    canvas.render(str(output), animation=GifOptions(fps=4))
    with Image.open(output) as image:
        frames = [
            (frame.convert("RGBA").tobytes(), frame.info["duration"])
            for frame in ImageSequence.Iterator(image)
        ]

    # Then: export sampling preserves actual changing contours and the requested timing grid
    assert len({pixels for pixels, _ in frames}) >= 4
    assert [duration for _, duration in frames[:4]] == [250] * 4
    assert video._SlideAnimator(canvas, {}).segments(0, 1) == [(0, 1, True)]
