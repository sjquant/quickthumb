"""Frame indices must not depend on ffprobe side-data formatting or seek history."""

import shutil
import subprocess
from types import SimpleNamespace

import pytest
from PIL import Image
from quickthumb._video import VideoDecoder, _probe_frame_times, probe_video


def test_frame_timestamp_csv_keeps_the_first_sei_frame(monkeypatch):
    output = "0.000000,H.264 User Data Unregistered SEI message\n\n0.100000\n0.200000\n"
    monkeypatch.setattr(
        subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout=output, returncode=0)
    )
    assert _probe_frame_times("ffprobe", "clip.mp4") == (0.0, 0.1, 0.2)


def test_frame_timestamp_csv_rejects_invalid_or_decreasing_values(monkeypatch):
    output = "N/A\nnan\n0.000000,side data\n0.200000\n0.1\ninf\n0.300000\n"
    monkeypatch.setattr(
        subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout=output, returncode=0)
    )
    assert _probe_frame_times("ffprobe", "clip.mp4") == (0.0, 0.2, 0.3)


@pytest.mark.skipif(
    not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="ffmpeg/ffprobe not installed"
)
def test_real_h264_decode_is_independent_of_seek_history(tmp_path):
    source = tmp_path / "clip.mp4"
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
    info = probe_video(str(source))
    assert info.frame_times == pytest.approx((0.0, 0.1, 0.2, 0.3, 0.4, 0.5))
    final_frames = []
    for times in ((0, 0.1, 0.2, 0.3, 0.4, 0.51875, 0.6), (0, 0.6), (0.6,), (0.5, 0, 0.6)):
        decoder = VideoDecoder(str(source), info)
        try:
            frames = [decoder.frame_at(time) for time in times]
            final_frames.append(frames[-1].tobytes())
        finally:
            decoder.close()
    assert len(set(final_frames)) == 1
