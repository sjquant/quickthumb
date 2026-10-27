"""Behavioral specifications for the constrained VideoLayer composition API."""

import cmath
import json
import math
import shutil
import struct
import subprocess
from bisect import bisect_right
from io import BytesIO
from itertools import accumulate
from pathlib import Path
from typing import cast

import pytest
from PIL import Image, ImageChops, ImageStat
from quickthumb import (
    AnimationSpec,
    AudioTrack,
    Canvas,
    Deck,
    ExportPolicy,
    GifOptions,
    ValidationError,
    VideoOptions,
)
from quickthumb.models import VideoCaption, VideoLayer
from quickthumb.transitions import Cut, Fade, Morph

from tests._helpers import pixel_rgb

HAS_FFMPEG = shutil.which("ffmpeg") is not None
HAS_FFPROBE = shutil.which("ffprobe") is not None


@pytest.fixture()
def source_video(tmp_path):
    """Given a one-second red/blue clip with a one-second audio stream."""
    output = tmp_path / "source.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=64x32:r=10:d=0.5",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=64x32:r=10:d=0.5",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000:duration=1",
            "-filter_complex",
            "[0:v][1:v]concat=n=2:v=1:a=0[v]",
            "-map",
            "[v]",
            "-map",
            "2:a",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(output),
        ],
        check=True,
    )
    return output


def _gif_frames(data: bytes):
    return [frame for frame, _ in _gif_frames_with_durations(data)]


def _gif_frames_with_durations(data: bytes):
    image = Image.open(BytesIO(data))
    frames = []
    for _ in range(int(getattr(image, "n_frames", 1))):
        image.seek(len(frames))
        frames.append((image.convert("RGBA"), image.info.get("duration", 0)))
    return frames


