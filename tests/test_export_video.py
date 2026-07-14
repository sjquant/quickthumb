"""Tests for animated GIF/MP4/WebM export (Canvas/Deck .to_gif/.to_mp4/.to_webm and render)."""

import math
import shutil
import struct
import subprocess
import wave
from io import BytesIO

import pytest
from PIL import Image
from quickthumb import (
    Appear,
    AudioTrack,
    Blinds,
    Box,
    Canvas,
    Checkerboard,
    Circle,
    Deck,
    Diamond,
    Dissolve,
    Fade,
    Wheel,
    Wipe,
)
from quickthumb import transitions as tr
from quickthumb.errors import RenderingError, ValidationError

RED = (255, 45, 85)
BLUE = (17, 49, 170)
GREEN = (34, 170, 85)

HAS_FFMPEG = shutil.which("ffmpeg") is not None
HAS_FFPROBE = shutil.which("ffprobe") is not None


def gif_frames(data: bytes) -> list[tuple[Image.Image, int]]:
    """Decode a GIF into (RGB frame, duration ms) pairs."""
    image = Image.open(BytesIO(data))
    frames = []
    for index in range(image.n_frames):
        image.seek(index)
        frames.append((image.convert("RGB"), image.info.get("duration", 0)))
    return frames


def total_ms(frames: list[tuple[Image.Image, int]]) -> int:
    """Sum of all frame durations in milliseconds."""
    return sum(duration for _, duration in frames)


def close_to(color: tuple, expected: tuple, tolerance: int = 24) -> bool:
    """True when two RGB colors match within a GIF-quantization tolerance."""
    return all(abs(a - b) <= tolerance for a, b in zip(color, expected, strict=True))


def red_box_slide() -> Canvas:
    """A blue slide with a red shape that fades in (used across tests)."""
    return (
        Canvas(160, 90)
        .background(color="#1131AA")
        .shape("rectangle", (40, 20), 80, 50, "#FF2D55", animation=Fade(duration=0.5))
    )


def tone_wav(path, seconds: float) -> str:
    """Write a mono 16-bit 440Hz sine WAV used as a soundtrack fixture."""
    rate = 44100
    frames = b"".join(
        struct.pack("<h", int(20000 * math.sin(2 * math.pi * 440 * i / rate)))
        for i in range(int(rate * seconds))
    )
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(frames)
    return str(path)


def decoded_audio(data: bytes, path) -> list[int]:
    """Decode a video's audio track to 8kHz mono PCM samples via ffmpeg."""
    path.write_bytes(data)
    pcm = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a", "-f", "s16le",
         "-ar", "8000", "-ac", "1", "-"],
        check=True,
        capture_output=True,
    ).stdout  # fmt: skip
    return list(struct.unpack(f"<{len(pcm) // 2}h", pcm))


