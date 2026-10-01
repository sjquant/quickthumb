"""Subpixel motion, exact legacy landing pixels, and renderer/worker parity."""

import math
import shutil
import subprocess
from typing import cast
from unittest.mock import patch

import pytest
from benchmarks.animated_export import centroid, displacement_jitter
from benchmarks.scenes import build_scene
from PIL import Image, ImageDraw, ImageFilter
from quickthumb import (
    AnimationSpec,
    Canvas,
    ClipProgressTrack,
    GifOptions,
    KeyframeSpec,
    OpacityTrack,
    PositionTrack,
    TimingSpec,
    VideoOptions,
)
from quickthumb import _export_base as base
from quickthumb import _export_video as video
from quickthumb.motion import (
    LayerState,
    NormalizedKeyframe,
    NormalizedTrack,
    Timeline,
    TimelineEvent,
    _canonical_target_timelines,
    _geometry_in_motion,
)


def legacy_geometry(image, state, pos, *, include_scale=True, **kwargs):
    """Frozen pre-#147 geometry, including its settled-state rounding."""
    centre_x, centre_y = pos[0] + image.width / 2, pos[1] + image.height / 2
    if include_scale and state.scale > 0 and state.scale != 1:
        image = image.resize(
            (max(1, round(image.width * state.scale)), max(1, round(image.height * state.scale))),
            resample=Image.Resampling.LANCZOS,
        )
    if state.rotation:
        image = image.rotate(-state.rotation, expand=True, resample=Image.Resampling.BICUBIC)
    if state.blur > 0:
        margin = max(1, math.ceil(state.blur * 3))
        padded = Image.new("RGBA", (image.width + margin * 2, image.height + margin * 2))
        padded.alpha_composite(image.convert("RGBA"), (margin, margin))
        image = padded.filter(ImageFilter.GaussianBlur(state.blur))
    x, y = state.position or (0, 0)
    return image, (round(centre_x - image.width / 2 + x), round(centre_y - image.height / 2 + y))


def marker():
    image = Image.new("RGBA", (31, 23))
    ImageDraw.Draw(image).polygon(
        [(0, 0), (12, 0), (12, 12), (30, 12), (30, 22), (0, 22)], fill=(255, 40, 90, 180)
    )
    return image


def composite(fragment, pos, size=(128, 96)):
    frame = Image.new("RGBA", size)
    frame.alpha_composite(fragment, pos)
    return frame


@pytest.mark.parametrize("scale", [-1.0, 0.0, 0.75, 1.0, 1.15])
@pytest.mark.parametrize("angle", [-15, 0, 12, 90])
@pytest.mark.parametrize("blur", [0, 1.25])
def test_inactive_geometry_keeps_exact_legacy_pixels(scale, angle, blur):
    state = LayerState(scale=scale, rotation=angle, position=(-0.3, 2.25), blur=blur)
    actual, pos = base.apply_canonical_geometry(marker(), state, (17, 25))
    expected, expected_pos = legacy_geometry(marker(), state, (17, 25))
    assert (pos, actual.size, actual.tobytes()) == (expected_pos, expected.size, expected.tobytes())


@pytest.mark.parametrize("offset", [(0, 0), (3, -5), (-9, 8)])
@pytest.mark.parametrize("blur", [0, 1.25])
def test_integral_identity_motion_uses_exact_fast_path(offset, blur, monkeypatch):
    monkeypatch.setattr(
        base, "_affine_geometry", lambda *args: pytest.fail("unexpected resampling")
    )
    state = LayerState(position=offset, blur=blur)
    expected, expected_pos = legacy_geometry(marker(), state, (13, 21))
    actual, pos = base.apply_canonical_geometry(marker(), state, (13, 21), subpixel=True)
    assert (pos, actual.tobytes()) == (expected_pos, expected.tobytes())


def test_motion_uses_one_affine_resampling_and_keeps_input_unchanged(monkeypatch):
    source = marker()
    previous = source.tobytes()
    original = Image.Image.transform
    transforms = []

    def transform(image, size, method, data=None, resample=0, *args, **kwargs):
        transforms.append((image.mode, method, resample))
        return original(image, size, method, data, resample, *args, **kwargs)

    monkeypatch.setattr(Image.Image, "transform", transform)
    monkeypatch.setattr(
        Image.Image, "resize", lambda *args, **kwargs: pytest.fail("separate resize")
    )
    monkeypatch.setattr(
        Image.Image, "rotate", lambda *args, **kwargs: pytest.fail("separate rotate")
    )
    state = LayerState(scale=1.15, rotation=12, position=(0.2, -0.7))
    base.apply_canonical_geometry(source, state, (15, 17), subpixel=True)
    # RGBA delegates to premultiplied RGBa; only the latter resamples the pixels.
    assert transforms == [
        (mode, Image.Transform.AFFINE, Image.Resampling.BICUBIC) for mode in ("RGBA", "RGBa")
    ]
    assert source.tobytes() == previous


