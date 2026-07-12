"""Tests for animated GIF/MP4/WebM export (Canvas/Deck .to_gif/.to_mp4/.to_webm and render)."""

import shutil
from io import BytesIO

import pytest
from PIL import Image
from quickthumb import (
    Appear,
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

    def test_should_render_canvas_to_mp4_file(self, tmp_path):
        """Canvas.render dispatches .mp4 through the animation exporter"""
        # given
        canvas = red_box_slide()
        path = tmp_path / "clip.mp4"

        # when
        canvas.render(str(path))

        # then
        assert path.read_bytes()[4:8] == b"ftyp"

    def test_should_reap_ffmpeg_and_drop_output_when_a_slide_fails_mid_encode(self, tmp_path):
        """A slide failing to render mid-stream kills ffmpeg and removes the file"""

        # given: slide 2's custom layer raises while its frames are produced
        def boom(image):
            raise RuntimeError("boom")

        first = Canvas(160, 90).background(color="#1131AA")
        second = Canvas(160, 90).background(color="#22AA55").custom(boom)
        deck = Deck(160, 90, slides=[first, second])
        output = tmp_path / "deck.mp4"

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


class TestVideoErrors:
    """Test suite for animated-export validation and error paths"""

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
            ({"fps": 500}, "fps must be <= 120"),
            ({"hold": -1.0}, "slide_duration must be >= 0"),
            ({"loop": -1}, "loop must be >= 0"),
            ({"matte": "not-a-color"}, "Invalid matte color"),
        ],
        ids=["fps-zero", "fps-huge", "negative-hold", "negative-loop", "bad-matte"],
    )
    def test_should_validate_export_knobs(self, kwargs, message):
        """Out-of-range export settings raise a quickthumb ValidationError"""
        # given
        canvas = Canvas(160, 90).background(color="#1131AA")

        # when / then
        with pytest.raises(ValidationError, match=message):
            canvas.to_gif(**kwargs)

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
        """A failed video export removes its truncated output file"""
        # given: an "ffmpeg" that exits nonzero after creating the output
        fake = tmp_path / "fake-ffmpeg"
        fake.write_text('#!/bin/sh\nfor last; do :; done\ntouch "$last"\nexit 1\n')
        fake.chmod(0o755)
        monkeypatch.setenv("QUICKTHUMB_FFMPEG", str(fake))
        canvas = Canvas(160, 90).background(color="#1131AA")
        output = tmp_path / "clip.mp4"

        # when
        with pytest.raises(RenderingError, match="ffmpeg failed"):
            canvas.render(str(output))

        # then
        assert not output.exists()

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
