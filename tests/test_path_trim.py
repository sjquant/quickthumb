"""Normalized stroke trim uses local arc length through canonical Path exports."""

import base64
import json

import jsonschema
import pytest
from PIL import Image, ImageChops, ImageSequence
from quickthumb import (
    AnimationSpec,
    Canvas,
    ExportPolicy,
    GifOptions,
    ImageSequenceOptions,
    KeyframeSpec,
    PathLayer,
    ScaleTrack,
    TimingSpec,
    TrimEndTrack,
    TrimOffsetTrack,
    TrimStartTrack,
    canvas_json_schema,
)
from quickthumb import _export_video as video
from quickthumb.errors import RenderingError, ValidationError

from tests.test_path_motion import motion, track


def scene(d="M0 8H80", **options):
    return Canvas(180, 72).path(
        d,
        (10, 10),
        160,
        48,
        None,
        view_box=(0, 0, 80, 32),
        stroke="#30C08090",
        stroke_width=2,
        **options,
    )


@pytest.mark.parametrize(
    ("start", "end", "offset", "reference"),
    [
        (0.25, 0.75, 0, "M20 8H60"),
        (0.75, 0.25, 0, "M60 8H80M0 8H20"),
        (0, 0.5, -0.25, "M60 8H80M0 8H20"),
        (0, 0.5, 2.25, "M20 8H60"),
    ],
)
@pytest.mark.parametrize("cap", ["butt", "round", "square"])
def test_trim_window_matches_independent_open_paths(start, end, offset, reference, cap):
    """Wrapped and shifted trim intervals retain independently authored line endpoints and caps."""
    # Given: a stroke trimmed in local SVG distance under a nonuniform viewBox mapping
    canvas = scene(trim_start=start, trim_end=end, trim_offset=offset, line_cap=cap)

    # When: static JSON is validated and reconstructed
    encoded = canvas.to_json()
    jsonschema.validate(json.loads(encoded), canvas_json_schema())
    actual = Canvas.from_json(encoded).render_frame(0)

    # Then: exact RGBA agrees with independently authored visible line segments
    assert actual.tobytes() == scene(reference, line_cap=cap).render_frame(0).tobytes()


def test_multiple_contours_share_length_without_connecting():
    """Unequal subpaths share one local length clock while disconnected portions stay separate."""
    # Given: 20- and 60-unit subpaths, with a trim window spanning their boundary
    canvas = scene("M0 4H20M0 20H60", trim_start=0.125, trim_end=0.5)
    expected = scene("M10 4H20M0 20H20")

    # When/Then: quarter points use the total 80-unit length and never add a connector
    assert canvas.render_frame(0).tobytes() == expected.render_frame(0).tobytes()
    empty = scene("M0 4H20M0 20H60", trim_start=0.4, trim_end=0.4, line_cap="round")
    assert empty.render_frame(0).getbbox() is None
    dots = scene("M20 8L20 8", trim_end=0.5, line_cap="round")
    assert dots.render_frame(0).getbbox() is None
    assert scene("M20 8L20 8", line_cap="round").render_frame(0).getbbox() is not None


def test_closed_seam_keeps_joins_and_fill():
    """A wrapped closed contour keeps its seam join, and trimming preserves authored fill."""
    # Given: a square whose last and first retained quarters meet across the closing seam
    d = "M20 4H40V24H20Z"
    trimmed = scene(d, trim_start=0.75, trim_end=0.25, line_join="bevel", line_cap="round")
    reference = scene("M20 24V4H40", line_join="bevel", line_cap="round")

    # When/Then: the seam is an interior join, while the two cut ends retain caps
    assert trimmed.render_frame(0).tobytes() == reference.render_frame(0).tobytes()
    filled = scene(
        d,
        trim_end=0,
        fill={"type": "linear", "angle": 0, "stops": [("#FF000080", 0), ("#0000FF", 1)]},
    )
    expected = scene(
        d, fill={"type": "linear", "angle": 0, "stops": [("#FF000080", 0), ("#0000FF", 1)]}
    )
    layer = expected.layers[0]
    assert isinstance(layer, PathLayer)
    layer.stroke = None
    assert filled.render_frame(0).tobytes() == expected.render_frame(0).tobytes()
    assert (
        scene(d, trim_offset=0.35).render_frame(0).tobytes() == scene(d).render_frame(0).tobytes()
    )


def test_trim_then_dash_restarts_each_retained_run():
    """Dash painting starts at each retained trim run using the authored local dash offset."""
    # Given: a trim window across a corner, followed by an odd dash pattern
    canvas = scene(
        "M0 4H40V24",
        trim_start=1 / 3,
        trim_end=1,
        dash_array=(5, 2, 1),
        dash_offset=-3,
        line_cap="round",
    )
    reference = scene("M20 4H40V24", dash_array=(5, 2, 1), dash_offset=-3, line_cap="round")

    # When/Then: the retained corner and each dash use the existing join and cap rules
    assert canvas.render_frame(0).tobytes() == reference.render_frame(0).tobytes()


