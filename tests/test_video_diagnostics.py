"""Behavioral specifications for the time-aware video diagnostics."""

import shutil
import subprocess

import pytest
from quickthumb import Canvas
from quickthumb._diagnostic_rules import (
    MAX_CAPTION_COLUMNS_PER_SECOND,
    MAX_NATURAL_CLIP_SPEED,
    MIN_CAPTION_SECONDS,
    MIN_NATURAL_CLIP_SPEED,
)

HAS_FFMPEG = shutil.which("ffmpeg") is not None
CLIP_SECONDS = 4.0


@pytest.fixture()
def source_video(tmp_path):
    """Given a four-second clip, long enough to time cues inside."""
    output = tmp_path / "source.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"color=c=red:s=64x32:r=10:d={CLIP_SECONDS}",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ],
        check=True,
    )
    return output


def clip_canvas(source, captions=None, **options):
    """Place one clip that fills its scene at its own rate unless told otherwise."""
    defaults = {
        "position": (0, 0),
        "width": 64,
        "height": 32,
        "trim_start": 0.0,
        "trim_end": CLIP_SECONDS,
        "duration": CLIP_SECONDS,
    }
    return Canvas(64, 32).video(str(source), captions=captions or [], **{**defaults, **options})


def caption(text, start, end):
    """Build one caption cue."""
    return {"text": text, "start": start, "end": end, "size": 8}


