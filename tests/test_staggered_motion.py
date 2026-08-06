"""Behavioral specifications for staggering motion across a layer's targets."""

from quickthumb import AnimationSpec, Canvas
from quickthumb._export_video import _SlideAnimator

from tests._helpers import ink_bands

FONT = "assets/fonts/Pretendard-ExtraBold.woff2"


def staggered_canvas(stagger=0.4, target="lines", content="ONE\nTWO\nTHREE"):
    """Place a multi-line headline under a staggered rise."""
    return (
        Canvas(600, 300)
        .background(color="#000000")
        .text(
            content=content,
            font=FONT,
            size=56,
            color="#FFFFFF",
            position=(40, 40),
            line_height=1.3,
            animation=AnimationSpec.rise(
                from_="bottom", distance=60, duration=0.5, stagger=stagger, target=target
            ),
        )
    )


def line_tops(frame):
    """Return the top row of every separated band of ink in a frame."""
    return [band[0] for band in ink_bands(frame.convert("RGB"))]


class TestStaggeredTargetsMoveIndependently:
    """A stagger should sequence its targets, not shift the block as one."""

    def test_should_bring_lines_in_one_after_another(self):
        """Given a line stagger, when it plays, then each line arrives on its own beat."""
        # Given: three lines rising 0.4s apart
        canvas = staggered_canvas()

        # When: the composition is sampled across the sequence
        early = line_tops(canvas.render_frame(0.1))
        middle = line_tops(canvas.render_frame(0.5))
        late = line_tops(canvas.render_frame(0.9))

        # Then: the lines appear one at a time rather than all at once
        assert len(early) == 1
        assert len(middle) == 2
        assert len(late) == 3

    def test_should_settle_every_line_in_its_laid_out_place(self):
        """Given a finished stagger, when settled, then the block is where it belongs."""
        # Given: the same headline, staggered and static
        staggered = staggered_canvas()
        static = staggered_canvas(stagger=0.0)

        # When: both are sampled after the motion has run
        assert line_tops(staggered.render_frame(2.0)) == line_tops(static.render_frame(2.0))

    def test_should_hold_a_line_off_screen_until_its_turn(self):
        """Given a stagger, when a line is waiting, then it is not already in place."""
        # Given: a stagger sampled while the last line is still waiting
        canvas = staggered_canvas()

        # When: the first frame is measured against the settled one
        waiting = line_tops(canvas.render_frame(0.1))
        settled = line_tops(canvas.render_frame(2.0))

        # Then: only the first line is on screen, and it has not landed yet
        assert len(waiting) == 1
        assert waiting[0] != settled[0]

    def test_should_stagger_the_same_way_in_stills_and_video(self):
        """Given one composition, when both pipelines run, then the sequence matches."""
        # Given: a staggered headline
        canvas = staggered_canvas()
        animator = _SlideAnimator(canvas, {})

        # When: the same instants are sampled in each pipeline
        # Then: neither pipeline sequences the lines differently
        for time in (0.1, 0.5, 0.9, 1.6):
            assert line_tops(canvas.render_frame(time)) == line_tops(animator.frame_at(time))

    def test_should_move_a_single_line_headline_as_one_block(self):
        """Given one target, when it animates, then nothing is sliced apart."""
        # Given: a stagger declared on a headline that has only one line
        canvas = staggered_canvas(content="ONE")

        # When: the motion is sampled part way through
        tops = line_tops(canvas.render_frame(0.2))

        # Then: the single line still rises as a whole
        assert len(tops) == 1
        assert tops[0] != line_tops(canvas.render_frame(2.0))[0]