class TestCanvasGif:
    """Test suite for Canvas-level animated GIF export"""

    def test_should_render_static_canvas_as_single_frame(self):
        """A canvas without animations exports as a one-frame GIF held for `hold`"""
        # given
        canvas = Canvas(120, 60).background(color="#1131AA")

        # when
        frames = gif_frames(canvas.to_gif(fps=10, hold=2.0))

        # then
        assert len(frames) == 1
        assert frames[0][0].size == (120, 60)
        assert frames[0][1] == 2000
        assert close_to(frames[0][0].getpixel((60, 30)), BLUE)

    def test_should_play_entrance_animation_then_hold(self):
        """A fading layer is absent at the start, partial midway, and settled at the end"""
        # given
        canvas = red_box_slide()

        # when
        frames = gif_frames(canvas.to_gif(fps=10, hold=1.0))

        # then
        first, last = frames[0][0], frames[-1][0]
        assert close_to(first.getpixel((80, 45)), BLUE)
        assert close_to(last.getpixel((80, 45)), RED)
        partial = [
            frame.getpixel((80, 45))
            for frame, _ in frames
            if not close_to(frame.getpixel((80, 45)), BLUE)
            and not close_to(frame.getpixel((80, 45)), RED)
        ]
        assert partial, "expected at least one partially faded frame"
        assert total_ms(frames) == pytest.approx(1500, abs=50)

    def test_should_run_on_click_effects_sequentially(self):
        """`on_click` effects auto-play one after another, so runtime adds up"""
        # given
        first = (
            Canvas(160, 90)
            .background(color="#1131AA")
            .shape("rectangle", (10, 10), 40, 30, "#FF2D55", animation=Fade(duration=1.0))
            .shape("rectangle", (60, 10), 40, 30, "#22AA55", animation=Fade(duration=1.0))
        )
        second = (
            Canvas(160, 90)
            .background(color="#1131AA")
            .shape("rectangle", (10, 10), 40, 30, "#FF2D55", animation=Fade(duration=1.0))
            .shape(
                "rectangle",
                (60, 10),
                40,
                30,
                "#22AA55",
                animation=Fade(duration=1.0, trigger="with_previous"),
            )
        )

        # when
        sequential_ms = total_ms(gif_frames(first.to_gif(fps=10, hold=0.5)))
        concurrent_ms = total_ms(gif_frames(second.to_gif(fps=10, hold=0.5)))

        # then
        assert sequential_ms == pytest.approx(2500, abs=100)
        assert concurrent_ms == pytest.approx(1500, abs=100)

    def test_should_delay_effect_start_by_its_delay(self):
        """An effect's delay extends the timeline before the layer appears"""
        # given
        canvas = (
            Canvas(160, 90)
            .background(color="#1131AA")
            .shape(
                "rectangle", (40, 20), 80, 50, "#FF2D55", animation=Fade(duration=0.5, delay=0.5)
            )
        )

        # when
        frames = gif_frames(canvas.to_gif(fps=10, hold=0.5))

        # then: the hidden delay period collapses into a long-held first frame
        assert total_ms(frames) == pytest.approx(1500, abs=100)
        assert close_to(frames[0][0].getpixel((80, 45)), BLUE)
        assert frames[0][1] >= 500

    def test_should_collapse_timeline_gaps_into_held_frames(self):
        """Idle spans between effect windows become single held shots, not fps frames"""
        # given: two 0.2s fades separated by long delays (2.6s of idle timeline)
        canvas = (
            Canvas(160, 90)
            .background(color="#1131AA")
            .shape(
                "rectangle", (10, 10), 40, 30, "#FF2D55", animation=Fade(duration=0.2, delay=1.3)
            )
            .shape(
                "rectangle", (60, 10), 40, 30, "#22AA55", animation=Fade(duration=0.2, delay=1.3)
            )
        )

        # when
        frames = gif_frames(canvas.to_gif(fps=20, hold=0.5))

        # then: the clock covers the full 3.5s, but only the 0.4s of actual
        # animation is sampled at fps -- the gaps are single held frames
        assert total_ms(frames) == pytest.approx(3500, abs=50)
        assert len(frames) <= 20  # naive fps sampling would need ~70
        assert any(duration >= 1000 for _, duration in frames)

    def test_should_show_settled_frame_even_with_zero_hold(self):
        """The fully settled composition appears even when the hold is zero"""
        # given
        canvas = (
            Canvas(160, 90)
            .background(color="#1131AA")
            .shape("rectangle", (40, 20), 80, 50, "#FF2D55", animation=Fade(duration=0.5))
        )

        # when
        frames = gif_frames(canvas.to_gif(fps=10, hold=0.0))

        # then: the last frame is the settled state, not a ~95%-reveal sample
        assert close_to(frames[-1][0].getpixel((80, 45)), RED)

    def test_should_keep_timing_exact_when_effect_boundaries_land_one_ulp_apart(self):
        """Float-noise effect boundaries (0.1+0.2 vs 0.3) don't distort the timeline"""
        # given: concurrent fades whose windows end/start one float ulp apart
        canvas = (
            Canvas(160, 90)
            .background(color="#1131AA")
            .shape(
                "rectangle", (10, 20), 60, 50, "#FF2D55", animation=Fade(duration=0.2, delay=0.1)
            )
            .shape(
                "rectangle",
                (90, 20),
                60,
                50,
                "#22AA55",
                animation=Fade(duration=0.2, delay=0.3, trigger="with_previous"),
            )
        )

        # when
        frames = gif_frames(canvas.to_gif(fps=20, hold=0.5))

        # then: the clock stays exact and both layers settle fully
        assert total_ms(frames) == pytest.approx(1000, abs=30)
        assert close_to(frames[-1][0].getpixel((40, 45)), RED)
        assert close_to(frames[-1][0].getpixel((120, 45)), GREEN)

    def test_should_keep_gif_clock_accurate_at_non_centisecond_fps(self):
        """GIF centisecond durations don't drift the clock at fps like 30"""
        # given: 2s of animation + 1s hold; 33.33ms frames don't fit centiseconds
        canvas = (
            Canvas(160, 90)
            .background(color="#1131AA")
            .shape("rectangle", (40, 20), 80, 50, "#FF2D55", animation=Fade(duration=2.0))
        )

        # when
        frames = gif_frames(canvas.to_gif(fps=30, hold=1.0))

        # then: per-frame rounding to 30ms would land near 2810ms
        assert total_ms(frames) == pytest.approx(3000, abs=20)

    def test_should_hide_layer_after_exit_animation(self):
        """An exit effect leaves the layer hidden in the settled frame"""
        # given
        canvas = (
            Canvas(160, 90)
            .background(color="#1131AA")
            .shape(
                "rectangle",
                (40, 20),
                80,
                50,
                "#FF2D55",
                animation=Fade(animate="exit", duration=0.5),
            )
        )

        # when
        frames = gif_frames(canvas.to_gif(fps=10, hold=0.5))

        # then
        assert close_to(frames[0][0].getpixel((80, 45)), RED)
        assert close_to(frames[-1][0].getpixel((80, 45)), BLUE)

    @pytest.mark.parametrize(
        "animation",
        [
            Appear(),
            Fade(),
            Wipe(direction="left"),
            Wipe(direction="right"),
            Wipe(direction="up"),
            Wipe(direction="down"),
            Box(direction="out"),
            Box(direction="in"),
            Blinds(orientation="vertical"),
            Blinds(orientation="horizontal"),
            Checkerboard(direction="down"),
            Checkerboard(direction="across"),
            Circle(),
            Diamond(),
            Dissolve(),
            Wheel(spokes=3),
        ],
        ids=lambda animation: "-".join(
            str(part)
            for part in (
                animation.effect,
                getattr(animation, "orientation", None),
                getattr(animation, "direction", None),
            )
            if part
        ),
    )
    def test_should_settle_every_effect_at_full_visibility(self, animation):
        """Every entrance effect starts hidden and ends fully revealed"""
        # given
        canvas = (
            Canvas(160, 90)
            .background(color="#1131AA")
            .shape("rectangle", (40, 20), 80, 50, "#FF2D55", animation=animation)
        )

        # when
        frames = gif_frames(canvas.to_gif(fps=10, hold=0.5))

        # then
        assert close_to(frames[-1][0].getpixel((80, 45)), RED)

    def test_should_animate_group_children_as_one_unit(self):
        """A group's animation drives all its children together"""
        # given
        canvas = (
            Canvas(160, 90)
            .background(color="#1131AA")
            .group(
                children=[
                    {
                        "type": "shape",
                        "shape": "rectangle",
                        "width": 40,
                        "height": 30,
                        "color": "#FF2D55",
                    },
                    {
                        "type": "shape",
                        "shape": "rectangle",
                        "width": 40,
                        "height": 30,
                        "color": "#22AA55",
                    },
                ],
                gap=10,
                position=(20, 10),
                animation=Fade(duration=0.5),
            )
        )

        # when
        frames = gif_frames(canvas.to_gif(fps=10, hold=0.5))

        # then: both children hidden at the start, both shown at the end
        first, last = frames[0][0], frames[-1][0]
        assert close_to(first.getpixel((30, 20)), BLUE)
        assert close_to(first.getpixel((30, 65)), BLUE)
        assert close_to(last.getpixel((30, 20)), RED)
        assert close_to(last.getpixel((30, 65)), GREEN)


