"""Opt-in 2x layer compositing, unchanged defaults and native export contracts."""

import json
import shutil
import subprocess
from typing import Any, cast

import pytest
from PIL import Image, ImageSequence
from quickthumb import (
    AnimationSpec,
    BackdropBlur,
    BlurTrack,
    Canvas,
    ClipProgressTrack,
    Deck,
    Fade,
    GifOptions,
    KeyframeSpec,
    OpacityTrack,
    PositionTrack,
    RotationTrack,
    ScaleTrack,
    TimingSpec,
    VideoOptions,
)
from quickthumb import _export_video as video
from quickthumb.errors import ValidationError
from quickthumb.models import VideoCaption, VideoLayer
from quickthumb.transitions import Fade as CrossFade
from quickthumb.transitions import Morph

FONT = "assets/fonts/Roboto-Medium.ttf"
QUALITIES: tuple[video.AnimationQuality, ...] = ("standard", "high")
HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def animated_text(*, authored: bool = False, size: tuple[int, int] = (151, 91)) -> Canvas:
    tracks = [
        RotationTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=0.4, value=12)]),
        ScaleTrack(keyframes=[KeyframeSpec(time=0, value=0.9), KeyframeSpec(time=0.4, value=0.65)]),
        PositionTrack(
            keyframes=[
                KeyframeSpec(time=0, value=(-0.4, -0.2)),
                KeyframeSpec(time=0.4, value=(1.3, 0.7)),
            ]
        ),
    ]
    return (
        Canvas(*size)
        .background(color="#101820")
        .text(
            "Subpixel",
            font=FONT,
            size=28,
            color="#FFFFFF",
            position=(17, 31),
            motion_key="hero",
            rotation=12 if authored else 0,
            animation=None
            if authored
            else AnimationSpec.timeline(*tracks, timing=TimingSpec(duration=0.4), easing="linear"),
        )
    )