def findings_for(canvas, code):
    """Return the findings of one code raised by a canvas."""
    return [finding for finding in canvas.diagnose() if finding.code == code]


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg is required")
class TestCaptionReadingTime:
    """A cue nobody can read in time is a defect the settled frame cannot show."""

    def test_should_report_a_cue_that_flashes_past(self, source_video):
        """Given a very short cue, when diagnosed, then it is reported as too brief."""
        # Given: a caption held for well under the minimum
        canvas = clip_canvas(source_video, captions=[caption("flash", 0.2, 0.5)])

        # When: the composition is diagnosed
        findings = findings_for(canvas, "caption-reading-time")

        # Then: the message names the shortfall and the minimum it fell under
        assert len(findings) == 1
        assert "too brief" in findings[0].message
        assert f"{MIN_CAPTION_SECONDS:.2f}s minimum" in findings[0].message
        assert f"at least {MIN_CAPTION_SECONDS:.2f}s" in findings[0].suggestion

    def test_should_report_a_cue_that_reads_too_fast(self, source_video):
        """Given a long cue in a short window, when diagnosed, then the rate is reported."""
        # Given: forty narrow columns given one second, twice the readable rate
        canvas = clip_canvas(source_video, captions=[caption("x" * 40, 1.0, 2.0)])

        # When: the composition is diagnosed
        findings = findings_for(canvas, "caption-reading-time")

        # Then: the message states the rate that fired, not a friendlier number
        assert len(findings) == 1
        assert "too fast" in findings[0].message
        assert "40 columns of text in 1.00s" in findings[0].message
        assert findings[0].measured["columns_per_second"] == pytest.approx(40.0)

    def test_should_suggest_a_hold_long_enough_for_the_text(self, source_video):
        """Given an overlong cue, when diagnosed, then the suggested hold fits its length."""
        # Given: sixty columns, which need three seconds at the readable rate
        canvas = clip_canvas(source_video, captions=[caption("x" * 60, 0.5, 1.5)])

        # When: the composition is diagnosed
        findings = findings_for(canvas, "caption-reading-time")

        # Then: the suggestion is derived from the text, not a flat minimum
        assert "at least 3.00s" in findings[0].suggestion

    def test_should_charge_a_wide_script_for_the_room_it_takes(self, source_video):
        """Given a dense Korean cue, when diagnosed, then it is not judged as Latin."""
        # Given: the same window given a Korean line and a Latin line of equal length
        korean = "정확한 순간에 사라집니다"
        dense = clip_canvas(source_video, captions=[caption(korean, 1.0, 2.0)])
        sparse = clip_canvas(source_video, captions=[caption("x" * len(korean), 1.0, 2.0)])

        # When: both are diagnosed
        # Then: the wide script is charged for the reading it actually demands
        assert findings_for(dense, "caption-reading-time") != []
        assert findings_for(sparse, "caption-reading-time") == []

    def test_should_measure_the_time_a_cue_is_really_on_screen(self, source_video):
        """Given a cue running past its clip, when diagnosed, then the visible time counts."""
        # Given: a cue declaring two seconds but whose clip ends half a second in
        canvas = clip_canvas(
            source_video,
            trim_end=2.0,
            duration=2.0,
            captions=[caption("trailing", 1.5, 3.5)],
        )

        # When: the composition is diagnosed
        findings = findings_for(canvas, "caption-reading-time")

        # Then: it is judged on the half second it is actually seen
        assert len(findings) == 1
        assert findings[0].measured["caption_duration"] == pytest.approx(0.5)

    def test_should_attribute_each_finding_to_its_own_cue(self, source_video):
        """Given several cues, when diagnosed, then each finding names the one at fault."""
        # Given: a readable cue between two unreadable ones
        canvas = clip_canvas(
            source_video,
            captions=[
                caption("flash", 0.1, 0.3),
                caption("comfortable line", 1.0, 3.0),
                caption("y" * 40, 3.2, 3.7),
            ],
        )

        # When: the composition is diagnosed
        findings = findings_for(canvas, "caption-reading-time")

        # Then: only the offending cues report, each under its own index
        assert [finding.measured["caption_index"] for finding in findings] == [0, 2]
        assert "caption 0" in findings[0].message
        assert "caption 2" in findings[1].message

    def test_should_call_a_cue_that_is_both_short_and_dense_too_brief(self, source_video):
        """Given a cue failing both ways, when diagnosed, then the shorter fault is named."""
        # Given: forty columns held for a fifth of a second
        canvas = clip_canvas(source_video, captions=[caption("x" * 40, 0.1, 0.3)])

        # When: the composition is diagnosed
        findings = findings_for(canvas, "caption-reading-time")

        # Then: one finding is raised, and it leads with the time on screen
        assert len(findings) == 1
        assert "too brief" in findings[0].message

    def test_should_stay_quiet_for_a_cue_with_room_to_breathe(self, source_video):
        """Given a comfortable cue, when diagnosed, then nothing is reported."""
        # Given: sixteen columns held for two seconds
        canvas = clip_canvas(source_video, captions=[caption("comfortable line", 1.0, 3.0)])

        # When / Then: a readable cue is not second-guessed
        assert findings_for(canvas, "caption-reading-time") == []

    def test_should_accept_a_cue_sitting_exactly_on_the_documented_limits(self, source_video):
        """Given a cue at both thresholds, when diagnosed, then it is allowed through."""
        # Given: the documented limits, written out so moving one is a visible change
        assert (MIN_CAPTION_SECONDS, MAX_CAPTION_COLUMNS_PER_SECOND) == (0.8, 20.0)

        # Given: the shortest allowed hold, filled to exactly the readable rate
        canvas = clip_canvas(source_video, captions=[caption("x" * 16, 1.0, 1.8)])

        # When / Then: the boundary itself is not a defect
        assert findings_for(canvas, "caption-reading-time") == []

    def test_should_report_a_cue_just_past_each_limit(self, source_video):
        """Given cues a hair outside the limits, when diagnosed, then both report."""
        # Given: one cue held fractionally too briefly, one packed fractionally too densely
        brief = clip_canvas(source_video, captions=[caption("x" * 8, 1.0, 1.79)])
        dense = clip_canvas(source_video, captions=[caption("x" * 17, 1.0, 1.8)])

        # When / Then: the thresholds bite immediately outside the range
        assert findings_for(brief, "caption-reading-time") != []
        assert findings_for(dense, "caption-reading-time") != []


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg is required")
class TestClipStretch:
    """Footage played far from its own rate renders cleanly and looks wrong."""

    def test_should_report_a_clip_crawling_through_its_scene(self, source_video):
        """Given a heavily slowed clip, when diagnosed, then the stretch is reported."""
        # Given: a clip playing at a third of its rate
        canvas = clip_canvas(source_video, speed=1 / 3, duration=CLIP_SECONDS)

        # When: the composition is diagnosed
        findings = findings_for(canvas, "clip-stretch")

        # Then: the message and repair both describe slowing down
        assert len(findings) == 1
        assert "crawls" in findings[0].message
        assert "longer window" in findings[0].suggestion
        assert "shorten the scene" in findings[0].suggestion

    def test_should_report_a_clip_racing_through_its_scene(self, source_video):
        """Given a heavily sped-up clip, when diagnosed, then the repair is inverted."""
        # Given: a clip playing at three times its rate
        canvas = clip_canvas(source_video, speed=3.0, duration=1.0)

        # When: the composition is diagnosed
        findings = findings_for(canvas, "clip-stretch")

        # Then: a racing clip is told to trim shorter and lengthen, not the reverse
        assert len(findings) == 1
        assert "races" in findings[0].message
        assert "shorter window" in findings[0].suggestion
        assert "lengthen the scene" in findings[0].suggestion

    def test_should_accept_a_clip_played_near_its_own_rate(self, source_video):
        """Given a mild adjustment, when diagnosed, then it is left alone."""
        # Given: a clip slowed by a quarter, as fitting a scene often needs
        canvas = clip_canvas(source_video, speed=0.75, duration=CLIP_SECONDS)

        # When / Then: ordinary fitting is not treated as a defect
        assert findings_for(canvas, "clip-stretch") == []

    def test_should_accept_a_clip_sitting_exactly_on_the_documented_limits(self, source_video):
        """Given clips at both thresholds, when diagnosed, then neither is reported."""
        # Given: the documented limits, written out so moving one is a visible change
        assert (MIN_NATURAL_CLIP_SPEED, MAX_NATURAL_CLIP_SPEED) == (0.5, 2.0)

        # Given: clips at the slowest and fastest accepted rates
        slowest = clip_canvas(source_video, speed=0.5, duration=CLIP_SECONDS)
        fastest = clip_canvas(source_video, speed=2.0, duration=1.0)

        # When / Then: the boundary itself is not a defect
        assert findings_for(slowest, "clip-stretch") == []
        assert findings_for(fastest, "clip-stretch") == []

    def test_should_report_a_clip_just_past_each_limit(self, source_video):
        """Given clips a hair outside the limits, when diagnosed, then both report."""
        # Given: clips fractionally slower and faster than the accepted range
        slower = clip_canvas(source_video, speed=0.49, duration=1.0)
        faster = clip_canvas(source_video, speed=2.01, duration=1.0)

        # When / Then: the thresholds bite immediately outside the range
        assert findings_for(slower, "clip-stretch") != []
        assert findings_for(faster, "clip-stretch") != []


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg is required")
def test_should_close_its_decoders_rather_than_leave_them_running(source_video):
    """Given a diagnosed clip, when it returns, then no decoder is left open."""
    # Given: a composition carrying footage
    canvas = clip_canvas(source_video)

    # When: it is diagnosed
    canvas.diagnose()

    # Then: diagnosing has not stranded a decoder process behind it
    assert list(canvas._ctx.video_decoder_cache) == []
