"""Dash phase timelines paint local stroke distances through shared export paths."""

import base64
import json

import jsonschema
import pytest
from PIL import Image, ImageSequence
from quickthumb import (
    AnimationSpec,
    BarChartSpec,
    Canvas,
    DashOffsetTrack,
    GifOptions,
    ImageSequenceOptions,
    KeyframeSpec,
    PathLayer,
    TimingSpec,
    canvas_json_schema,
)
from quickthumb import _export_video as video
from quickthumb.errors import RenderingError, ValidationError

from tests.test_path_motion import motion, track


def scene(animation=None, *, offset=2, pattern=(5, 3), rotation=0):
    return Canvas(128, 48).path(
        "M0 8H48V16H0",
        (8, 8),
        112,
        32,
        None,
        view_box=(0, 0, 56, 16),
        stroke="#30C08090",
        stroke_width=1,
        dash_array=pattern,
        dash_offset=offset,
        rotation=rotation,
        animation=animation,
    )


@pytest.mark.parametrize("pattern", [(5, 3), (3, 1, 2)])
@pytest.mark.parametrize("rotation", [0, 12])
def test_sampled_phase_matches_authored_strokes(pattern, rotation):
    """Repeated sampled phases match independent static paths including negative odd cycles."""
    # Given: authored phase plus a changing relative phase, round-tripped through JSON
    canvas = scene(motion(track(DashOffsetTrack, -6, 12)), pattern=pattern, rotation=rotation)
    encoded = canvas.to_json()
    jsonschema.validate(json.loads(encoded), canvas_json_schema())
    canvas = Canvas.from_json(encoded)
    prepared = video._SlideAnimator(canvas, {})

    # When: one prepared renderer visits times in a nonmonotonic order
    for time, effective in ((0, -4), (0.5, 5), (1, 14), (0.5, 5), (0, -4)):
        expected = scene(offset=effective, pattern=pattern, rotation=rotation).render_frame(0)
        actual = canvas.render_frame(time)
        capture = canvas.sample(time=time).frames[0]

        # Then: the retained source, canonical sample and direct frame retain exact RGBA
        assert actual.tobytes() == expected.tobytes()
        assert prepared.frame_at(time).tobytes() == expected.tobytes()
        matte = Image.new("RGBA", expected.size, "#000000")
        matte.alpha_composite(expected)
        assert base64.b64decode(capture.data) == matte.tobytes()
    inspected = canvas.inspect_motion(fps=2).slides[0].layers[0]
    assert inspected.static_state["dash_offset"] == 2
    assert [state["dash_offset"] for state in inspected.samples] == [-4, 5, 14]
    assert canvas.inspect_motion(fps=2).slides[0].layers[0] == inspected
    assert isinstance(canvas.layers[0], PathLayer)
    assert canvas.layers[0].dash_offset == 2
    zero = scene(motion(track(DashOffsetTrack, -2, 10))).inspect_motion().slides[0].layers[0]
    assert zero.initial_state["dash_offset"] == 0


def test_local_clock_hold_easing_and_composition():
    """Delayed dash motion applies outgoing holds, easing and additive event composition."""
    # Given: an outgoing hold followed by easing, and a later additive relative track
    phase = DashOffsetTrack(
        keyframes=[
            KeyframeSpec(time=0, value=0, hold=True),
            KeyframeSpec(time=0.5, value=6, easing="ease_in"),
            KeyframeSpec(time=1, value=12),
        ]
    )
    first = AnimationSpec.timeline(phase, timing=TimingSpec(start=1, duration=1), easing="linear")
    extra = DashOffsetTrack(keyframes=[KeyframeSpec(time=0, value=-3)], blend="add")
    second = AnimationSpec.timeline(extra, timing=TimingSpec(start=2, duration=1))
    canvas = scene([first, second])

    # When/Then: local event time and event order determine the independently painted phase
    for time, effective in ((0, 2), (1.25, 2), (1.5, 8), (1.75, 9.5), (2, 11), (3, 11)):
        assert (
            canvas.render_frame(time).tobytes() == scene(offset=effective).render_frame(0).tobytes()
        )
    replace = extra.model_copy(update={"blend": "replace"})
    canvas.layers[0].animation = [
        first,
        AnimationSpec.timeline(replace, timing=TimingSpec(start=2, duration=1)),
    ]
    assert canvas.render_frame(2).tobytes() == scene(offset=-1).render_frame(0).tobytes()