def test_tight_opaque_edges_translate_fractionally_without_dark_halos():
    image = Image.new("RGBA", (11, 9), (255, 0, 0, 255))
    centers = []
    for index in range(6):
        moved, pos = base.apply_canonical_geometry(
            image, LayerState(position=(index / 5, 0)), (30, 40), subpixel=True
        )
        frame = composite(moved, pos).getchannel("A")
        centers.append(centroid(frame)[0])
        pixels = cast(tuple[tuple[int, int, int, int], ...], moved.get_flattened_data())
        assert all(pixel[:3] == (255, 0, 0) for pixel in pixels if pixel[3])
    assert all(
        abs(step - 0.2) < 0.02
        for step in [b - a for a, b in zip(centers, centers[1:], strict=False)]
    )


def test_blur_keeps_fractional_placement_and_clips_negative_coordinates():
    states = [
        LayerState(position=(-19 + fraction, -7.3), scale=0.7, rotation=-12, blur=1.2)
        for fraction in (0.1, 0.4, 0.7)
    ]
    frames = [
        composite(*base.apply_canonical_geometry(marker(), state, (20, 15), subpixel=True))
        for state in states
    ]
    assert len({frame.tobytes() for frame in frames}) == 3
    assert all(frame.getbbox() for frame in frames)


def event(property, values, *, start=0, duration=2, blend="replace"):
    return TimelineEvent(
        source="timeline",
        start=start,
        delay=0,
        duration=duration,
        tracks=(
            NormalizedTrack(
                property=property,
                blend=blend,
                keyframes=tuple(NormalizedKeyframe(time=t, value=value) for t, value in values),
            ),
        ),
    )


def test_activity_preserves_delays_holds_early_ends_and_decimal_endpoints():
    timeline = Timeline(
        events=(event("rotation", [(0.5, 12), (1, 24), (1.5, 24)], start=0.1, duration=2),)
    )
    times = [0, 0.1, 0.5, 0.6, 0.7, 1.1, 1.2, 1.6, 2.1, 3]
    assert [_geometry_in_motion(timeline, t) for t in times] == [
        False,
        False,
        False,
        False,
        True,
        False,
        False,
        False,
        False,
        False,
    ]
    fractional = Timeline(events=(event("rotation", [(0, 0), (0.2, 12)], start=0.1, duration=0.2),))
    assert not _geometry_in_motion(fractional, 0.3)
    assert not _geometry_in_motion(fractional, 0.1 + 0.2)
    assert _geometry_in_motion(fractional, 0.2)


def test_interior_motion_knots_keep_affine_and_later_replace_masks_activity():
    moving = event("rotation", [(0, 0), (1, 12), (2, 24)])
    assert _geometry_in_motion(Timeline(events=(moving,)), 1)
    held = event("rotation", [(0, 12)], start=0.5)
    assert not _geometry_in_motion(Timeline(events=(moving, held)), 1)
    assert _geometry_in_motion(Timeline(events=(held, moving)), 1)
    opacity = event("opacity", [(0, 0), (2, 1)])
    assert not _geometry_in_motion(Timeline(events=(held, opacity)), 1)


def test_image_scale_activity_can_be_excluded_without_hiding_translation():
    scale = event("scale", [(0, 1), (2, 1.15)], blend="multiply")
    held = event("rotation", [(0, 12)])
    timeline = Timeline(events=(held, scale))
    assert _geometry_in_motion(timeline, 1)
    assert not _geometry_in_motion(timeline, 1, include_scale=False)
    move = event("position", [(0, (0, 0)), (2, (2, 1))], blend="add")
    assert _geometry_in_motion(Timeline(events=(held, scale, move)), 1, include_scale=False)


@pytest.mark.parametrize("scene,ratio", [("translation", 0.03), ("rotation", 0.7), ("scale", 0.05)])
def test_public_jitter_improves_and_transformed_endpoints_stay_identical(scene, ratio):
    deck = build_scene(scene)
    times = [index / 30 for index in range(60)] + [2.0, 2.3]
    current = [frame.to_image() for frame in deck.sample(time=times).frames]
    with patch.object(video, "apply_canonical_geometry", legacy_geometry):
        previous = [frame.to_image() for frame in build_scene(scene).sample(time=times).frames]
    before = displacement_jitter([centroid(frame) for frame in previous[:60]])
    after = displacement_jitter([centroid(frame) for frame in current[:60]])
    assert after < before * ratio
    assert current[-2].tobytes() == previous[-2].tobytes()
    assert current[-1].tobytes() == previous[-1].tobytes()
    state = next(
        unit for unit in video._SlideAnimator(deck._slides[0], {})._units if unit.timeline
    ).timeline.sample(2)
    if scene == "rotation":
        assert state.rotation == 12
    if scene == "scale":
        assert state.scale == 1.15


