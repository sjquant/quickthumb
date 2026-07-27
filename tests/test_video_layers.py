"""Behavioral specifications for the constrained VideoLayer composition API."""

import json
import shutil
import subprocess
from io import BytesIO

import pytest
from PIL import Image
from quickthumb import Canvas, Deck, ValidationError
from quickthumb.models import VideoLayer

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
    image = Image.open(BytesIO(data))
    frames = []
    for _ in range(image.n_frames):
        image.seek(len(frames))
        frames.append(image.convert("RGBA"))
    return frames


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
            captions=[{"text": "bad", "start": 1, "end": 1}],
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
        captions=[{"text": "hello", "start": 0.1, "end": 0.4}],
    )

    restored = Canvas.from_json(canvas.to_json())

    payload = json.loads(restored.to_json())
    layer = payload["layers"][0]
    assert layer["trim_start"] == 0.25
    assert layer["trim_end"] == 0.75
    assert layer["start"] == 0.1
    assert layer["speed"] == 2.0
    assert layer["captions"][0]["text"] == "hello"


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

    assert contain_frame.getpixel((32, 0))[3] == 0
    assert cover_frame.getpixel((32, 0))[3] == 255
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

    gif_with_caption = _gif_frames(canvas.to_gif(fps=10, hold=0))
    plain = Canvas(96, 64).video(
        str(source_video),
        (16, 8),
        64,
        48,
        trim_start=0.25,
        trim_end=0.75,
        speed=2,
    )
    gif_without_caption = _gif_frames(plain.to_gif(fps=10, hold=0))
    assert any(
        a.tobytes() != b.tobytes()
        for a, b in zip(gif_with_caption, gif_without_caption, strict=True)
    )


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

    frames = _gif_frames(deck.to_gif(fps=10, slide_duration=0))

    assert len(frames) >= 2
