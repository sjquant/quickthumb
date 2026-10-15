"""Lossless static-prefix caching at the animated frame-compositing boundary."""

from dataclasses import replace

import pytest
from PIL import Image
from quickthumb import AnimationSpec, BackdropBlur, Canvas, Fade
from quickthumb import _export_video as video
from quickthumb._video import VideoInfo
from quickthumb.models import GroupLayer, VideoCaption, VideoLayer
from quickthumb.motion import Timeline

FONT = "assets/fonts/Roboto-Medium.ttf"
SAMPLE_TIMES = (1.5, 0.0, 0.75, 0.25, 1.0, -0.1, 0.75)


def _unit(seed: int, *, moving: bool = False) -> video._Unit:
    """Make overlapping cropped RGBA units, including almost-transparent pixels."""
    image = Image.new("RGBA", (9, 7))
    image.putdata(
        [
            ((seed * 53 + x * 19) % 256, y * 31, (seed * 79) % 256, (x * 29 + y) % 256)
            for y in range(7)
            for x in range(9)
        ]
    )
    return video._Unit(
        image=image,
        pos=(seed % 3 - 1, seed % 2),
        effects=[Fade(duration=1.0, trigger="with_previous")] if moving else [],
        seed=seed,
    )


def _uncached_frame(animator: video._SlideAnimator, time: float, **options) -> Image.Image:
    """Run the original full ordered stack without a pre-composited background."""
    return video._composite_frame(animator._canvas, animator._units, time, **options)


@pytest.mark.parametrize(
    ("moving", "prefix_length"),
    [
        ((True, False, True), 0),
        ((False, False, False), 3),
        ((False, False, True, False, True, False), 2),
        ((), 0),
    ],
    ids=["no-prefix", "fully-static", "interleaved-transparency", "empty"],
)
def test_static_plate_preserves_exact_pixels_order_and_sample_independence(
    monkeypatch, moving, prefix_length
):
    """Prefix reuse matches the uncached stack even after a caller mutates a frame."""
    units = [_unit(index, moving=dynamic) for index, dynamic in enumerate(moving)]
    monkeypatch.setattr(video, "_build_units", lambda *args, **kwargs: units)
    animator = video._SlideAnimator(Canvas(12, 10), {})
    assert animator._frame_units == units[prefix_length:]
    assert (animator._static_plate is not None) == (prefix_length > 0)
    plate_bytes = animator._static_plate.tobytes() if animator._static_plate is not None else None
    unit_bytes = [unit.image.tobytes() for unit in units if unit.image is not None]

    for time in SAMPLE_TIMES:
        frame = animator.frame_at(time)
        assert frame.mode == "RGBA"
        assert frame.size == (12, 10)
        assert frame.tobytes() == _uncached_frame(animator, time).tobytes()
        frame.paste((91, 2, 33, 77), (0, 0, 12, 10))

    if animator._static_plate is not None:
        assert animator._static_plate.tobytes() == plate_bytes
    assert [unit.image.tobytes() for unit in units if unit.image is not None] == unit_bytes


@pytest.mark.parametrize(
    ("moving", "prefix_length"),
    [((True, False, True), 0), ((False, False, False), 3), ((False, False, True, False, True), 2)],
    ids=["no-prefix", "fully-static", "mixed"],
)
def test_static_plate_reduces_alpha_composites_including_one_time_preparation(
    monkeypatch, moving, prefix_length
):
    """The prefix is paid for once; every remaining unit keeps its per-frame call."""
    units = [_unit(index, moving=dynamic) for index, dynamic in enumerate(moving)]
    monkeypatch.setattr(video, "_build_units", lambda *args, **kwargs: units)
    calls = 0
    composite = Image.alpha_composite

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return composite(*args, **kwargs)

    monkeypatch.setattr(Image, "alpha_composite", counted)
    animator = video._SlideAnimator(Canvas(12, 10), {})
    times = (0.5, 1.5, 0.8, 1.0, 0.3)
    cached = [animator.frame_at(time).tobytes() for time in times]
    cached_calls = calls
    calls = 0
    reference = [_uncached_frame(animator, time).tobytes() for time in times]

    assert cached == reference
    assert calls == len(times) * len(units)
    assert cached_calls == prefix_length + len(times) * (len(units) - prefix_length)
    assert calls - cached_calls == prefix_length * (len(times) - 1)


@pytest.mark.parametrize(
    "attributes",
    [
        {"effects": [Fade()]},
        {"nodes": [video._Node(Fade(), 0.0)]},
        {"timeline": Timeline()},
        {"target_timelines": (Timeline(),)},
        {"component_duration": 0.01},
        {"animates_layers": True},
    ],
    ids=["effects", "nodes", "timeline", "target-timelines", "component", "backdrop"],
)
def test_every_dynamic_signal_prevents_static_caching(attributes):
    """Even empty canonical timelines conservatively mark a unit as dynamic."""
    unit = _unit(0)
    assert not video._unit_is_dynamic(unit)
    assert video._unit_is_dynamic(replace(unit, **attributes))
    assert video._unit_is_dynamic(replace(unit, image=None, **attributes))


@pytest.mark.parametrize("nested", [False, True], ids=["direct", "group-descendant"])
def test_video_without_motion_metadata_still_prevents_static_caching(nested):
    """Frozen/reduced-motion video can retain time-dependent foreground captions."""
    layer = VideoLayer(type="video", source="clip.mp4", position=(0, 0), width=8, height=8)
    # Construct a nested internal layer directly: the public group schema does
    # not currently expose video children, but recursive detection must be safe.
    layers = [GroupLayer.model_construct(type="group", children=[layer])] if nested else [layer]
    assert video._unit_is_dynamic(replace(_unit(0), layers=layers))


