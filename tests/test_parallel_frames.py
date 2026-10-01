"""Spawned rendering preserves ordered pixels, variable timing, and public exports."""

import hashlib
import json
import shutil
import subprocess
from typing import cast

import pytest
from quickthumb import (
    AnimationSpec,
    Canvas,
    Deck,
    ExportPolicy,
    Fade,
    GifOptions,
    Grain,
    VideoOptions,
)
from quickthumb import _export_video as video
from quickthumb import transitions as tr
from quickthumb._render_workers import ParallelFrames
from quickthumb.errors import ValidationError

HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
FONT = "assets/fonts/Roboto-Medium.ttf"


def _scene(kind):
    shared = Fade(duration=0.35, delay=0.12)
    first = Canvas(80, 56).background(color="#123456")
    if kind == "shared":
        first.shape("rectangle", (2, 3), 25, 23, "#FF2345", animation=shared)
        first.shape("rectangle", (22, 5), 30, 32, "#34FF56", opacity=0.55, animation=shared)
    elif kind == "stagger":
        first.text(
            "one\ntwo",
            position=(3, 3),
            size=18,
            font=FONT,
            animation=AnimationSpec.typewriter(duration=0.3, target="lines", stagger=0.1),
        )
    elif kind == "counter":
        first.counter(0, 10, 0.4, position=(3, 3), size=24, font=FONT)
    elif kind == "grain":
        first.background(color="#AABBCC", effects=[Grain(intensity=0.3, seed=7)])
        first.shape(
            "rectangle",
            (3, 3),
            60,
            40,
            "#AABBCC",
            animation=Fade(duration=0.4),
        )
    elif kind == "morph":
        first.shape("rectangle", (3, 3), 35, 30, "#FF3344", motion_key="box")
    else:
        first.shape(
            "rectangle", (3, 3), 35, 30, "#FF3344", animation=Fade(duration=0.12, delay=0.6)
        )
    first.shape("rectangle", (17, 5), 30, 40, "#4488AA", opacity=0.4)
    second = Canvas(80 if kind == "morph" else 64, 56 if kind == "morph" else 44).background(
        color="#F0EEDD"
    )
    second.shape("rectangle", (22, 14), 30, 20, "#33AAFF", motion_key="box")
    transition = tr.Morph(duration=0.25) if kind == "morph" else tr.Dissolve(duration=0.25)
    return [first, second], [None, transition]


def _shots(canvases, transitions, workers, *, hold=0.0, reduced=False, fps=12):
    source = video._deck_shots(
        canvases, transitions, fps, hold, (9, 11, 13), workers=workers, reduced_motion=reduced
    )
    try:
        return [
            (
                shot.frame.size,
                hashlib.sha256(shot.frame.tobytes()).hexdigest(),
                shot.duration,
                shot.caption_active,
            )
            for shot in source
        ]
    finally:
        source.close()
        video._close_video_decoders(canvases)


@pytest.mark.parametrize("kind", ["shared", "stagger", "counter", "grain", "morph", "gaps"])
@pytest.mark.parametrize("workers", [2, 3])
def test_spawned_shots_are_identical(kind, workers):
    canvases, transitions = _scene(kind)
    assert _shots(canvases, transitions, workers) == _shots(canvases, transitions, 1)


@pytest.mark.parametrize("hold", [0.0, 0.01, 0.3])
def test_half_frame_and_reduced_motion_shots_are_identical(hold):
    canvases, transitions = _scene("shared")
    assert _shots(canvases, transitions, 2, hold=hold, reduced=True, fps=10) == _shots(
        canvases, transitions, 1, hold=hold, reduced=True, fps=10
    )


@pytest.mark.parametrize("options", [GifOptions, VideoOptions])
@pytest.mark.parametrize("workers", [True, False, 0, -1, 9, 1.0, "2", None])
def test_worker_options_require_a_bounded_integer(options, workers):
    with pytest.raises(ValidationError, match="workers"):
        options(workers=workers)


@pytest.mark.parametrize("options", [GifOptions, VideoOptions])
def test_worker_options_default_to_one_and_accept_bounds(options):
    assert options().workers == 1
    assert options(workers=8).workers == 8


@pytest.mark.parametrize("workers", [2, 3])
@pytest.mark.parametrize("document", ["canvas", "deck"])
def test_public_gif_render_and_export_match_bytes(tmp_path, workers, document):
    canvases, transitions = _scene("shared")
    source = (
        canvases[0]
        if document == "canvas"
        else Deck(80, 56).slide(canvases[0]).slide(canvases[1], transition=transitions[1])
    )
    serial = tmp_path / "serial.gif"
    parallel = tmp_path / "parallel.gif"
    source.render(str(serial), animation=GifOptions(fps=12, colors=32, max_size=(60, 40), loop=2))
    result = source.export(
        str(parallel),
        animation=GifOptions(fps=12, colors=32, max_size=(60, 40), loop=2, workers=workers),
    )
    assert serial.read_bytes() == parallel.read_bytes()
    assert result.pixel_metrics.frame_count > 0


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg/ffprobe not installed")
@pytest.mark.parametrize("container", ["mp4", "webm"])
def test_public_video_decoded_bytes_timing_and_audio_match(tmp_path, container):
    canvases, _ = _scene("shared")
    source = Deck(80, 56).slide(canvases[0], duration=0.8).slide(canvases[1], duration=0.7)
    outputs = []
    for workers in (1, 2):
        path = tmp_path / f"workers-{workers}.{container}"
        source.render(str(path), animation=VideoOptions(fps=12, workers=workers))
        decoded = subprocess.run(
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
            check=True,
            capture_output=True,
        ).stdout
        probe = json.loads(
            subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-count_frames",
                    "-show_entries",
                    "stream=codec_name,codec_type,width,height,nb_read_frames:format=duration",
                    "-of",
                    "json",
                    str(path),
                ],
                check=True,
                capture_output=True,
            ).stdout
        )
        pcm = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a", "-f", "s16le", "-"],
            check=True,
            capture_output=True,
        ).stdout
        outputs.append((decoded, probe, pcm, path.read_bytes()))
    assert outputs[0][:3] == outputs[1][:3]
    if container == "mp4":
        assert outputs[0][3] == outputs[1][3]


