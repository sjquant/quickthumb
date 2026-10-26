"""Temporal exposure through real files and independently located pixel anchors."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image, ImageSequence
from quickthumb import (
    AnimationSpec,
    Canvas,
    GifOptions,
    ImageSequenceOptions,
    KeyframeSpec,
    MotionBlur,
    PositionTrack,
    VideoOptions,
)


@pytest.mark.parametrize("workers", [1, 2])
def test_exposure_preserves_red_in_transparent_motion_trails(tmp_path, workers):
    """A moving red patch has half-alpha edges and saturated color across its exposure."""
    # Given: a four-pixel red patch travels sixteen pixels in one second.
    canvas = Canvas(24, 8).shape(
        "rectangle",
        (2, 2),
        4,
        4,
        "#FF0000",
        animation=AnimationSpec.timeline(
            PositionTrack(
                keyframes=[
                    KeyframeSpec(time=0, value=(0, 0)),
                    KeyframeSpec(time=1, value=(16, 0)),
                ]
            )
        ),
    )

    # When: the exposure at .25 seconds averages the positions at .1875 and .3125.
    result = canvas.export_image_sequence(
        tmp_path / "frames",
        options=ImageSequenceOptions(
            fps=4, hold=0.25, workers=workers, motion_blur=MotionBlur(samples=2, shutter_angle=360)
        ),
    )

    # Then: positions 5 and 10 receive one sample, while 7 receives both samples.
    with Image.open(Path(result.output_directory) / "000001.png") as frame:
        assert frame.getpixel((4, 3)) == (0, 0, 0, 0)
        assert frame.getpixel((5, 3)) == (255, 0, 0, 128)
        assert frame.getpixel((7, 3)) == (255, 0, 0, 255)
        assert frame.getpixel((10, 3)) == (255, 0, 0, 128)
        assert frame.getpixel((11, 3)) == (0, 0, 0, 0)
    assert (result.frame_count, result.duration) == (5, 1.25)
    assert any(row.feature == "motion_blur" for row in result.capability_report)
    assert not any(row.feature == "motion_blur" for row in canvas.inspect_motion().capabilities)


@pytest.mark.parametrize("format", ["gif", "mp4"])
def test_fractional_exposure_reports_actual_encoded_playback(tmp_path, format):
    """A fractional Canvas timeline retains GIF delays and the allocated video frame clock."""
    # Given: motion and hold occupy .25 seconds at a requested ten frames per second.
    if format == "mp4" and not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg is required for MP4 output")
    canvas = Canvas(32, 16).shape(
        "rectangle", (4, 4), 12, 8, "#FF0000", animation=AnimationSpec.fade(duration=0.17)
    )
    options = GifOptions if format == "gif" else VideoOptions

    # When: writing and decoding a two-sample temporal exposure.
    result = canvas.export(
        tmp_path / f"fractional.{format}",
        animation=options(fps=10, hold=0.08, motion_blur=MotionBlur(samples=2)),
    )

    # Then: metadata describes the encoded delays/count, including format quantization.
    if format == "gif":
        with Image.open(result.written_paths[0]) as image:
            decoded = [
                (frame.info["duration"], frame.convert("RGB").getpixel((8, 8)))
                for frame in ImageSequence.Iterator(image)
            ]
            durations = [duration for duration, _ in decoded]
            assert len(durations) == result.timing_metrics.frame_count == 3
            assert sum(durations) == 250
            # GIF's last shot starts at 1/6 second and still exposes the fade.
            assert decoded[-1][1] == (243, 0, 0)
        assert result.timing_metrics.duration == 0.25
    else:
        stream = json.loads(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-count_frames",
                    "-show_entries",
                    "stream=nb_read_frames,duration,r_frame_rate",
                    "-of",
                    "json",
                    result.written_paths[0],
                ]
            )
        )["streams"][0]
        assert stream["nb_read_frames"] == "3"
        assert stream["r_frame_rate"] == "10/1"
        assert float(stream["duration"]) == result.timing_metrics.duration == 0.3
        assert result.timing_metrics.frame_count == 3
        pixels = subprocess.check_output(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                result.written_paths[0],
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-",
            ]
        )
        last = pixels[-32 * 16 * 3 :]
        # The CFR frame at .2 exposes .1875/.2125, both after the .17 fade.
        assert last[(8 * 32 + 8) * 3] >= 250
    assert result.timing_metrics.fps == 10

    if format == "gif":
        # Image sequences use the CFR observation grid, with exact alpha.
        sequence = canvas.export_image_sequence(
            tmp_path / "frames",
            options=ImageSequenceOptions(fps=10, hold=0.08, motion_blur=MotionBlur(samples=2)),
        )
        with Image.open(Path(sequence.output_directory) / "000002.png") as frame:
            assert frame.getpixel((8, 8)) == (255, 0, 0, 255)


@pytest.mark.parametrize("hard_cut", [False, True])
def test_deck_exposure_matches_spawned_rgba_and_respects_cuts(tmp_path, hard_cut):
    """Smooth transitions expose both sides, while hard cuts never blend slides."""
    from quickthumb import Deck
    from quickthumb.transitions import Cut, Fade

    first = Canvas(16, 8).shape("rectangle", (2, 2), 4, 4, "#FF0000")
    second = Canvas(16, 8).shape("rectangle", (2, 2), 4, 4, "#0000FF")
    deck = (
        Deck()
        .slide(first, duration=0.2)
        .slide(second, duration=0.2, transition=Cut() if hard_cut else Fade(duration=0.1))
    )
    rendered = []
    for workers in (1, 2):
        result = deck.export_image_sequence(
            tmp_path / f"workers-{workers}",
            options=ImageSequenceOptions(
                fps=10, workers=workers, motion_blur=MotionBlur(samples=2, shutter_angle=360)
            ),
        )
        frames = []
        for path in sorted(Path(result.output_directory).glob("*.png")):
            with Image.open(path) as frame:
                frames.append(frame.copy())
        rendered.append((result.duration, [frame.tobytes() for frame in frames]))
        assert frames[2].getpixel((15, 7)) == (0, 0, 0, 0)
        boundary = frames[2].getpixel((3, 3))
        if hard_cut:
            assert boundary == (0, 0, 255, 255)
            assert frames[3].getpixel((3, 3)) == (0, 0, 255, 255)
        else:
            assert boundary[0] > 0 and boundary[2] > 0 and boundary[3] == 255
            assert frames[3].getpixel((3, 3)) == (5, 0, 250, 255)
        for frame in frames:
            frame.close()
    assert rendered[0] == rendered[1]


def test_exposure_before_fractional_cut_stays_on_outgoing_slide(tmp_path):
    """A shutter extending past a .22-second cut cannot introduce its next slide."""
    from quickthumb import Deck
    from quickthumb.transitions import Cut

    deck = (
        Deck()
        .slide(Canvas(8, 8).background(color="#FF0000"), duration=0.22)
        .slide(Canvas(8, 8).background(color="#0000FF"), duration=0.2, transition=Cut())
    )
    result = deck.export_image_sequence(
        tmp_path / "fractional-cut",
        options=ImageSequenceOptions(fps=10, motion_blur=MotionBlur(samples=2, shutter_angle=360)),
    )
    with Image.open(Path(result.output_directory) / "000002.png") as frame:
        assert frame.getpixel((4, 4)) == (255, 0, 0, 255)


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg is required")
def test_deck_caption_exposure_is_identical_with_spawned_workers(tmp_path):
    """A cue inside a shutter window contributes through the existing caption compositor."""
    from quickthumb import Deck
    from quickthumb.transitions import Cut

    source = tmp_path / "black.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=64x32:r=20:d=0.4",
            "-pix_fmt",
            "yuv420p",
            str(source),
        ],
        check=True,
    )
    captioned = Canvas(64, 32).video(
        str(source),
        (0, 0),
        64,
        32,
        captions=[
            {
                "text": "cue",
                "start": 0.1,
                "end": 0.2,
                "size": 12,
                "font": "assets/fonts/Roboto-Medium.ttf",
            }
        ],
    )
    deck = (
        Deck().slide(Canvas(64, 32), duration=0.2).slide(captioned, duration=0.4, transition=Cut())
    )
    outputs = []
    for workers in (1, 2):
        result = deck.export_image_sequence(
            tmp_path / f"caption-{workers}",
            options=ImageSequenceOptions(
                fps=10, workers=workers, motion_blur=MotionBlur(samples=2, shutter_angle=360)
            ),
        )
        frames = []
        for path in sorted(Path(result.output_directory).glob("*.png")):
            with Image.open(path) as frame:
                frames.append(frame.tobytes())
        outputs.append(frames)
        assert frames[2] != frames[3]  # Cue begins inside the exposure centered at .3.
        with Image.open(Path(result.output_directory) / "000003.png") as exposure:
            assert exposure.getchannel("R").getextrema()[1] == 128
    assert outputs[0] == outputs[1]