class TestDeckGif:
    """Test suite for Deck-level animated GIF export with slide transitions"""

    def two_slide_deck(self, transition) -> Deck:
        """A blue slide then a green slide joined by the given transition."""
        first = Canvas(160, 90).background(color="#1131AA")
        second = Canvas(160, 90).background(color="#22AA55")
        return Deck(160, 90).slide(first).slide(second, transition=transition)

    def test_should_render_deck_render_dispatch_to_gif(self, tmp_path):
        """Deck.render writes a .gif file and returns its path"""
        # given
        deck = self.two_slide_deck(tr.Fade(duration=0.5))
        path = tmp_path / "deck.gif"

        # when
        written = deck.render(str(path))

        # then
        assert written == [str(path)]
        assert Image.open(path).n_frames > 1

    def test_should_cross_fade_between_slides(self):
        """A fade transition blends the outgoing and incoming slides"""
        # given
        deck = self.two_slide_deck(tr.Fade(duration=1.0))

        # when
        frames = gif_frames(deck.to_gif(fps=10, slide_duration=0.5))

        # then: first frame pure blue, last pure green, and some frame in between
        assert close_to(frames[0][0].getpixel((80, 45)), BLUE)
        assert close_to(frames[-1][0].getpixel((80, 45)), GREEN)
        blended = [
            frame.getpixel((80, 45))
            for frame, _ in frames
            if not close_to(frame.getpixel((80, 45)), BLUE, 40)
            and not close_to(frame.getpixel((80, 45)), GREEN, 40)
        ]
        assert blended, "expected at least one blended transition frame"

    def test_should_push_slides_across_the_frame(self):
        """A push-left transition shows both slides side by side midway"""
        # given
        deck = self.two_slide_deck(tr.Push(direction="left", duration=1.0))

        # when
        frames = gif_frames(deck.to_gif(fps=10, slide_duration=0.5))

        # then: some frame carries the old slide on the left, the new on the right
        split = [
            frame
            for frame, _ in frames
            if close_to(frame.getpixel((8, 45)), BLUE)
            and close_to(frame.getpixel((152, 45)), GREEN)
        ]
        assert split, "expected a mid-push frame showing both slides"

    def test_should_cut_directly_between_slides(self):
        """A cut transition produces no blended frames at all"""
        # given
        deck = self.two_slide_deck(tr.Cut())

        # when
        frames = gif_frames(deck.to_gif(fps=10, slide_duration=0.5))

        # then
        for frame, _ in frames:
            pixel = frame.getpixel((80, 45))
            assert close_to(pixel, BLUE) or close_to(pixel, GREEN)

    @pytest.mark.parametrize(
        "transition",
        [
            tr.Fade(duration=0.4),
            tr.Dissolve(duration=0.4),
            tr.Newsflash(duration=0.4),
            tr.Wedge(duration=0.4),
            tr.Circle(duration=0.4),
            tr.Diamond(duration=0.4),
            tr.Random(duration=0.4),
            tr.Wheel(duration=0.4, spokes=4),
            tr.Push(duration=0.4, direction="up"),
            tr.Push(duration=0.4, direction="down"),
            tr.Wipe(duration=0.4, direction="right"),
            tr.Wipe(duration=0.4, direction="up"),
            tr.Cover(duration=0.4, direction="down"),
            tr.Cover(duration=0.4, direction="left"),
            tr.Uncover(duration=0.4, direction="left"),
            tr.Uncover(duration=0.4, direction="down"),
            tr.Zoom(duration=0.4, direction="out"),
            tr.Zoom(duration=0.4, direction="in"),
            tr.Split(duration=0.4, orientation="vertical", direction="in"),
            tr.Split(duration=0.4, orientation="vertical", direction="out"),
            tr.Split(duration=0.4, orientation="horizontal", direction="in"),
            tr.Split(duration=0.4, orientation="horizontal", direction="out"),
            tr.Blinds(duration=0.4, orientation="horizontal"),
            tr.Blinds(duration=0.4, orientation="vertical"),
            tr.Checker(duration=0.4, orientation="vertical"),
            tr.Checker(duration=0.4, orientation="horizontal"),
            tr.Comb(duration=0.4, orientation="horizontal"),
            tr.Comb(duration=0.4, orientation="vertical"),
        ],
        ids=lambda transition: "-".join(
            str(part)
            for part in (
                transition.effect,
                getattr(transition, "orientation", None),
                getattr(transition, "direction", None),
            )
            if part
        ),
    )
    def test_should_land_every_transition_on_the_incoming_slide(self, transition):
        """Every transition effect ends with the incoming slide fully shown"""
        # given
        deck = self.two_slide_deck(transition)

        # when
        frames = gif_frames(deck.to_gif(fps=10, slide_duration=0.5))

        # then
        last = frames[-1][0]
        for probe in ((8, 8), (80, 45), (152, 82)):
            assert close_to(last.getpixel(probe), GREEN)

    def test_should_default_to_half_second_cross_fade_between_slides(self):
        """Slides without a transition fall back to the HTML default 0.5s fade"""
        # given
        deck = Deck(
            160,
            90,
            slides=[
                Canvas().background(color="#1131AA"),
                Canvas().background(color="#22AA55"),
            ],
        )

        # when
        frames = gif_frames(deck.to_gif(fps=10, slide_duration=1.0))

        # then: 1s hold + 0.5s fade + 1s hold
        assert total_ms(frames) == pytest.approx(2500, abs=100)

    def test_should_hold_slide_for_advance_after(self):
        """A transition's advance_after replaces the default slide hold"""
        # given
        deck = self.two_slide_deck(tr.Fade(duration=0.5, advance_after=2.0))

        # when
        frames = gif_frames(deck.to_gif(fps=10, slide_duration=0.5))

        # then: slide 1 holds 0.5s, then 0.5s fade + 2.0s advance_after hold
        assert total_ms(frames) == pytest.approx(3000, abs=100)

    def test_should_play_slide_zero_transition_from_the_matte(self):
        """An explicit transition on the first slide fades in from the matte color"""
        # given
        first = Canvas(160, 90).background(color="#22AA55")
        deck = Deck(160, 90).slide(first, transition=tr.Fade(duration=1.0))

        # when
        frames = gif_frames(deck.to_gif(fps=10, slide_duration=0.5, matte="#FFFFFF"))

        # then
        assert close_to(frames[0][0].getpixel((80, 45)), (255, 255, 255))
        assert close_to(frames[-1][0].getpixel((80, 45)), GREEN)

    def test_should_letterbox_mixed_size_slides(self):
        """Slides smaller than the first are scaled to fit and centered on the matte"""
        # given
        wide = Canvas(160, 90).background(color="#1131AA")
        square = Canvas(50, 50).background(color="#22AA55")
        deck = Deck(slides=[wide, square])

        # when
        frames = gif_frames(deck.to_gif(fps=10, slide_duration=0.5, matte="#000000"))

        # then: the last frame centers the square slide with matte pillarboxing
        last = frames[-1][0]
        assert last.size == (160, 90)
        assert close_to(last.getpixel((80, 45)), GREEN)
        assert close_to(last.getpixel((5, 45)), (0, 0, 0))
        assert close_to(last.getpixel((155, 45)), (0, 0, 0))

    def test_should_write_loop_count_into_the_gif(self):
        """The loop parameter lands in the GIF metadata (0 = forever)"""
        # given
        deck = self.two_slide_deck(tr.Fade(duration=0.5))

        # when
        forever = Image.open(BytesIO(deck.to_gif(fps=10, slide_duration=0.5)))
        thrice = Image.open(BytesIO(deck.to_gif(fps=10, slide_duration=0.5, loop=3)))

        # then
        assert forever.info.get("loop") == 0
        assert thrice.info.get("loop") == 3


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
class TestVideoEncoding:
    """Test suite for ffmpeg-backed MP4/WebM encoding"""

    def test_should_encode_deck_to_mp4_bytes(self):
        """Deck.to_mp4 returns a valid MP4 container"""
        # given
        deck = Deck(
            160,
            90,
            slides=[
                Canvas().background(color="#1131AA"),
                Canvas().background(color="#22AA55"),
            ],
        )

        # when
        data = deck.to_mp4(fps=12, slide_duration=0.5)

        # then
        assert data[4:8] == b"ftyp"

    def test_should_encode_deck_to_webm_bytes(self):
        """Deck.to_webm returns a valid WebM (EBML) container"""
        # given
        deck = Deck(160, 90, slides=[Canvas().background(color="#1131AA")])

        # when
        data = deck.to_webm(fps=12, slide_duration=0.5)

        # then
        assert data[:4] == b"\x1a\x45\xdf\xa3"

    def test_should_write_settled_frame_when_clock_lands_on_half_frame(self, tmp_path):
        """The settled frame is encoded even when its count lands on an exact .5 boundary"""
        # given: 0.75s of animation at 10fps puts the settled shot at 8.5 frames,
        # where round-half-even would emit zero frames for it
        canvas = (
            Canvas(160, 90)
            .background(color="#1131AA")
            .shape("rectangle", (40, 20), 80, 50, "#FF2D55", animation=Fade(duration=0.75))
        )
        path = tmp_path / "clip.mp4"
        path.write_bytes(canvas.to_mp4(fps=10, hold=0.0))

        # when
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            check=True,
            capture_output=True,
        ).stdout
        frame_count = len(raw) // (160 * 90 * 3)
        last = Image.frombytes("RGB", (160, 90), raw[-160 * 90 * 3 :])

        # then: 8 animation frames plus the settled frame, which shows full red
        assert frame_count == 9
        assert close_to(last.getpixel((80, 45)), RED)

    @pytest.mark.parametrize("container", ["mp4", "webm"])
    def test_should_loop_soundtrack_across_the_video(self, tmp_path, container):
        """A short soundtrack repeats to cover the whole video"""
        # given: a 0.5s tone under a 2s video
        canvas = Canvas(160, 90).background(color="#1131AA")
        tone = tone_wav(tmp_path / "tone.wav", 0.5)

        # when
        export = canvas.to_mp4 if container == "mp4" else canvas.to_webm
        data = export(fps=10, hold=2.0, soundtrack=AudioTrack(path=tone, volume=0.5, loop=True))
        samples = decoded_audio(data, tmp_path / f"clip.{container}")

        # then: the audio spans the video and the tone still plays at the end
        assert len(samples) / 8000 == pytest.approx(2.0, abs=0.15)
        assert max(abs(sample) for sample in samples[-2000:]) > 5000

    def test_should_pad_unlooped_soundtrack_with_silence(self, tmp_path):
        """loop_audio=False plays the track once without cutting the video short"""
        # given: a 0.5s tone under a 2s video, playing once
        canvas = Canvas(160, 90).background(color="#1131AA")
        tone = tone_wav(tmp_path / "tone.wav", 0.5)
        path = tmp_path / "clip.mp4"

        # when
        data = canvas.to_mp4(fps=10, hold=2.0, soundtrack=tone, loop_audio=False)
        samples = decoded_audio(data, path)

        # then: the audio tail is silence, not a repeated tone
        assert len(samples) / 8000 == pytest.approx(2.0, abs=0.15)
        assert max(abs(sample) for sample in samples[-2000:]) < 500

        # and the video keeps its full length (the short track must not trim it)
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v", "-f", "rawvideo",
             "-pix_fmt", "rgb24", "-"],
            check=True,
            capture_output=True,
        ).stdout  # fmt: skip
        assert len(raw) // (160 * 90 * 3) == 20

    def test_should_render_canvas_to_mp4_file(self, tmp_path):
        """Canvas.render dispatches .mp4 through the animation exporter"""
        # given
        canvas = red_box_slide()
        path = tmp_path / "clip.mp4"

        # when
        canvas.render(str(path))
        streams = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "stream=codec_type,codec_name",
                "-of",
                "csv=p=0",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout

        # then
        assert path.read_bytes()[4:8] == b"ftyp"
        assert "aac,audio" in streams

    def test_should_reap_ffmpeg_and_drop_output_when_a_slide_fails_mid_encode(self, tmp_path):
        """A slide failing to render mid-stream kills ffmpeg and removes the file"""

        # given: slide 2's custom layer raises while its frames are produced
        def boom(image):
            raise RuntimeError("boom")

        first = Canvas(160, 90).background(color="#1131AA")
        second = Canvas(160, 90).background(color="#22AA55").custom(boom)
        deck = Deck(160, 90, slides=[first, second])
        output_dir = tmp_path / "deck 'quoted'"
        output_dir.mkdir()
        output = output_dir / "deck.mp4"

        # when
        with pytest.raises(RenderingError, match="Custom layer callback failed"):
            deck.render(str(output))

        # then
        assert not output.exists()

    def test_should_handle_odd_dimensions(self):
        """Odd-sized canvases encode by dropping the last pixel row/column"""
        # given
        canvas = Canvas(161, 91).background(color="#1131AA")

        # when
        data = canvas.to_mp4(fps=12, hold=0.3)

        # then
        assert data[4:8] == b"ftyp"