@pytest.mark.parametrize(
    "clip,opacity", [(1.0, 1.0), (0.5, 1.0), (1.0, 0.37), (0.5, 0.37), (0.0, 1.0)]
)
def test_fractional_canvas_and_export_compositors_agree(clip, opacity):
    animation = AnimationSpec.timeline(
        PositionTrack(
            keyframes=[KeyframeSpec(time=0, value=(0, 0)), KeyframeSpec(time=1, value=(1, 0))]
        ),
        ClipProgressTrack(keyframes=[KeyframeSpec(time=0, value=clip)]),
        OpacityTrack(keyframes=[KeyframeSpec(time=0, value=opacity)]),
        timing=TimingSpec(duration=1),
        easing="linear",
    )
    canvas = (
        Canvas(80, 60)
        .background(color="#101820")
        .shape("rectangle", (30, 20), 20, 20, "#D04210", animation=animation)
    )
    animator = video._SlideAnimator(canvas, {})
    for time in [0.2, 0.5, 0.8, 0.5]:
        assert canvas.render_frame(time).tobytes() == animator.frame_at(time).tobytes()


def test_stagger_targets_settle_on_their_own_clocks():
    canvas = Canvas(160, 130).text(
        "ONE\nTWO\nTHREE",
        position=(20, 20),
        size=20,
        font="assets/fonts/Roboto-Medium.ttf",
        color="#FFFFFF",
        animation=AnimationSpec.rise(distance=13, duration=0.5, stagger=0.4, target="lines"),
    )
    timelines = _canonical_target_timelines(canvas.layers[0], 3)
    assert timelines is not None
    assert [_geometry_in_motion(t, 0.6) for t in timelines] == [False, True, False]
    animator = video._SlideAnimator(canvas, {})
    for time in [0.6, 1.0, 1.3, 0.6]:
        assert canvas.render_frame(time).tobytes() == animator.frame_at(time).tobytes()
    with patch.object(base, "apply_canonical_geometry", legacy_geometry):
        assert canvas.render_frame(1.3).tobytes() == animator.frame_at(1.3).tobytes()


@pytest.mark.parametrize("format", ["gif", "mp4", "webm"])
def test_subpixel_output_is_identical_across_spawn_workers(tmp_path, format):
    if format != "gif" and not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not installed")
    deck = build_scene("rotation")
    options_type = GifOptions if format == "gif" else VideoOptions
    paths = [tmp_path / f"workers-{workers}.{format}" for workers in (1, 2)]
    for workers, path in zip((1, 2), paths, strict=True):
        deck.render(str(path), animation=options_type(fps=6, workers=workers))
    if format == "gif":
        assert paths[0].read_bytes() == paths[1].read_bytes()
    else:
        # WebM embeds random UIDs even for repeated serial exports.
        decoded = [
            subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-i",
                    str(path),
                    "-map",
                    "0:v",
                    "-vsync",
                    "0",
                    "-f",
                    "rawvideo",
                    "-pix_fmt",
                    "rgb24",
                    "-",
                ],
                capture_output=True,
                check=True,
                timeout=30,
            ).stdout
            for path in paths
        ]
        assert decoded[0] == decoded[1]


def test_cancelled_additive_motion_and_zero_scale_keep_held_geometry():
    held = event("rotation", [(0, 12)])
    up = event("position", [(0, (0, 13)), (2, (0, 0))], blend="add")
    down = event("position", [(0, (0, -13)), (2, (0, 0))], blend="add")
    cancelled = Timeline(events=(held, up, down))
    assert cancelled.sample(0.5).position == (0, 0)
    assert not _geometry_in_motion(cancelled, 0.5)
    zoom = event("scale", [(0, 1), (2, 1.15)], blend="multiply")
    zero = event("scale", [(0, 0)], blend="multiply")
    for events in [(held, zoom, zero), (held, zero, zoom)]:
        assert not _geometry_in_motion(Timeline(events=events), 0.5)
    reset = event("scale", [(0, 1), (2, 1.15)])
    assert _geometry_in_motion(Timeline(events=(held, zero, reset)), 0.5)


def test_nonpositive_scale_preserves_the_existing_ignore_scale_behavior():
    held = event("rotation", [(0, 12)])
    negative = event("scale", [(0, -2), (2, -1)])
    timeline = Timeline(events=(held, negative))
    assert not _geometry_in_motion(timeline, 1)
    assert not _geometry_in_motion(timeline, 1, state=timeline.sample(1))
    rotate = event("rotation", [(0, 12), (2, 24)])
    assert _geometry_in_motion(Timeline(events=(negative, rotate)), 1)