def _decoded_frame(path: Path, time: float) -> Image.Image:
    """Decode one public export frame for codec-level assertions."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            str(time),
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-f",
            "image2pipe",
            "-vcodec",
            "png",
            "pipe:1",
        ],
        capture_output=True,
        check=True,
    )
    return Image.open(BytesIO(result.stdout)).convert("RGB")


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg is required")
def test_video_layer_rejects_invalid_trim_and_caption_ranges():
    """Given invalid ranges, when a VideoLayer is constructed, then validation fails."""
    with pytest.raises(ValidationError, match="trim_end"):
        VideoLayer(
            type="video",
            source="clip.mp4",
            position=(0, 0),
            width=20,
            height=20,
            trim_start=1,
            trim_end=1,
        )

    with pytest.raises(ValidationError, match="caption end"):
        VideoLayer(
            type="video",
            source="clip.mp4",
            position=(0, 0),
            width=20,
            height=20,
            captions=cast(list[VideoCaption], [{"text": "bad", "start": 1, "end": 1}]),
        )


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg is required")
def test_video_layer_round_trips_through_public_canvas_json(source_video):
    """Given a configured clip, when Canvas JSON round-trips, then its timing survives."""
    canvas = Canvas(96, 64).video(
        str(source_video),
        position=(8, 4),
        width=64,
        height=48,
        trim_start=0.25,
        trim_end=0.75,
        start=0.1,
        speed=2,
        volume=0.4,
        captions=[
            {
                "text": "hello",
                "font": "Pretendard-Regular.woff2",
                "vertical_align": "optical-center",
                "start": 0.1,
                "end": 0.4,
            }
        ],
    )

    restored = Canvas.from_json(canvas.to_json())

    payload = json.loads(restored.to_json())
    layer = payload["layers"][0]
    assert layer["trim_start"] == 0.25
    assert layer["trim_end"] == 0.75
    assert layer["start"] == 0.1
    assert layer["speed"] == 2.0
    assert layer["captions"][0]["text"] == "hello"
    assert layer["captions"][0]["font"] == "Pretendard-Regular.woff2"
    assert layer["captions"][0]["vertical_align"] == "optical-center"


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg is required")
def test_video_caption_background_is_serializable_and_changes_only_active_frames(source_video):
    """Given a caption background, when it is sampled, then it is deterministic and time-bound."""
    canvas = Canvas(96, 64).video(
        str(source_video),
        (8, 8),
        64,
        48,
        captions=[
            {
                "text": "caption",
                "start": 0.1,
                "end": 0.3,
                "background": "#000000",
                "background_opacity": 0.6,
                "padding": (1, 8, 3, 4),
                "border_radius": 4,
            }
        ],
    )

    restored = Canvas.from_json(canvas.to_json())
    before = restored.render_frame(0.09)
    active = restored.render_frame(0.2)
    after = restored.render_frame(0.3)

    assert before.tobytes() == after.tobytes()
    assert active.tobytes() != before.tobytes()
    assert active.tobytes() == restored.render_frame(0.2).tobytes()


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg is required")
def test_video_captions_render_above_later_canvas_layers(source_video):
    """Given a later shade, when a cue is active, then its glyphs stay foreground-visible."""
    # Given: a caption-owned video followed by a mostly opaque full-canvas shade
    canvas = Canvas(96, 64).video(
        str(source_video),
        (0, 0),
        96,
        64,
        captions=[
            {
                "text": "caption",
                "start": 0.1,
                "end": 0.3,
                "size": 12,
                "color": "#FFFFFF",
            }
        ],
    )
    canvas.shape("rectangle", (0, 0), 96, 64, "#000000", opacity=0.9)

    # When: the public frame renderer samples the active cue
    frame = canvas.render_frame(0.2).convert("RGB")
    plain = Canvas(96, 64).video(str(source_video), (0, 0), 96, 64)
    plain.shape("rectangle", (0, 0), 96, 64, "#000000", opacity=0.9)
    baseline = plain.render_frame(0.2).convert("RGB")

    # Then: the caption remains visibly white instead of being dimmed by the shade
    changed = ImageChops.difference(frame, baseline).getbbox()
    assert changed is not None
    assert changed[1] > frame.height // 2

    # The animated exporter uses the same foreground pass as direct sampling.
    lower = (0, frame.height // 2, frame.width, frame.height)
    exported_timed = _gif_frames_with_durations(canvas.to_gif(fps=10, hold=0))
    exported_gif = [frame for frame, _ in exported_timed]
    assert sum(duration for _, duration in exported_timed) / 1000 == pytest.approx(1.0, abs=0.15)
    assert any(
        min(exported.getpixel((x, y))) > 240
        for exported in exported_gif
        for y in range(lower[1], lower[3])
        for x in range(lower[0], lower[2])
    )


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg is required")
def test_video_caption_rejects_negative_padding(source_video):
    """Given negative caption padding, when the layer is built, then validation fails."""
    with pytest.raises(ValidationError, match="padding cannot be negative"):
        Canvas(96, 64).video(
            str(source_video),
            (8, 8),
            64,
            48,
            captions=[{"text": "caption", "start": 0, "end": 1, "padding": -1}],
        )


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg is required")
def test_video_layer_inspection_and_static_fallback_keep_delayed_clips_visible(source_video):
    """Given a delayed clip, inspection and SVG fallback keep video identified and visible."""
    canvas = Canvas(96, 64).video(
        str(source_video), (8, 8), 64, 48, start=0.2, trim_start=0.1, trim_end=0.4
    )

    assert canvas.inspect().layers[0].type == "video"
    assert "data:image/png;base64," in canvas.to_svg()


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg is required")
def test_video_layer_fit_and_trim_change_public_frame_content(source_video):
    """Given a clip, when fit and trim vary, then the public frame changes predictably."""
    contain = Canvas(64, 64).video(str(source_video), (0, 0), 64, 64, fit="contain")
    cover = Canvas(64, 64).video(str(source_video), (0, 0), 64, 64, fit="cover")

    contain_frame = contain.render_frame(0.1)
    cover_frame = cover.render_frame(0.1)

    contain_pixel = cast(tuple[int, int, int, int], contain_frame.getpixel((32, 0)))
    cover_pixel = cast(tuple[int, int, int, int], cover_frame.getpixel((32, 0)))
    assert contain_pixel[3] == 0
    assert cover_pixel[3] == 255
    assert contain.render_frame(0.1).tobytes() == contain.render_frame(0.1).tobytes()


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg is required")
def test_caption_cues_have_deterministic_half_open_boundaries(source_video):
    """Caption sampling uses an inclusive start and exclusive end boundary."""
    canvas = Canvas(96, 64).video(
        str(source_video),
        (8, 8),
        64,
        48,
        captions=[{"text": "caption", "start": 0.1, "end": 0.3, "size": 12}],
    )

    before = canvas.render_frame(0.09)
    active = canvas.render_frame(0.2)
    after = canvas.render_frame(0.3)

    assert before.tobytes() == after.tobytes()
    assert active.tobytes() != before.tobytes()


@pytest.mark.skipif(not (HAS_FFMPEG and HAS_FFPROBE), reason="FFmpeg tools are required")
def test_video_layer_speed_duration_caption_and_audio_stay_synchronized(source_video, tmp_path):
    """Given a sped-up clip, when MP4 and WebM export, then duration, captions, and audio align."""
    canvas = Canvas(96, 64).video(
        str(source_video),
        (16, 8),
        64,
        48,
        trim_start=0.25,
        trim_end=0.75,
        speed=2,
        volume=0.25,
        captions=[{"text": "caption", "start": 0.1, "end": 0.3, "size": 12}],
    )
    mp4 = tmp_path / "clip.mp4"
    webm = tmp_path / "clip.webm"

    plain = Canvas(96, 64).video(
        str(source_video),
        (16, 8),
        64,
        48,
        trim_start=0.25,
        trim_end=0.75,
        speed=2,
    )
    canvas.shape("rectangle", (0, 0), 96, 64, "#000000", opacity=0.9)
    plain.shape("rectangle", (0, 0), 96, 64, "#000000", opacity=0.9)
    mp4.write_bytes(canvas.to_mp4(fps=10, hold=0))
    webm.write_bytes(canvas.to_webm(fps=10, hold=0))

    for output in (mp4, webm):
        metadata = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_type",
                "-of",
                "json",
                str(output),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(metadata.stdout)
        assert float(payload["format"]["duration"]) == pytest.approx(0.25, abs=0.15)
        assert {stream["codec_type"] for stream in payload["streams"]} == {"video", "audio"}
        baseline_path = tmp_path / f"plain-{output.suffix[1:]}.mp4"
        if output.suffix == ".webm":
            baseline_path = tmp_path / "plain.webm"
            baseline_path.write_bytes(plain.to_webm(fps=10, hold=0))
        else:
            baseline_path.write_bytes(plain.to_mp4(fps=10, hold=0))
        exported = _decoded_frame(output, 0.125)
        baseline = _decoded_frame(baseline_path, 0.125)
        caption_region = (16, 32, 80, 64)
        assert (
            ImageChops.difference(
                exported.crop(caption_region), baseline.crop(caption_region)
            ).getbbox()
            is not None
        )

    gif_timed = _gif_frames_with_durations(canvas.to_gif(fps=10, hold=0))
    gif_with_caption = [frame for frame, _ in gif_timed]
    assert sum(duration for _, duration in gif_timed) / 1000 == pytest.approx(0.25, abs=0.1)
    caption_region = (16, 32, 80, 64)
    assert any(
        min(frame.getpixel((x, y))) > 240
        for frame in gif_with_caption
        for y in range(caption_region[1], caption_region[3])
        for x in range(caption_region[0], caption_region[2])
    )


@pytest.mark.skipif(not (HAS_FFMPEG and HAS_FFPROBE), reason="FFmpeg tools are required")
@pytest.mark.parametrize(
    "container,reduced",
    [("gif", False), ("gif", True), ("mp4", False), ("webm", False), ("mp4", True), ("webm", True)],
)
def test_motion_package_keeps_frames_captions_and_narration_aligned(
    source_video, tmp_path, container, reduced
):
    """A three-slide package keeps motion, caption cues and mixed audio on its declared clock."""
    # Given: a fading title card followed by a narrated clip with a short caption.
    # Every boundary is on the 10 fps grid; normal GIF uses advance_after instead of narration.
    opening = (
        Canvas(96, 64)
        .background(color="#102030")
        .shape("rectangle", (8, 4), 24, 12, "#00FF00", animation=AnimationSpec.fade(duration=0.4))
    )
    closing = (
        Canvas(96, 64)
        .background(color="#304050")
        .video(
            str(source_video),
            (16, 24),
            64,
            32,
            trim_end=0.6,
            volume=0,
            captions=[{"text": "GO", "start": 0.4, "end": 0.6, "size": 12, "position": (48, 48)}],
        )
    )
    deck = (
        Deck(96, 64)
        .slide(opening, transition=Cut(advance_after=0.8), duration=0.8)
        .slide(
            closing,
            transition=Fade(duration=0.2, advance_after=0.6),
            audio=str(source_video),
            duration=0.8,
        )
        .slide(
            Canvas(96, 64).background(color="#102030"),
            transition=Fade(duration=0.2, advance_after=0.3),
            duration=0.5,
        )
    )
    output = tmp_path / f"motion-package.{container}"
    if container == "gif":
        options = GifOptions(fps=10, hold=0.8)
    else:
        music = tmp_path / "music.wav"
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=880:sample_rate=8000:duration=0.2",
                str(music),
            ],
            check=True,
        )
        options = VideoOptions(
            fps=10,
            hold=0.8,
            workers=2 if container == "webm" else 1,
            soundtrack=AudioTrack(path=str(music), volume=0.2, loop=True),
        )

    # When: the public export writes the complete package and its receipt.
    result = deck.export(output, animation=options, policy=ExportPolicy(reduced_motion=reduced))
    metadata = json.loads(
        subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-count_frames",
                "-show_entries",
                "stream=codec_type,avg_frame_rate,nb_read_frames",
                "-of",
                "json",
                str(output),
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )
    times = [0.0, 0.2, 0.7, 0.8, 0.9, 1.1, 1.2, 1.4, 1.5, 1.6, 1.7]
    reduced_gif = container == "gif" and reduced
    if reduced_gif:
        # GIF ignores explicit slide durations. Removing authored transitions
        # restores the default 0.5s incoming fades: windows end at .8, 2.2, 3.5.
        times[-2:] = [2.2, 2.3]
    if container == "gif":
        frames = _gif_frames_with_durations(output.read_bytes())
        ends_ms = list(accumulate(duration for _, duration in frames))
        observed = [
            frames[bisect_right(ends_ms, round(time * 1000))][0].convert("RGB") for time in times
        ]
        assert ends_ms[-1] / 1000 == result.timing_metrics.duration == (3.5 if reduced_gif else 2.1)
        assert {stream["codec_type"] for stream in metadata["streams"]} == {"video"}
    else:
        raw = subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                str(output),
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
        ).stdout
        frame_size = 96 * 64 * 3
        frames = [
            Image.frombytes("RGB", (96, 64), raw[offset : offset + frame_size])
            for offset in range(0, len(raw), frame_size)
        ]
        observed = [frames[round(time * 10)] for time in times]
        video_stream = next(
            stream for stream in metadata["streams"] if stream["codec_type"] == "video"
        )
        assert video_stream["avg_frame_rate"] == "10/1"
        assert int(video_stream["nb_read_frames"]) == len(frames) == 21
        assert len(frames) / 10 == result.timing_metrics.duration == 2.1
        assert {stream["codec_type"] for stream in metadata["streams"]} == {"video", "audio"}

        # The music is audible before the next slide; its narration joins at 0.8s.
        pcm = subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                str(output),
                "-map",
                "0:a",
                "-f",
                "s16le",
                "-ar",
                "8000",
                "-ac",
                "1",
                "-",
            ],
            capture_output=True,
            check=True,
        ).stdout
        samples = struct.unpack(f"<{len(pcm) // 2}h", pcm)

        def amplitude(frequency, start):
            window = samples[round(start * 8000) : round((start + 0.2) * 8000)]
            return (
                2
                * abs(
                    sum(
                        value * cmath.exp(-2j * math.pi * frequency * index / 8000)
                        for index, value in enumerate(window)
                    )
                )
                / len(window)
            )

        assert amplitude(880, 0.3) > 100, "soundtrack missing before narration"
        assert amplitude(880, 1.1) > 100, "looped soundtrack missing on narrated slide"
        assert amplitude(440, 1.1) > 10 * amplitude(440, 0.3) + 200, (
            "narration starts on wrong slide"
        )

    # Then: independent visual anchors identify motion, the clip and half-open caption cues.
    assert result.timing_metrics.fps == 10
    assert result.timing_metrics.frame_count == result.pixel_metrics.frame_count == len(frames)
    (
        first,
        middle,
        settled,
        boundary,
        transition,
        before_caption,
        caption,
        after_caption,
        final,
        next_boundary,
        next_transition,
    ) = observed
    assert pixel_rgb(settled, (16, 10)) == pytest.approx((0, 255, 0), abs=24)
    assert pixel_rgb(boundary, (16, 10)) == pytest.approx((0, 255, 0), abs=24)
    assert 64 < pixel_rgb(transition, (16, 10))[1] < 255
    if reduced:
        assert pixel_rgb(first, (16, 10)) == pytest.approx((0, 255, 0), abs=24)
        assert pixel_rgb(final, (20, 28)) == pytest.approx((255, 0, 0), abs=24)
    else:
        assert pixel_rgb(first, (16, 10)) == pytest.approx((16, 32, 48), abs=24)
        assert 40 < pixel_rgb(middle, (16, 10))[1] < 250
        assert pixel_rgb(final, (20, 28)) == pytest.approx((0, 0, 255), abs=24)
        canonical = deck.sample(times, hold=0.8)
        assert [(part.start, part.end) for part in canonical.timeline] == [
            (0.0, 0.8),
            (0.8, 1.6),
            (1.6, 2.1),
        ]
        for time, actual, expected in zip(times, observed, canonical.frames, strict=True):
            error = ImageStat.Stat(
                ImageChops.difference(actual, expected.to_image().convert("RGB"))
            ).mean
            assert max(error) < 8, f"{container} pixels drift at {time}s: {error}"
    caption_region = (24, 36, 72, 60)
    assert sum(before_caption.crop(caption_region).convert("L").histogram()[220:]) == 0
    assert sum(caption.crop(caption_region).convert("L").histogram()[220:]) > 2
    for frame in (after_caption, final, next_boundary, next_transition):
        assert sum(frame.crop(caption_region).convert("L").histogram()[220:]) == 0


@pytest.mark.skipif(not (HAS_FFMPEG and HAS_FFPROBE), reason="FFmpeg tools are required")
def test_reduced_motion_ignores_captions_outside_the_clip(source_video, tmp_path):
    """A caption starting at the clip's exclusive end cannot extend frozen playback."""
    # Given: a frozen 0.3s trimmed clip whose subtraction has floating-point noise
    canvas = Canvas(96, 64).video(
        str(source_video),
        (16, 24),
        64,
        32,
        trim_start=0.1,
        trim_end=0.4,
        captions=[{"text": "outside", "start": 0.3, "end": 0.6, "size": 12}],
    )
    output = tmp_path / "outside.gif"

    # When: reduced-motion output is encoded through the public file contract
    result = canvas.export(
        output,
        animation=GifOptions(fps=10, hold=0.1),
        policy=ExportPolicy(reduced_motion=True),
    )

    # Then: the unreachable cue adds neither playback time nor encoded frames
    frames = _gif_frames_with_durations(output.read_bytes())
    assert result.timing_metrics.duration == sum(duration for _, duration in frames) / 1000 == 0.1
    assert result.timing_metrics.frame_count == len(frames) == 1


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg is required")
def test_captioned_morph_falls_back_to_timed_fade(source_video):
    """Given captioned morph slides, when exported, then captions keep fade timing."""
    source = Canvas(96, 64).video(
        str(source_video),
        (0, 0),
        96,
        64,
        motion_key="clip",
        captions=[{"text": "source", "start": 0.1, "end": 0.4, "size": 12}],
    )
    target = Canvas(96, 64).video(
        str(source_video),
        (0, 0),
        96,
        64,
        motion_key="clip",
        captions=[{"text": "target", "start": 0.1, "end": 0.4, "size": 12}],
    )

    morph = Deck(slides=[source, target], transition=Morph(duration=0.4))
    fade = Deck(slides=[source, target], transition=Fade(duration=0.4))

    morph_frames = _gif_frames(morph.to_gif(fps=10, hold=0))
    fade_frames = _gif_frames(fade.to_gif(fps=10, hold=0))
    assert len(morph_frames) == len(fade_frames)
    assert all(
        ImageChops.difference(morph_frame, fade_frame).getbbox() is None
        for morph_frame, fade_frame in zip(morph_frames, fade_frames, strict=True)
    )
    diagnostic = [
        item for item in morph.validate_export("video") if item.feature == "morph_caption_timing"
    ]
    assert len(diagnostic) == 1
    assert diagnostic[0].fallback == "fade"
    inspection = morph.inspect_motion(target="video")
    assert any(item.feature == "morph_caption_timing" for item in inspection.diagnostics)


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg is required")
def test_video_caption_outside_canvas_is_diagnosed_and_safely_rendered(source_video):
    """Given an edge-anchored caption, when rendered, then it is diagnosed and kept visible."""
    # Given: a caption whose center anchor would place its background outside the canvas
    canvas = Canvas(96, 64).video(
        str(source_video),
        (16, 8),
        64,
        48,
        captions=[
            {
                "text": "caption extends left",
                "start": 0,
                "end": 1,
                "position": (2, 40),
                "size": 12,
                "background": "#000000",
                "padding": (4, 8),
            }
        ],
    )

    # When: public diagnostics and frame rendering are requested
    diagnostics = canvas.diagnose().findings
    frame = canvas.render_frame(0.2)

    # Then: the unsafe source geometry is reported and rendering still succeeds
    clipped = [finding for finding in diagnostics if finding.code == "text-clipped"]
    assert clipped
    assert clipped[0].measured["caption_index"] == 0
    assert frame.size == (96, 64)


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg is required")
def test_video_caption_ink_is_optically_centered_inside_its_background(source_video):
    """Given a caption cue, when rendered, then visible glyph ink is centered in its box."""
    # Given: a centered caption using a real font with non-symmetric vertical metrics
    font = str(Path(__file__).parents[1] / "assets" / "fonts" / "Pretendard-Regular.woff2")
    canvas = Canvas(96, 64).video(
        str(source_video),
        (0, 0),
        96,
        64,
        captions=[
            {
                "text": "정렬된 자막",
                "font": font,
                "vertical_align": "optical-center",
                "start": 0,
                "end": 1,
                "position": (48, 32),
                "size": 12,
                "color": "#FFFFFF",
                "background": "#000000",
                "padding": 6,
            }
        ],
    )

    # When: the public frame renderer composites the caption
    frame = canvas.render_frame(0.2).convert("RGB")
    black = [
        (x, y)
        for y in range(frame.height)
        for x in range(frame.width)
        if max(pixel_rgb(frame, (x, y))) < 20
    ]
    white = [
        (x, y)
        for y in range(frame.height)
        for x in range(frame.width)
        if min(pixel_rgb(frame, (x, y))) > 220
    ]

    # Then: the glyph ink center stays within 2px of the background center
    background_center_y = (min(y for _, y in black) + max(y for _, y in black)) / 2
    ink_center_y = (min(y for _, y in white) + max(y for _, y in white)) / 2
    assert ink_center_y < background_center_y
    assert abs(background_center_y - ink_center_y) <= 2


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg is required")
def test_video_caption_diagnostics_cover_multiline_timing_and_background_overlap(source_video):
    """Given overlapping multiline cues, when diagnosed, then timing and overlap are explicit."""
    # Given: two centered Korean/English cues, with one extending beyond the layer timeline
    canvas = Canvas(160, 96).video(
        str(source_video),
        (16, 8),
        128,
        80,
        trim_start=0,
        trim_end=1,
        duration=1,
        captions=[
            {
                "text": "첫 줄\nSECOND LINE",
                "start": 0,
                "end": 0.8,
                "position": (80, 48),
                "size": 12,
                "background": "#000000",
                "padding": (4, 8),
            },
            {
                "text": "겹치는 자막",
                "start": 0.4,
                "end": 1.2,
                "position": (80, 48),
                "size": 12,
                "background": "#000000",
                "padding": (4, 8),
            },
        ],
    )

    # When: the public diagnostic API inspects the composition
    codes = [finding.code for finding in canvas.diagnose().findings]

    # Then: multiline geometry remains safe and semantic timing issues are reported
    assert "text-clipped" not in codes
    assert "caption-timing" in codes
    assert "caption-overlap" in codes


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg is required")
def test_video_caption_safe_area_diagnostic_reports_a_caption_near_the_bottom_edge(source_video):
    """Given a bottom-edge cue, when diagnosed, then its safe-area risk is explicit."""
    # Given: a caption whose background enters the 24px canvas safety margin
    canvas = Canvas(160, 96).video(
        str(source_video),
        (0, 0),
        160,
        96,
        trim_end=1,
        captions=[
            {
                "text": "Bottom edge",
                "start": 0,
                "end": 0.5,
                "position": (80, 90),
                "size": 12,
                "background": "#000000",
                "padding": 4,
            }
        ],
    )

    # When: the public diagnostic API inspects the composition
    findings = canvas.diagnose().findings

    # Then: the caption is identified without requiring an export
    assert any(finding.code == "caption-safe-area" for finding in findings)


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg is required")
def test_video_layer_rejects_duration_longer_than_trimmed_source(source_video):
    """Given a short clip, when duration exceeds its source, then rendering fails safely."""
    canvas = Canvas(96, 64).video(str(source_video), (0, 0), 64, 32, duration=2)

    with pytest.raises(ValidationError, match="exceeds available trimmed video duration"):
        canvas.render_frame(0)


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg is required")
def test_video_layer_missing_source_has_safe_error():
    """Given a missing source, when it is rendered, then the public error identifies the source."""
    canvas = Canvas(32, 32).video("missing.mp4", (0, 0), 32, 32)
    with pytest.raises(FileNotFoundError, match="missing.mp4"):
        canvas.render_frame(0)


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg is required")
def test_deck_exports_a_canvas_video_layer_through_the_public_timeline(source_video):
    """Given a Deck slide containing a clip, when GIF export runs, then the clip is sampled."""
    deck = Deck(96, 64).slide(
        Canvas().video(str(source_video), (8, 8), 64, 48, trim_start=0.25, trim_end=0.75)
    )

    frames = _gif_frames(deck.to_gif(fps=10, hold=0))

    assert len(frames) >= 2
