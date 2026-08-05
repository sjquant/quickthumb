"""Behavioral specifications for motion around backdrop-dependent layers."""

import pytest
from quickthumb import (
    AnimationSpec,
    BackdropBlur,
    Canvas,
    KeyframeSpec,
    PositionTrack,
    RenderingError,
    TimingSpec,
    Wipe,
)
from quickthumb._export_video import _SlideAnimator

from tests._helpers import lit_span, pixel_channel

FONT = "assets/fonts/Roboto-Medium.ttf"


def travel(distance, duration=2.0):
    """Build a linear left-to-right position track."""
    return AnimationSpec.timeline(
        PositionTrack(
            keyframes=[
                KeyframeSpec(time=0.0, value=(0.0, 0.0)),
                KeyframeSpec(time=duration, value=(float(distance), 0.0)),
            ]
        ),
        timing=TimingSpec(start=0.0, duration=duration),
        easing="linear",
    )


def frosted_canvas(bar_animation=None, panel_animation=None):
    """Place a bar under a frosted panel, either of which may animate."""
    return (
        Canvas(400, 200)
        .background(color="#0A0E12")
        .shape(
            shape="rectangle",
            position=(0, 80),
            width=60,
            height=40,
            color="#E8A552",
            animation=bar_animation,
        )
        .shape(
            shape="rectangle",
            position=(0, 0),
            width=400,
            height=200,
            color="#0A0E12",
            opacity=0.35,
            effects=[BackdropBlur(radius=10)],
            animation=panel_animation,
        )
    )


def bar_span(animator, time):
    """Return the horizontal extent of the bar seen through the panel."""
    return lit_span(animator.frame_at(time).convert("RGB"), row=100, threshold=180)


class TestMotionUnderABackdrop:
    """A frosted panel should not freeze the composition beneath it."""

    def test_should_move_a_layer_that_sits_under_a_backdrop_blur(self):
        """Given a blurred panel above it, when a layer moves, then it still travels."""
        # Given: a bar travelling under a frosted panel
        animator = _SlideAnimator(frosted_canvas(bar_animation=travel(200)), {})

        # When: the slide is sampled across the move
        # Then: the panel blurs the bar without pinning it in place
        assert bar_span(animator, 0.0) == (0, 59)
        assert bar_span(animator, 1.0) == (100, 159)
        assert bar_span(animator, 2.0) == (200, 259)

    def test_should_let_the_frosted_panel_itself_animate(self):
        """Given a panel that fades in, when the slide plays, then the fade renders."""
        # Given: a frosted panel carrying its own fade
        canvas = frosted_canvas(panel_animation=AnimationSpec.fade(duration=1.0))
        animator = _SlideAnimator(canvas, {})

        # When: the frame is sampled before and after the fade settles
        early = animator.frame_at(0.05).convert("RGB").getpixel((300, 40))
        settled = animator.frame_at(1.2).convert("RGB").getpixel((300, 40))

        # Then: the panel arrives rather than being there from the first frame
        assert early != settled

    def test_should_still_refuse_an_entrance_effect_inside_the_backdrop_group(self):
        """Given a legacy effect below a backdrop, when exported, then it is refused clearly."""
        # Given: a PPTX-style reveal on a layer the backdrop must rasterize with
        canvas = frosted_canvas(bar_animation=Wipe(direction="right", duration=1.0))

        # When / Then: the refusal names the real constraint and the way out
        with pytest.raises(RenderingError, match="AnimationSpec"):
            _SlideAnimator(canvas, {})


class TestCanonicalAlphaMatchesAcrossPipelines:
    """Opacity and clip should be applied once, the same way, everywhere."""

    def test_should_fade_at_the_same_rate_in_stills_and_video(self):
        """Given a fade, when both pipelines sample it, then neither squares it."""
        # Given: a plain one-second fade
        canvas = (
            Canvas(200, 100)
            .background(color="#000000")
            .shape(
                shape="rectangle",
                position=(0, 0),
                width=200,
                height=100,
                color="#FFFFFF",
                animation=AnimationSpec.fade(duration=1.0),
            )
        )

        # When: the midpoint is measured in both pipelines
        still = pixel_channel(canvas.render_frame(0.5).convert("RGB"), (100, 50), 0)
        moving = pixel_channel(
            _SlideAnimator(canvas, {}).frame_at(0.5).convert("RGB"), (100, 50), 0
        )

        # Then: halfway through a linear fade is halfway, not a quarter
        assert still == pytest.approx(128, abs=2)
        assert moving == pytest.approx(128, abs=2)

    def test_should_type_without_fading(self):
        """Given a typewriter, when it plays, then it reveals at full strength."""
        # Given: text typing over one second
        canvas = (
            Canvas(400, 100)
            .background(color="#000000")
            .text(
                content="TYPEWRITER",
                font=FONT,
                size=40,
                color="#FFFFFF",
                position=(10, 20),
                animation=AnimationSpec.typewriter(duration=1.0),
            )
        )

        # When: an early frame is measured in both pipelines
        still = canvas.render_frame(0.25).convert("RGB")
        moving = _SlideAnimator(canvas, {}).frame_at(0.25).convert("RGB")

        def typed(frame):
            lit = [
                x for x in range(400) if any(frame.getpixel((x, y))[0] > 200 for y in range(100))
            ]
            return max(lit) if lit else None

        # Then: the letters already typed are solid, not a quarter transparent
        assert typed(still) == typed(moving)
        assert typed(moving) is not None
