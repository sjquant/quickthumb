"""Behavioral specifications for the time-aware video diagnostics."""

import shutil

import pytest
from quickthumb import Canvas

HAS_FFMPEG = shutil.which("ffmpeg") is not None
SOURCE = "assets/video/ordinary-coffee.mp4"


def clip_canvas(captions=None, **options):
    """Place one clip that fills its scene at its own rate unless told otherwise."""
    defaults = {
        "position": (0, 0),
        "width": 640,
        "height": 360,
        "fit": "cover",
        "trim_start": 0.0,
        "trim_end": 6.0,
        "duration": 6.0,
    }
    return Canvas(640, 360).video(SOURCE, captions=captions or [], **{**defaults, **options})


def caption(text, start, end):
    """Build one caption cue."""
    return {"text": text, "start": start, "end": end, "size": 20}


def codes(canvas, code):
    """Return the findings of one code raised by a canvas."""
    return [finding for finding in canvas.diagnose() if finding.code == code]


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg is required")
class TestCaptionReadingTime:
    """A cue nobody can read in time is a defect the settled frame cannot show."""

    def test_should_report_a_cue_that_flashes_past(self):
        """Given a very short cue, when diagnosed, then it is reported as too brief."""
        # Given: a caption held for less than a third of a second
        canvas = clip_canvas(captions=[caption("flash", 0.2, 0.5)])

        # When: the composition is diagnosed
        findings = codes(canvas, "caption-reading-time")

        # Then: the finding names the shortfall and how long it needs
        assert len(findings) == 1
        assert "too brief" in findings[0].message
        assert findings[0].measured["caption_duration"] == pytest.approx(0.3)
        assert findings[0].measured["minimum_duration"] > 0.3
        assert "hold" in findings[0].suggestion

    def test_should_report_a_cue_that_reads_too_fast(self):
        """Given a long cue in a short window, when diagnosed, then the rate is reported."""
        # Given: fifty characters given one second
        text = "a very long caption line that races past the viewer"
        canvas = clip_canvas(captions=[caption(text, 1.0, 2.0)])

        # When: the composition is diagnosed
        findings = codes(canvas, "caption-reading-time")

        # Then: the rate is measured and a longer hold is suggested
        assert len(findings) == 1
        assert findings[0].measured["columns_per_second"] == pytest.approx(len(text), abs=0.5)
        assert "at least" in findings[0].suggestion

    def test_should_stay_quiet_for_a_cue_with_room_to_breathe(self):
        """Given a comfortable cue, when diagnosed, then nothing is reported."""
        # Given: sixteen columns held for three seconds
        canvas = clip_canvas(captions=[caption("comfortable line", 3.0, 6.0)])

        # When / Then: a readable cue is not second-guessed
        assert codes(canvas, "caption-reading-time") == []

    def test_should_charge_a_wide_script_for_the_room_it_takes(self):
        """Given a dense Korean cue, when diagnosed, then it is not judged as Latin."""
        # Given: the same window given a Korean line and a Latin line of equal length
        korean = "정확한 순간에 사라집니다"
        latin = "x" * len(korean)
        dense = clip_canvas(captions=[caption(korean, 1.0, 2.0)])
        sparse = clip_canvas(captions=[caption(latin, 1.0, 2.0)])

        # When: both are diagnosed
        # Then: the wide script is charged for the reading it actually demands
        assert codes(dense, "caption-reading-time") != []
        assert codes(sparse, "caption-reading-time") == []


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg is required")
class TestClipStretch:
    """Footage stretched to fill a scene renders cleanly and looks wrong."""

    def test_should_report_a_clip_crawling_to_fill_its_scene(self):
        """Given a short clip in a long scene, when diagnosed, then the stretch is reported."""
        # Given: two seconds of source asked to cover six
        canvas = clip_canvas(trim_end=2.0, duration=6.0, speed=2.0 / 6.0)

        # When: the composition is diagnosed
        findings = codes(canvas, "clip-stretch")

        # Then: the rate is named along with the way out
        assert len(findings) == 1
        assert "crawls" in findings[0].message
        assert findings[0].measured["speed"] == pytest.approx(1 / 3)
        assert "shorten the scene" in findings[0].suggestion

    def test_should_report_a_clip_racing_through_its_scene(self):
        """Given a heavily sped-up clip, when diagnosed, then that is reported too."""
        # Given: a clip running at three times its own rate
        canvas = clip_canvas(speed=3.0, duration=2.0)

        # When: the composition is diagnosed
        findings = codes(canvas, "clip-stretch")

        # Then: the opposite failure is described in its own terms
        assert len(findings) == 1
        assert "races" in findings[0].message

    def test_should_accept_a_clip_played_near_its_own_rate(self):
        """Given a mild adjustment, when diagnosed, then it is left alone."""
        # Given: a clip slowed by a little under a third, as a scene often needs
        canvas = clip_canvas(trim_end=4.5, duration=6.0, speed=0.75)

        # When / Then: ordinary fitting is not treated as a defect
        assert codes(canvas, "clip-stretch") == []
