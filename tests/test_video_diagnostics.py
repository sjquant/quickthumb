"""Behavioral specifications for the time-aware video diagnostics."""

import shutil
import subprocess
from typing import Any

import pytest
from quickthumb import Canvas
from quickthumb._diagnostic_rules import (
    MAX_CAPTION_COLUMNS_PER_SECOND,
    MAX_NATURAL_CLIP_SPEED,
    MIN_CAPTION_SECONDS,
    MIN_NATURAL_CLIP_SPEED,
)
from quickthumb._video import VideoDecoder

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
    defaults: dict[str, Any] = {
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
        assert "0.80s minimum" in findings[0].message
        assert "at least 0.80s" in findings[0].suggestion

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

    def test_should_publish_what_it_measured_for_an_agent_to_act_on(self, source_video):
        """Given a finding, when inspected, then its payload carries the whole measurement."""
        # Given: forty columns crammed into one second
        canvas = clip_canvas(source_video, captions=[caption("x" * 40, 1.0, 2.0)])

        # When: the finding's measured payload is read
        payload = findings_for(canvas, "caption-reading-time")[0].measured

        # Then: every value an agent needs to repair the cue is present
        assert findings_for(canvas, "caption-reading-time")[0].severity == "warning"
        assert payload == {
            "caption_index": 0,
            "caption_text": "x" * 40,
            "caption_duration": pytest.approx(1.0),
            "declared_duration": pytest.approx(1.0),
            "columns": 40,
            "columns_per_second": pytest.approx(40.0),
            "minimum_duration": 0.8,
            "maximum_columns_per_second": 20.0,
        }

    def test_should_not_charge_for_marks_that_render_into_their_neighbour(self, source_video):
        """Given joiners and accents, when measured, then only the visible glyphs count."""
        # Given: one cue of plain letters and one where every letter carries an accent
        plain = clip_canvas(source_video, captions=[caption("x" * 21, 1.0, 2.0)])
        accented = clip_canvas(source_video, captions=[caption("e\u0301" * 21, 1.0, 2.0)])

        # When / Then: the combining accents cost nothing, so both read the same
        assert findings_for(plain, "caption-reading-time") != []
        assert (
            findings_for(accented, "caption-reading-time")[0].measured["columns"]
            == findings_for(plain, "caption-reading-time")[0].measured["columns"]
        )

    def test_should_not_charge_for_joiners_between_glyphs(self, source_video):
        """Given zero-width joiners, when measured, then only the joined glyphs count."""
        # Given: fifteen letters, each followed by a joiner that renders nothing
        canvas = clip_canvas(source_video, captions=[caption("a\u200d" * 15, 1.0, 2.0)])

        # When / Then: fifteen columns is a readable rate; thirty would not be
        assert findings_for(canvas, "caption-reading-time") == []

    def test_should_not_charge_for_padding_around_the_text(self, source_video):
        """Given a padded cue, when measured, then the surrounding spaces are ignored."""
        # Given: fifteen letters inside ten spaces of padding
        canvas = clip_canvas(
            source_video, captions=[caption("     " + "x" * 15 + "     ", 1.0, 1.9)]
        )

        # When / Then: the padding is not text anybody has to read
        assert findings_for(canvas, "caption-reading-time") == []

    def test_should_charge_a_fullwidth_form_like_the_wide_script_it_is(self, source_video):
        """Given fullwidth Latin, when measured, then it costs twice its halfwidth twin."""
        # Given: the same eleven letters, once halfwidth and once fullwidth
        halfwidth = clip_canvas(source_video, captions=[caption("A" * 11, 1.0, 2.0)])
        fullwidth = clip_canvas(source_video, captions=[caption("\uff21" * 11, 1.0, 2.0)])

        # When / Then: only the fullwidth line is dense enough to report
        assert findings_for(halfwidth, "caption-reading-time") == []
        assert findings_for(fullwidth, "caption-reading-time") != []

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
        canvas = clip_canvas(source_video, speed=1 / 3)

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
        canvas = clip_canvas(source_video, speed=3.0, duration=CLIP_SECONDS / 3)

        # When: the composition is diagnosed
        findings = findings_for(canvas, "clip-stretch")

        # Then: a racing clip is told to trim shorter and lengthen, not the reverse
        assert len(findings) == 1
        assert "races" in findings[0].message
        assert "shorter window" in findings[0].suggestion
        assert "lengthen the scene" in findings[0].suggestion

    def test_should_publish_the_speed_and_window_it_judged(self, source_video):
        """Given a finding, when inspected, then its payload names the clip's timing."""
        # Given: a clip crawling through its scene
        canvas = clip_canvas(source_video, speed=1 / 3)

        # When: the finding's measured payload is read
        payload = findings_for(canvas, "clip-stretch")[0].measured

        # Then: the speed, the window it came from, and the limits are all present
        assert findings_for(canvas, "clip-stretch")[0].severity == "warning"
        assert payload == {
            "speed": pytest.approx(1 / 3),
            "trim_start": 0.0,
            "trim_end": CLIP_SECONDS,
            "duration": CLIP_SECONDS,
            "minimum_speed": 0.5,
            "maximum_speed": 2.0,
        }

    def test_should_accept_a_clip_played_near_its_own_rate(self, source_video):
        """Given a mild adjustment, when diagnosed, then it is left alone."""
        # Given: a clip slowed by a quarter, as fitting a scene often needs
        canvas = clip_canvas(source_video, speed=0.75)

        # When / Then: ordinary fitting is not treated as a defect
        assert findings_for(canvas, "clip-stretch") == []

    def test_should_accept_a_clip_sitting_exactly_on_the_documented_limits(self, source_video):
        """Given clips at both thresholds, when diagnosed, then neither is reported."""
        # Given: the documented limits, written out so moving one is a visible change
        assert (MIN_NATURAL_CLIP_SPEED, MAX_NATURAL_CLIP_SPEED) == (0.5, 2.0)

        # Given: clips at the slowest and fastest accepted rates
        slowest = clip_canvas(source_video, speed=0.5)
        fastest = clip_canvas(source_video, speed=2.0, duration=CLIP_SECONDS / 2)

        # When / Then: the boundary itself is not a defect
        assert findings_for(slowest, "clip-stretch") == []
        assert findings_for(fastest, "clip-stretch") == []

    def test_should_report_a_clip_just_past_each_limit(self, source_video):
        """Given clips a hair outside the limits, when diagnosed, then both report."""
        # Given: clips fractionally slower and faster than the accepted range
        slower = clip_canvas(source_video, speed=0.49)
        faster = clip_canvas(source_video, speed=2.01, duration=CLIP_SECONDS / 3)

        # When / Then: the thresholds bite immediately outside the range
        assert findings_for(slower, "clip-stretch") != []
        assert findings_for(faster, "clip-stretch") != []


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg is required")
def test_should_close_the_decoders_it_opens(source_video, monkeypatch):
    """Given a diagnosed clip, when it returns, then its decoder process is gone."""
    # Given: a recording decoder, so the ones diagnose opens can be inspected after
    opened = []

    class RecordingDecoder(VideoDecoder):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            opened.append(self)

    monkeypatch.setattr("quickthumb._video.VideoDecoder", RecordingDecoder)
    canvas = clip_canvas(source_video)

    # When: the composition is diagnosed
    canvas.diagnose()

    # Then: every ffmpeg child it started was terminated, not merely dropped
    assert opened, "diagnosing a clip should open a decoder for it"
    assert all(decoder._process is None for decoder in opened)