def test_curved_trim_tracks_repaint_at_device_density():
    """A scaled curved trim reaches the same pixels as independently authored final geometry."""
    # Given: a symmetric quadratic whose half-length point is its parameter midpoint
    animation = motion(track(TrimEndTrack, 0, 0.5), track(ScaleTrack, 1, 3))
    canvas = Canvas(540, 200).path(
        "M0 20Q40 -12 80 20",
        (10, 10),
        160,
        48,
        None,
        anchor=(0, 0),
        animation=animation,
        view_box=(0, 0, 80, 32),
        stroke="#30C08090",
        stroke_width=2,
    )
    reference = Canvas(540, 200).path(
        "M0 20Q20 4 40 4",
        (10, 10),
        480,
        144,
        None,
        view_box=(0, 0, 80, 32),
        stroke="#30C08090",
        stroke_width=2,
    )

    # When: settled geometry is rendered by direct and prepared adaptive painters
    actual = canvas.render_frame(1)
    expected = reference.render_frame(0)

    # Then: the independently split curve agrees within the painter's chord tolerance
    difference = ImageChops.difference(actual, expected).getchannel("A")
    assert sum(difference.tobytes()) / (actual.width * actual.height) < 0.2
    assert actual.getbbox() is not None
    assert video._SlideAnimator(canvas, {}).frame_at(1).tobytes() == actual.tobytes()


def test_trim_tracks_local_hold_composition_and_inspection():
    """Local held boundaries replace authored trim values while relative offset tracks compose."""
    # Given: a delayed outgoing hold and two ordered relative offset tracks
    end = TrimEndTrack(
        keyframes=[KeyframeSpec(time=0, value=0.25, hold=True), KeyframeSpec(time=1, value=0.75)]
    )
    first = AnimationSpec.timeline(
        end,
        track(TrimStartTrack, 0, 0.25),
        track(TrimOffsetTrack, 0, 0.25),
        timing=TimingSpec(start=1, duration=1),
        easing="linear",
    )
    extra = TrimOffsetTrack(keyframes=[KeyframeSpec(time=0, value=-0.125)], blend="add")
    second = AnimationSpec.timeline(extra, timing=TimingSpec(start=2, duration=1))
    canvas = scene(trim_start=0.125, trim_end=0.5, trim_offset=0.125, animation=[first, second])
    prepared = video._SlideAnimator(canvas, {})

    # When: the same retained source visits changing phases and previously sampled instants
    for instant, start, end, offset in (
        (0, 0.125, 0.5, 0.125),
        (1, 0, 0.25, 0.125),
        (1.5, 0.125, 0.25, 0.25),
        (2, 0.25, 0.75, 0.25),
        (1, 0, 0.25, 0.125),
    ):
        expected = scene(trim_start=start, trim_end=end, trim_offset=offset).render_frame(0)
        assert canvas.render_frame(instant).tobytes() == expected.tobytes()
        assert prepared.frame_at(instant).tobytes() == expected.tobytes()
    inspected = canvas.inspect_motion().slides[0].layers[0]
    assert inspected.static_state["trim_start"] == 0.125
    assert inspected.initial_state["trim_end"] == 0.5
    assert inspected.final_state["trim_start"] == 0.25
    assert inspected.final_state["trim_end"] == 0.75
    assert inspected.final_state["trim_offset"] == 0.25
    assert canvas.inspect_motion().slides[0].layers[0] == inspected


@pytest.mark.parametrize("kind", [TrimStartTrack, TrimEndTrack, TrimOffsetTrack])
def test_trim_contract_rejects_invalid_targets_and_values(kind):
    """Trim tracks reject non-Path layers and malformed boundaries before rendering."""
    # Given: a valid canonical trim track and a non-Path animated layer
    animation = motion(track(kind, 0, 0.5))

    # When/Then: model validation reports the unsupported target and out-of-range boundaries
    with pytest.raises(ValidationError, match="PathLayer"):
        Canvas(40, 40).shape("rectangle", (0, 0), 20, 20, "#123456", animation=animation)
    if kind != TrimOffsetTrack:
        with pytest.raises(ValidationError, match="between 0 and 1"):
            track(kind, 0, 1.1)


def test_trim_canonical_gif_and_worker_sequences(tmp_path):
    """Animated trim reaches canonical samples and decoded GIFs with serial/worker PNG parity."""
    # Given: a reveal with distinct quarter-second visible stroke lengths
    overflow = scene(trim_offset=1e308, animation=motion(track(TrimOffsetTrack, 1e308, 1e308)))
    with pytest.raises(RenderingError, match="trim_offset must be finite"):
        overflow.render_frame(0.5)
    canvas = scene(animation=motion(track(TrimEndTrack, 0, 1)))
    expected = [canvas.render_frame(t).tobytes() for t in (0, 0.25, 0.5, 0.75, 1)]
    assert len(set(expected)) == 5
    capture = canvas.sample(time=[0, 0.25, 0.5, 0.75, 1])
    for frame, instant in zip(capture.frames, (0, 0.25, 0.5, 0.75, 1), strict=True):
        authored = scene(trim_end=instant).render_frame(0)
        matte = Image.new("RGBA", authored.size, "#000000")
        matte.alpha_composite(authored)
        assert base64.b64decode(frame.data) == matte.tobytes()

    # When: independent serial and worker PNG exports and an actual GIF are decoded
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
    output = tmp_path / "trim.gif"
    canvas.render(str(output), animation=GifOptions(fps=4))
    with Image.open(output) as image:
        frames = [
            (frame.convert("RGBA").tobytes(), frame.info["duration"])
            for frame in ImageSequence.Iterator(image)
        ]

    # Then: encoded motion retains the requested grid and static document fallback is explicit
    assert len({pixels for pixels, _ in frames}) >= 4
    assert [duration for _, duration in frames[:4]] == [250] * 4
    assert video._SlideAnimator(canvas, {}).segments(0, 1) == [(0, 1, True)]
    for target in ("html", "pptx"):
        assert any(
            row.feature == "trim_end" and row.fallback == "static"
            for row in canvas.validate_export(target)
        )
    path = tmp_path / "trim.svg"
    static = scene(trim_end=0.5)
    static.export(path)
    assert "data:image/png" in path.read_text()
    with pytest.raises(RenderingError):
        static.export(path, policy=ExportPolicy(unsupported_motion="error"))