def test_invisible_static_units_do_not_change_the_prefix_boundary(monkeypatch):
    """Empty images remain no-ops both before and after the first moving unit."""
    units = [replace(_unit(0), image=None), _unit(1), _unit(2, moving=True)]
    monkeypatch.setattr(video, "_build_units", lambda *args, **kwargs: units)
    animator = video._SlideAnimator(Canvas(12, 10), {})
    assert animator._frame_units == units[2:]
    for time in SAMPLE_TIMES:
        assert animator.frame_at(time).tobytes() == _uncached_frame(animator, time).tobytes()


@pytest.mark.parametrize("reduced_motion", [False, True])
def test_counter_components_remain_dynamic_unless_reduced_motion_freezes_them(reduced_motion):
    """A counter without a layer-level effect must not become part of a static plate."""
    canvas = (
        Canvas(140, 64)
        .background(color="#143352")
        .counter(0, 100, 1.0, position=(12, 8), size=36, font=FONT, style="plain")
    )
    animator = video._SlideAnimator(canvas, {}, reduced_motion=reduced_motion)
    assert (animator._static_plate is not None) == reduced_motion
    samples = []
    for time in SAMPLE_TIMES:
        frame = animator.frame_at(time).tobytes()
        assert frame == _uncached_frame(animator, time).tobytes()
        samples.append(frame)
    assert (len(set(samples)) == 1) == reduced_motion


@pytest.mark.parametrize(
    "motion", ["legacy", "canonical", "stagger-words", "stagger-lines", "backdrop"]
)
def test_real_motion_units_keep_exact_uncached_pixels(motion):
    """Legacy, canonical, staggered, and backdrop-dependent motion remain sampled."""
    canvas = Canvas(140, 64).background(color="#143352")
    if motion.startswith("stagger"):
        lines = motion == "stagger-lines"
        canvas.text(
            "one\ntwo" if lines else "one two",
            position=(4, 4),
            size=18,
            font=FONT,
            animation=AnimationSpec.typewriter(
                duration=1.0, target="lines" if lines else "words", stagger=0.1
            ),
        )
    else:
        animation = Fade(duration=1.0) if motion == "legacy" else AnimationSpec.fade(duration=1.0)
        canvas.shape("rectangle", (4, 4), 80, 48, "#EF772A", opacity=0.65, animation=animation)
        if motion == "backdrop":
            canvas.shape(
                "rectangle",
                (0, 0),
                140,
                64,
                "#123456",
                opacity=0.4,
                effects=[BackdropBlur(radius=2)],
            )
    canvas.shape("rectangle", (18, 5), 40, 50, "#ABCDEF", opacity=0.35)
    animator = video._SlideAnimator(canvas, {})
    assert (animator._static_plate is None) == (motion == "backdrop")
    if motion.startswith("stagger"):
        unit = animator._frame_units[0]
        assert len(unit.target_timelines) == 2
        assert len(unit.target_images) == (2 if motion == "stagger-lines" else 0)
    samples = []
    for time in SAMPLE_TIMES:
        frame = animator.frame_at(time).tobytes()
        assert frame == _uncached_frame(animator, time).tobytes()
        samples.append(frame)
    assert len(set(samples)) > 1


@pytest.mark.parametrize("reduced_motion", [False, True])
@pytest.mark.parametrize("entrance", [False, True])
def test_video_captions_stay_timed_above_static_overlays(
    tmp_path, monkeypatch, reduced_motion, entrance
):
    """Caption visibility/timing survives frozen video, layer reveals, and foreground art."""
    source = tmp_path / "clip.mp4"
    source.touch()
    info = VideoInfo(duration=1.0, width=32, height=24, has_audio=False, frame_rate=10)
    monkeypatch.setattr("quickthumb.canvas.probe_video", lambda *args: info)
    monkeypatch.setattr(video, "probe_video", lambda *args: info)

    def draw_video(image, layer, time, *args):
        color = (200, 30, 15, 255) if time < 0.5 else (15, 30, 200, 255)
        image.paste(color, (0, 0, 32, 24))

    monkeypatch.setattr("quickthumb.canvas.render_video_layer", draw_video)
    canvas = (
        Canvas(96, 64)
        .background(color="#123456")
        .video(
            str(source),
            position=(0, 0),
            width=32,
            height=24,
            duration=1.0,
            animation=Fade(duration=0.2) if entrance else None,
            captions=[
                VideoCaption(text="cue", start=0.2, end=0.8, position=(48, 48), size=14, font=FONT)
            ],
        )
        .shape("rectangle", (0, 32), 96, 32, "#000000")
    )
    animator = video._SlideAnimator(canvas, {}, reduced_motion=reduced_motion)
    assert (animator._static_plate is not None) == (entrance and not reduced_motion)
    for time in (0.4, 0.0, 0.8, 0.2, 1.0, 0.4):
        captioned = animator.frame_at(time)
        bare = animator.frame_at(time, include_captions=False)
        assert captioned.tobytes() == _uncached_frame(animator, time).tobytes()
        assert bare.tobytes() == _uncached_frame(animator, time, include_captions=False).tobytes()
        assert (captioned.tobytes() != bare.tobytes()) == (0.2 <= time < 0.8)
        captioned.paste((91, 2, 33, 77), (0, 0, 96, 64))