def decode(path, media="video"):
    args = ["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v" if media == "video" else "0:a"]
    args += (
        ["-vsync", "0", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        if media == "video"
        else ["-f", "s16le", "-"]
    )
    return subprocess.run(args, check=True, capture_output=True, timeout=30).stdout


@pytest.mark.parametrize("options", [GifOptions, VideoOptions])
def test_quality_is_explicit_opt_in_and_roundtrips(options):
    assert options().quality == "standard"
    assert options.model_validate_json(options(quality="high").model_dump_json()).quality == "high"
    assert options.model_json_schema()["properties"]["quality"]["enum"] == ["standard", "high"]


@pytest.mark.parametrize("options", [GifOptions, VideoOptions])
@pytest.mark.parametrize("quality", [None, True, 2, "low", "normal", [], {}])
def test_invalid_quality_is_rejected_by_options(options, quality):
    with pytest.raises(ValidationError, match="quality"):
        options.model_validate({"quality": quality})
    with pytest.raises(ValidationError, match="quality"):
        video._validated_settings(
            [Canvas(8, 8)], "gif", 10, 0.1, 0, "#000000", quality=cast(Any, quality)
        )


def test_high_draws_into_double_surface_with_one_final_downsample(monkeypatch):
    canvas = animated_text()
    standard = video._SlideAnimator(canvas, {})
    high = video._SlideAnimator(canvas, {}, quality="high")
    assert high._static_plate is not None
    assert high._static_plate.size == (canvas.width * 2, canvas.height * 2)
    assert [u.image.size for u in high._units if u.image is not None] == [
        u.image.size for u in standard._units if u.image is not None
    ]
    original_resize = Image.Image.resize
    calls = []

    def resize(image, size, resample=None, *args, **kwargs):
        if image.mode != "RGBA":
            calls.append((image.size, size, resample))
        return original_resize(image, size, resample, *args, **kwargs)

    monkeypatch.setattr(Image.Image, "resize", resize)
    frame = high.frame_at(0.2)
    assert frame.size == (151, 91)
    assert calls == [((302, 182), (151, 91), Image.Resampling.LANCZOS)]
    assert frame.tobytes() != standard.frame_at(0.2).tobytes()


@pytest.mark.parametrize("color", ["#FFFFFF", "#A04080", "#000000"])
def test_identity_background_keeps_opaque_native_edges(color):
    canvas = Canvas(17, 11).background(color=color)
    actual = video._SlideAnimator(canvas, {}, quality="high").frame_at(0)
    expected = video._SlideAnimator(canvas, {}).frame_at(0)
    assert actual.tobytes() == expected.tobytes()


@pytest.mark.parametrize("kind", ["canonical", "authored", "stagger", "backdrop"])
def test_high_is_deterministic_and_does_not_mutate_source(kind):
    canvas = animated_text(authored=kind == "authored")
    if kind == "stagger":
        canvas = (
            Canvas(151, 121)
            .background(color="#101820")
            .text(
                "One\nTwo\nThree",
                font=FONT,
                size=20,
                position=(20, 10),
                color="#FFFFFF",
                animation=AnimationSpec.rise(
                    distance=13, duration=0.4, stagger=0.2, target="lines"
                ),
            )
        )
    if kind == "backdrop":
        canvas.shape("rectangle", (11, 8), 67, 55, "#20406080", effects=[BackdropBlur(radius=1)])
    spec = canvas.to_json()
    standard = video._SlideAnimator(canvas, {})
    baseline = standard.frame_at(0.2).tobytes()
    high = video._SlideAnimator(canvas, {}, quality="high")
    first = high.frame_at(0.2).tobytes()
    high.frame_at(0.4)
    frame = high.frame_at(0.2)
    assert first == frame.tobytes()
    assert frame.size == (canvas.width, canvas.height)
    assert canvas.to_json() == spec
    assert standard.frame_at(0.2).tobytes() == baseline
    assert video._SlideAnimator(canvas, {}, quality="standard").frame_at(0.2).tobytes() == baseline


@pytest.mark.parametrize("blur", [0, 1.2])
@pytest.mark.parametrize("opacity,clip", [(1, 1), (0.37, 0.5), (0, 1), (1, 0)])
def test_high_scales_spatial_values_without_changing_fractions(blur, opacity, clip):
    canvas = (
        Canvas(71, 43)
        .background(color="#101820")
        .shape(
            "rectangle",
            (0, 4),
            29,
            19,
            "#FF2050",
            animation=AnimationSpec.timeline(
                PositionTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value=(-0.4, 0.1)),
                        KeyframeSpec(time=1, value=(1.2, -0.4)),
                    ]
                ),
                RotationTrack(keyframes=[KeyframeSpec(time=0, value=12)]),
                ScaleTrack(keyframes=[KeyframeSpec(time=0, value=0.65)]),
                BlurTrack(keyframes=[KeyframeSpec(time=0, value=blur)]),
                OpacityTrack(keyframes=[KeyframeSpec(time=0, value=opacity)]),
                ClipProgressTrack(keyframes=[KeyframeSpec(time=0, value=clip)]),
                timing=TimingSpec(duration=1),
                easing="linear",
            ),
        )
    )
    high = video._SlideAnimator(canvas, {}, quality="high")
    frame = high.frame_at(0.5)
    assert frame.size == (71, 43)
    assert frame.tobytes() == high.frame_at(0.5).tobytes()
    if opacity == 0 or clip == 0:
        assert (
            frame.tobytes()
            == Canvas(71, 43).background(color="#101820")._render_to_image().tobytes()
        )


def test_captions_keep_native_dimensions_and_visible_layer_filter(monkeypatch):
    layer = VideoLayer(
        type="video",
        source="not-opened.mp4",
        position=(0, 0),
        width=8,
        height=8,
        captions=[VideoCaption(text="cue", start=0, end=2)],
    )
    unit = video._Unit(
        Image.new("RGBA", (8, 8), "red"), (2, 2), [Fade(delay=0.5, duration=0.5)], 0, layers=[layer]
    )
    video._schedule_units([unit])
    calls = []

    def captions(frame, layers, time, *args):
        calls.append((frame.size, list(layers), time))

    monkeypatch.setattr(video, "render_video_captions", captions)
    canvas = Canvas(31, 21)
    video._composite_frame(canvas, [unit], 0.25, render_scale=2)
    video._composite_frame(canvas, [unit], 0.75, render_scale=2)
    assert calls[:2] == [((31, 21), [], 0.25), ((31, 21), [layer], 0.75)]
    canvas._layers = [layer]
    monkeypatch.setattr(video, "_build_units", lambda *args, **kwargs: [unit])
    animator = video._SlideAnimator(canvas, {}, quality="high")
    animator.final_export_frame()
    assert calls[-1][0:2] == ((31, 21), [layer])
    assert calls[-1][2] == pytest.approx(1.0 - video._TIME_EPSILON)