@pytest.mark.skipif(not (HAS_FFMPEG and HAS_FFPROBE), reason="ffmpeg/ffprobe not installed")
class TestNarratedDeckMp4:
    """Black-box tests for static Deck MP4 narration export."""

    @pytest.mark.parametrize(
        ("container", "video_codec", "audio_codec", "with_soundtrack"),
        [
            ("mp4", "h264", "aac", True),
            ("webm", "vp9", "opus", True),
            ("webm", "vp9", "opus", False),
        ],
    )
    def test_should_mix_soundtrack_and_slide_narration_on_animated_render(
        self, tmp_path, container, video_codec, audio_codec, with_soundtrack
    ):
        """Deck.render keeps scheduled narration audible in MP4 and WebM output"""
        # given
        music = tone_wav(tmp_path / "music.wav", 0.1)
        voice = tone_wav(tmp_path / "voice.wav", 0.2)
        deck = (
            Deck(160, 90)
            .slide(
                Canvas().background(color="#1131AA"),
                transition=tr.Cut(advance_after=0.25),
                audio=voice,
            )
            .slide(
                Canvas().background(color="#22AA55"),
                transition=tr.Cut(advance_after=0.25),
                audio=voice,
            )
        )
        output = tmp_path / f"animated deck.{container}"

        # when
        soundtrack = AudioTrack(path=music, volume=0.2, loop=True) if with_soundtrack else None
        deck.render(str(output), soundtrack=soundtrack)
        streams = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "stream=codec_type,codec_name",
                "-of",
                "csv=p=0",
                str(output),
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        raw = subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-ss",
                "0.35",
                "-i",
                str(output),
                "-frames:v",
                "1",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-",
            ],
            check=True,
            capture_output=True,
        ).stdout

        # then
        assert f"{video_codec},video" in streams
        assert f"{audio_codec},audio" in streams
        assert Image.frombytes("RGB", (160, 90), raw).getpixel((80, 45)) == pytest.approx(
            GREEN, abs=24
        )
        assert (
            max(
                abs(sample) for sample in decoded_audio(output.read_bytes(), tmp_path / "audio.bin")
            )
            > 100
        )

    def test_should_keep_later_narration_when_the_soundtrack_does_not_loop(self, tmp_path):
        """A short non-looping music bed does not silence delayed slide narration"""
        # given
        music = tone_wav(tmp_path / "music.wav", 0.1)
        voice = tone_wav(tmp_path / "voice.wav", 0.2)
        deck = (
            Deck(160, 90)
            .slide(
                Canvas().background(color="#1131AA"),
                transition=tr.Cut(advance_after=0.3),
                audio=voice,
            )
            .slide(
                Canvas().background(color="#22AA55"),
                transition=tr.Cut(advance_after=0.3),
                audio=voice,
            )
        )
        output = tmp_path / "narrated.mp4"

        # when
        deck.render(str(output), soundtrack=AudioTrack(path=music, loop=False))
        samples = decoded_audio(output.read_bytes(), tmp_path / "decoded.pcm")

        # then
        assert max(abs(sample) for sample in samples[2600:3600]) > 100

    def test_should_trim_animated_narration_to_the_explicit_slide_duration(self, tmp_path):
        """Animated MP4 applies the same explicit narration duration contract as static MP4"""
        # given
        music = tone_wav(tmp_path / "music.wav", 0.1)
        voice = tone_wav(tmp_path / "voice.wav", 0.4)
        deck = (
            Deck(160, 90)
            .slide(
                Canvas().background(color="#1131AA"),
                transition=tr.Cut(advance_after=0.3),
                audio=voice,
                duration=0.1,
            )
            .slide(Canvas().background(color="#22AA55"), transition=tr.Cut(advance_after=0.3))
        )
        output = tmp_path / "trimmed.mp4"

        # when
        deck.render(str(output), soundtrack=AudioTrack(path=music, loop=False))
        samples = decoded_audio(output.read_bytes(), tmp_path / "trimmed.pcm")

        # then
        assert max(abs(sample) for sample in samples[1300:1900]) < 100

    def test_should_render_ordered_static_slides_with_aac_audio(self, tmp_path):
        """Deck MP4 joins explicit-audio and silent slides in their declared order"""
        # given
        audio = tone_wav(tmp_path / "voice 'quoted'.wav", 0.2)
        deck = (
            Deck(161, 91)
            .slide(Canvas().background(color="#1131AA"), audio=audio, duration=0.4)
            .slide(Canvas().background(color="#22AA55"), duration=0.4)
        )
        output = tmp_path / "deck.mp4"

        # when
        deck.render(str(output))
        streams = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "stream=codec_type,codec_name",
                "-of",
                "csv=p=0",
                str(output),
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        raw = subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-ss",
                "0.55",
                "-i",
                str(output),
                "-frames:v",
                "1",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-",
            ],
            check=True,
            capture_output=True,
        ).stdout

        # then
        assert "h264,video" in streams
        assert "aac,audio" in streams
        assert Image.frombytes("RGB", (160, 90), raw).getpixel((80, 45)) == pytest.approx(
            GREEN, abs=24
        )

    def test_should_infer_audio_duration_when_not_explicit(self, tmp_path):
        """Audio-only timing uses ffprobe's source duration instead of the default hold"""
        # given
        audio = tone_wav(tmp_path / "voice.wav", 0.3)
        deck = Deck(160, 90).slide(Canvas().background(color="#1131AA"), audio=audio)
        output = tmp_path / "deck.mp4"

        # when
        deck.render_mp4(str(output), default_duration=2.0)
        duration = float(
            subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=nw=1:nk=1",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
        )

        # then
        assert duration == pytest.approx(0.3, abs=0.12)

    def test_should_reject_non_numeric_slide_duration(self, tmp_path):
        """Malformed per-slide duration raises ValidationError before any output is created"""
        # given
        deck = Deck(160, 90).slide(Canvas().background(color="#1131AA"), duration="invalid")
        output = tmp_path / "deck.mp4"

        # when / then
        with pytest.raises(ValidationError, match="duration must be a finite"):
            deck.render_mp4(str(output))
        assert not output.exists()


