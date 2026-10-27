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


def test_exposure_preserves_red_in_transparent_motion_trails(tmp_path):
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
            fps=4, hold=0.25, motion_blur=MotionBlur(samples=2, shutter_angle=360)
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