@pytest.mark.parametrize("transition", [CrossFade(duration=0.3), Morph(duration=0.3)])
def test_mixed_size_and_morph_boundaries_keep_native_dimensions_and_timing(transition):
    first = animated_text(size=(151, 91))
    second = animated_text(size=(151, 91) if isinstance(transition, Morph) else (113, 75))
    plans = [
        video._deck_plan(
            [first, second],
            [None, transition],
            0.1,
            0.2,
            None,
            quality=quality,
        )
        for quality in QUALITIES
    ]
    assert plans[0].timings == plans[1].timings
    assert plans[0].offsets == plans[1].offsets
    for quality, plan in zip(QUALITIES, plans, strict=True):
        shots = list(
            video._deck_shots(
                [first, second],
                [None, transition],
                10,
                0.2,
                (0, 0, 0),
                plan=plan,
                quality=quality,
            )
        )
        assert all(shot.frame.size == (151, 91) for shot in shots)
        assert sum(shot.duration for shot in shots) == pytest.approx(plan.duration)


@pytest.mark.parametrize("format", ["gif", "mp4", "webm"])
def test_public_default_identity_and_high_spawn_parity(tmp_path, format):
    if format != "gif" and not HAS_FFMPEG:
        pytest.skip("ffmpeg/ffprobe not installed")
    source = (
        Deck(151, 91)
        .slide(animated_text())
        .slide(animated_text(size=(113, 75)), transition=CrossFade(duration=0.2))
    )
    options = GifOptions if format == "gif" else VideoOptions
    paths = [
        tmp_path / f"{name}.{format}"
        for name in ("implicit", "standard", "high1", "high2", "after")
    ]
    settings = [
        options(fps=10),
        options(fps=10, quality="standard"),
        options(fps=10, quality="high"),
        options(fps=10, quality="high", workers=2),
        options(fps=10),
    ]
    for path, setting in zip(paths, settings, strict=True):
        source.render(str(path), animation=setting)
    if format in {"gif", "mp4"}:
        outputs = [path.read_bytes() for path in paths]
    else:
        outputs = [decode(path) for path in paths]
    assert outputs[0] == outputs[1] == outputs[4]
    assert outputs[2] == outputs[3]
    assert outputs[0] != outputs[2]


def test_high_gif_palette_size_loop_and_centisecond_timing(tmp_path):
    source = animated_text()
    files = []
    for quality in QUALITIES:
        path = tmp_path / f"{quality}.gif"
        source.render(
            str(path),
            animation=GifOptions(
                fps=12,
                colors=16,
                max_size=(83, 61),
                loop=3,
                quality=quality,
            ),
        )
        with Image.open(path) as gif:
            durations = [frame.info["duration"] for frame in ImageSequence.Iterator(gif)]
            files.append((gif.size, gif.info["loop"], durations))
    assert files[0] == files[1]
    assert files[0][0] == (83, 50)
    assert files[0][1] == 3


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg/ffprobe not installed")
def test_high_video_keeps_audio_schedule_and_endpoint_captions(tmp_path):
    clip = tmp_path / "clip.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=red:s=24x18:r=10:d=0.6",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=0.6",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(clip),
        ],
        check=True,
    )
    canvas = (
        Canvas(80, 60)
        .background(color="#101820")
        .video(
            str(clip),
            position=(5, 4),
            width=48,
            height=36,
            captions=[
                VideoCaption(text="cue", font=FONT, size=12, start=0, end=0.6, position=(40, 48))
            ],
        )
    )
    outputs = []
    settings: tuple[tuple[video.AnimationQuality, int], ...] = (
        ("standard", 1),
        ("high", 1),
        ("high", 2),
    )
    for quality, workers in settings:
        path = tmp_path / f"{quality}-{workers}.mp4"
        canvas.render(
            str(path),
            animation=VideoOptions(fps=10, quality=quality, workers=workers),
        )
        metadata = json.loads(
            subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "stream=codec_type,duration,nb_frames:format=duration",
                    "-of",
                    "json",
                    str(path),
                ],
                check=True,
                capture_output=True,
            ).stdout
        )
        outputs.append((metadata, decode(path, "audio"), decode(path)))
    assert outputs[0][:2] == outputs[1][:2] == outputs[2][:2]
    assert outputs[1][2] == outputs[2][2]


def test_high_moving_edges_are_continuous_across_integral_positions():
    from PIL import ImageChops
    from quickthumb._export_base import apply_canonical_geometry
    from quickthumb.motion import LayerState

    source = Image.new("RGBA", (11, 9), "white")
    outputs = []
    for offset in (0.0, 1e-8):
        image, pos = apply_canonical_geometry(
            source, LayerState(position=(offset, 0)), (30, 40), subpixel=True, render_scale=2
        )
        frame = Image.new("RGBA", (128 * 2, 96 * 2))
        frame.alpha_composite(image, pos)
        outputs.append(frame.resize((128, 96), Image.Resampling.LANCZOS))
    assert (
        cast(tuple[int, int], ImageChops.difference(*outputs).getchannel("A").getextrema())[1] <= 1
    )