class TestVideoErrors:
    """Test suite for animated-export validation and error paths"""

    def test_should_reject_missing_configured_media_tool(self, monkeypatch, tmp_path):
        """An invalid configured ffmpeg path raises the install-guidance RenderingError"""
        # given
        monkeypatch.setenv("QUICKTHUMB_FFMPEG", str(tmp_path / "missing-ffmpeg"))
        deck = Deck(160, 90).slide(Canvas().background(color="#1131AA"))

        # when / then
        with pytest.raises(RenderingError, match="requires both ffmpeg and ffprobe"):
            deck.render_mp4(str(tmp_path / "deck.mp4"))

    def test_should_reject_quality_for_animated_output(self, tmp_path):
        """The quality parameter has no meaning for GIF/MP4/WebM output"""
        # given
        deck = Deck(160, 90, slides=[Canvas().background(color="#1131AA")])

        # when / then
        with pytest.raises(RenderingError, match="Quality parameter"):
            deck.render(str(tmp_path / "deck.gif"), quality=80)

    def test_should_reject_format_override_for_animated_output(self, tmp_path):
        """The raster format override cannot apply to animated output"""
        # given
        deck = Deck(160, 90, slides=[Canvas().background(color="#1131AA")])

        # when / then
        with pytest.raises(RenderingError, match="format override"):
            deck.render(str(tmp_path / "deck.gif"), format="PNG")

    def test_should_reject_debug_render_for_animated_output(self, tmp_path):
        """Debug overlays only exist for still raster output"""
        # given
        canvas = Canvas(160, 90).background(color="#1131AA")

        # when / then
        with pytest.raises(RenderingError, match="Debug render"):
            canvas.render(str(tmp_path / "clip.gif"), debug=True)

    def test_should_reject_empty_deck(self, tmp_path):
        """A deck with no slides cannot render an animation"""
        # given
        deck = Deck(160, 90)

        # when / then
        with pytest.raises(RenderingError, match="no slides"):
            deck.render(str(tmp_path / "deck.gif"))

    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            ({"fps": 0}, "fps must be > 0"),
            ({"fps": 500}, "fps must be <= 100 for gif output"),
            ({"hold": -1.0}, "slide_duration must be >= 0"),
            ({"hold": math.inf}, "slide_duration must be finite"),
            ({"loop": -1}, "loop must be >= 0"),
            ({"matte": "not-a-color"}, "Invalid matte color"),
        ],
        ids=[
            "fps-zero",
            "fps-huge",
            "negative-hold",
            "infinite-hold",
            "negative-loop",
            "bad-matte",
        ],
    )
    def test_should_validate_export_knobs(self, kwargs, message):
        """Out-of-range export settings raise a quickthumb ValidationError"""
        # given
        canvas = Canvas(160, 90).background(color="#1131AA")

        # when / then
        with pytest.raises(ValidationError, match=message):
            canvas.to_gif(**kwargs)

    def test_should_reject_soundtrack_for_gif(self):
        """The public GIF API does not accept a soundtrack option"""
        # given
        canvas = Canvas(160, 90).background(color="#1131AA")

        # when / then
        with pytest.raises(TypeError, match="soundtrack"):
            canvas.to_gif(soundtrack="tone.wav")

    def test_should_reject_missing_soundtrack_file(self, tmp_path):
        """A nonexistent soundtrack fails before any frame is rendered"""
        # given
        canvas = Canvas(160, 90).background(color="#1131AA")

        # when / then
        with pytest.raises(ValidationError, match="Soundtrack file not found"):
            canvas.to_mp4(soundtrack=str(tmp_path / "missing.mp3"))

    def test_should_reject_animated_layers_under_backdrop_compositing(self):
        """Layers that must flatten with a blend/custom backdrop cannot animate"""
        # given: an animated shape below a custom layer (which needs the backdrop)
        canvas = (
            Canvas(160, 90)
            .background(color="#1131AA")
            .shape("rectangle", (40, 20), 80, 50, "#FF2D55", animation=Fade(duration=0.5))
            .custom(lambda image: None)
        )

        # when / then
        with pytest.raises(RenderingError, match="backdrop"):
            canvas.to_gif()

    def test_should_reject_animated_children_in_clipped_groups(self):
        """A clipped group cannot independently animate one of its children"""
        # given
        canvas = Canvas(160, 90).group(
            children=[
                {
                    "type": "shape",
                    "shape": "rectangle",
                    "width": 80,
                    "height": 50,
                    "color": "#FF2D55",
                    "animation": Fade(duration=0.5),
                }
            ],
            position=(40, 20),
            clip={"shape": "rectangle", "position": (0, 0), "width": 80, "height": 50},
        )

        # when / then
        with pytest.raises(RenderingError, match="clipped or masked group"):
            canvas.to_gif()

    def test_should_reject_single_pixel_video_dimensions(self):
        """MP4/WebM dimensions below 2 pixels fail before ffmpeg runs"""
        # given
        canvas = Canvas(1, 90).background(color="#1131AA")

        # when / then
        with pytest.raises(ValidationError, match="at least 2x2"):
            canvas.to_mp4()

    @pytest.mark.parametrize("wheel", [Wheel, tr.Wheel], ids=["animation", "transition"])
    def test_should_cap_wheel_spokes(self, wheel):
        """Wheel effects reject spoke counts that would make each frame excessively expensive"""
        # given / when / then
        with pytest.raises(ValidationError, match="less than or equal to 64"):
            wheel(spokes=65)

    def test_should_surface_missing_ffmpeg_with_install_hint(self, monkeypatch, tmp_path):
        """MP4 export without ffmpeg raises a clear, actionable error"""
        # given: an environment where ffmpeg cannot be found
        monkeypatch.delenv("QUICKTHUMB_FFMPEG", raising=False)
        monkeypatch.setenv("PATH", str(tmp_path))
        canvas = Canvas(160, 90).background(color="#1131AA")

        # when / then
        with pytest.raises(RenderingError, match="ffmpeg"):
            canvas.to_mp4(hold=0.2)

    def test_should_surface_ffmpeg_encode_failure(self, monkeypatch):
        """A failing ffmpeg process surfaces as a RenderingError, not a crash"""
        # given: an "ffmpeg" that exits nonzero without reading its input
        monkeypatch.setenv("QUICKTHUMB_FFMPEG", "false")
        canvas = Canvas(160, 90).background(color="#1131AA")

        # when / then
        with pytest.raises(RenderingError, match="ffmpeg failed"):
            canvas.to_mp4(hold=0.2)

    def test_should_leave_no_partial_file_when_encoding_fails(self, monkeypatch, tmp_path):
        """A failed video export preserves a pre-existing destination file"""
        # given: an "ffmpeg" that exits nonzero after creating the output
        fake = tmp_path / "fake-ffmpeg"
        fake.write_text('#!/bin/sh\nfor last; do :; done\ntouch "$last"\nexit 1\n')
        fake.chmod(0o755)
        monkeypatch.setenv("QUICKTHUMB_FFMPEG", str(fake))
        canvas = Canvas(160, 90).background(color="#1131AA")
        output = tmp_path / "clip.mp4"
        output.write_bytes(b"previous video")

        # when
        with pytest.raises(RenderingError, match="ffmpeg failed"):
            canvas.render(str(output))

        # then
        assert output.read_bytes() == b"previous video"

    def test_should_fail_before_encoding_when_an_asset_is_missing(self, tmp_path):
        """A missing image on any slide fails up front, writing nothing"""
        # given: slide 2 references an image that does not exist
        first = Canvas(160, 90).background(color="#1131AA")
        second = Canvas(160, 90).image(str(tmp_path / "missing.png"), position=(0, 0))
        deck = Deck(160, 90, slides=[first, second])
        output = tmp_path / "deck.gif"

        # when
        with pytest.raises(FileNotFoundError):
            deck.render(str(output))

        # then
        assert not output.exists()