def test_finite_phase_range_and_sample_errors():
    """Finite opposite endpoints interpolate safely and nonrepresentable effective phases fail."""
    # Given: finite endpoints whose difference overflows ordinary subtraction
    canvas = scene(motion(track(DashOffsetTrack, -1e308, 1e308)))

    # When/Then: the reviewed shared scalar interpolation yields the actual midpoint paint
    assert canvas.render_frame(0.5).tobytes() == scene(offset=2).render_frame(0).tobytes()
    overflow = scene(motion(track(DashOffsetTrack, 1e308, 1e308)), offset=1e308)
    with pytest.raises(RenderingError, match="dash_offset must be finite"):
        overflow.render_frame(0.5)


@pytest.mark.parametrize("kind", ["shape", "text", "image", "null", "group", "chart"])
def test_non_path_rejects_dash_tracks(kind):
    """Non-Path layer models reject a dash track before any renderer can ignore it."""
    # Given: a valid layer of each supported non-Path motion category
    canvas = Canvas(64, 64)
    if kind == "shape":
        canvas.shape("rectangle", (0, 0), 20, 20, "#123456")
    elif kind == "text":
        canvas.text("phase", position=(0, 0))
    elif kind == "image":
        canvas.image("tests/fixtures/sample_image.jpg", (0, 0), 20, 20)
    elif kind == "null":
        canvas.null()
    elif kind == "group":
        canvas.group(Canvas(64, 64).shape("rectangle", (0, 0), 20, 20, "#123456").layers)
    else:
        canvas.chart(BarChartSpec(data=[1]), (0, 0), 40, 40)
    payload = json.loads(canvas.to_json())
    payload["layers"][0]["animation"] = json.loads(
        motion(track(DashOffsetTrack, 0, 12)).model_dump_json()
    )

    # When/Then: public document reconstruction reports the invalid target
    with pytest.raises(ValidationError, match="PathLayer"):
        Canvas.from_json(json.dumps(payload))


def test_encoded_gif_and_png_workers_keep_motion(tmp_path):
    """Decoded GIF frames retain timing and motion while serial and worker PNGs preserve RGBA."""
    # Given: effective phases 2, 5, 8, 11 and 14 on an eight-unit cycle
    canvas = scene(motion(track(DashOffsetTrack, 0, 12)))
    expected = [canvas.render_frame(t).tobytes() for t in (0, 0.25, 0.5, 0.75, 1)]
    assert len(set(expected)) == 5

    # When: actual PNGs are rendered serially and through spawned workers
    for workers in (1, 2):
        directory = tmp_path / f"png-{workers}"
        result = canvas.export_image_sequence(
            directory,
            options=ImageSequenceOptions(
                fps=4,
                hold=0.25,
                workers=workers,
            ),
        )
        decoded = []
        for path in sorted(directory.glob("*.png")):
            with Image.open(path) as image:
                decoded.append(image.convert("RGBA").tobytes())
        assert result.frame_count == 5 and result.duration == 1.25
        assert decoded == expected
    output = tmp_path / "phase.gif"
    canvas.render(str(output), animation=GifOptions(fps=4))
    with Image.open(output) as image:
        frames = [
            (frame.convert("RGBA").tobytes(), frame.info["duration"])
            for frame in ImageSequence.Iterator(image)
        ]

    # Then: decoding proves encoded changing paint and the requested quarter-second grid
    assert len({pixels for pixels, _ in frames}) >= 4
    assert [duration for _, duration in frames[:4]] == [250] * 4
    assert video._SlideAnimator(canvas, {}).segments(0, 1) == [(0, 1, True)]
    assert any(
        row.feature == "dash_offset" and row.support == "native"
        for row in canvas.validate_export("html")
    )
    assert any(
        row.feature == "dash_offset" and row.fallback == "static"
        for row in canvas.validate_export("pptx")
    )
    assert isinstance(canvas.layers[0], PathLayer)