def test_reduced_motion_option_is_forwarded_to_workers(tmp_path):
    canvases, _ = _scene("stagger")
    paths = [tmp_path / "serial.gif", tmp_path / "parallel.gif"]
    for workers, path in zip((1, 2), paths, strict=True):
        canvases[0].render(
            str(path),
            animation=GifOptions(fps=10, workers=workers),
            policy=ExportPolicy(reduced_motion=True),
        )
    assert paths[0].read_bytes() == paths[1].read_bytes()


def test_unseeded_grain_and_custom_layers_fail_before_output(tmp_path):
    canvas = Canvas(16, 16).background(color="#112233", effects=[Grain(intensity=0.2)])
    path = tmp_path / "grain.gif"
    with pytest.raises(ValidationError, match="explicit Grain seed"):
        canvas.render(str(path), animation=GifOptions(workers=2))
    assert not path.exists()
    canvas = Canvas(16, 16).custom(lambda image: image)
    with pytest.raises(ValidationError, match="custom/plugin"):
        canvas.render(str(path), animation=GifOptions(workers=2))
    assert not path.exists()


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg/ffprobe not installed")
@pytest.mark.parametrize("reduced", [False, True])
@pytest.mark.parametrize("hold", [0.0, 0.01])
def test_local_video_and_disappearing_captions_match(tmp_path, reduced, hold):
    from PIL import Image
    from quickthumb.models import VideoCaption

    source = tmp_path / "source.mp4"
    raw = b"".join(
        Image.new("RGB", (24, 18), (30 * i, 120, 230 - 25 * i)).tobytes() for i in range(6)
    )
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "rawvideo",
            "-pixel_format",
            "rgb24",
            "-video_size",
            "24x18",
            "-framerate",
            "10",
            "-i",
            "pipe:0",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(source),
        ],
        input=raw,
        capture_output=True,
        check=True,
    )
    canvas = (
        Canvas(64, 40)
        .background(color="#223344")
        .video(
            str(source),
            position=(2, 1),
            width=24,
            height=18,
            start=0.15,
            duration=0.6,
            animation=Fade(duration=0.1),
            captions=[
                VideoCaption(
                    text="cue", start=0.05, end=0.42, position=(40, 30), size=10, font=FONT
                )
            ],
        )
        .shape("rectangle", (0, 24), 64, 16, "#000000")
    )
    before = _shots([canvas], [None], 1, hold=hold, reduced=reduced)
    after = _shots([canvas], [None], 2, hold=hold, reduced=reduced)
    assert after == before
    assert any(caption for _, _, _, caption in after) or reduced


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg/ffprobe not installed")
@pytest.mark.parametrize("container", ["mp4", "webm"])
def test_parallel_video_crosses_encoded_batch_boundaries(tmp_path, container):
    canvas = (
        Canvas(32, 20)
        .background(color="#123456")
        .shape("rectangle", (2, 2), 20, 14, "#FF3344", animation=Fade(duration=6.5))
    )
    outputs = []
    for workers in (1, 2):
        data = video.export_animation_bytes(
            [canvas], [None], container, fps=10, slide_duration=0, workers=workers
        )
        path = tmp_path / f"{workers}.{container}"
        path.write_bytes(data)
        outputs.append(
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
                check=True,
                capture_output=True,
            ).stdout
        )
    assert outputs[0] == outputs[1]
    assert len(outputs[0]) == 65 * 32 * 20 * 3


def test_static_deck_mp4_route_does_not_create_parallel_renderer(tmp_path, monkeypatch):
    # A .mp4 Deck without VideoOptions remains the distinct static narrated exporter.
    from quickthumb import _export_deck_mp4, _render_workers

    calls = []
    monkeypatch.setattr(
        _export_deck_mp4, "render_deck_mp4", lambda *args, **kwargs: calls.append(True)
    )
    monkeypatch.setattr(
        _render_workers, "ParallelFrames", lambda *args, **kwargs: pytest.fail("unexpected workers")
    )
    Deck(16, 16).slide(Canvas().background(color="#112233")).render(str(tmp_path / "static.mp4"))
    assert calls == [True]


def test_parallel_motion_path_skips_parent_serial_morph_planning(monkeypatch):
    from PIL import Image

    canvas = Canvas(8, 8).background(color="#112233")
    animator = video._SlideAnimator(canvas, {})
    frame = Image.new("RGB", (8, 8), (20, 30, 40))

    class Renderer:
        def frames(self, index, samples):
            assert index == 3
            for time, duration in samples:
                yield time, duration, frame

    monkeypatch.setattr(video, "_morph_source", lambda *args: pytest.fail("serial planning ran"))
    shots = list(
        video._slide_motion_shots(
            animator,
            None,
            0.1,
            0.1,
            frame,
            (8, 8),
            (0, 0, 0),
            10,
            None,
            canvas,
            renderer=cast(ParallelFrames, Renderer()),
            slide_index=3,
        )
    )
    assert len(shots) == 1
    assert shots[0].frame is frame
    assert shots[0].duration == 0.1
