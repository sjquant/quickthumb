"""Behavioral specifications for legacy animation easing and absolute timing."""

import json
import shutil
import subprocess
from importlib.resources import files

import pytest
from quickthumb import AnimationSpec, Canvas, CubicBezierEasing, Fade, ValidationError, Wipe
from quickthumb._export_video import _SlideAnimator

from tests._helpers import pixel_channel
from tests.test_export_html import timelines


def bar_canvas(animation, width=400):
    """Place one full-width bar under the given animation."""
    return (
        Canvas(width, 80)
        .background(color="#101010")
        .shape(
            shape="rectangle",
            position=(0, 30),
            width=width,
            height=20,
            color="#E8A552",
            animation=animation,
        )
    )


def revealed_width(canvas, time, width=400):
    """Return how far a left-to-right reveal has travelled."""
    frame = _SlideAnimator(canvas, {}).frame_at(time).convert("RGB")
    lit = [x for x in range(width) if pixel_channel(frame, (x, 40), 0) > 100]
    return max(lit) + 1 if lit else 0


class TestAnimationEasing:
    """An effect should be able to choose its own curve."""

    def test_should_reveal_at_a_constant_rate_when_asked_for_linear(self):
        """Given linear easing, when a bar fills, then progress tracks elapsed time."""
        # Given: a two-second wipe across a 400px bar
        canvas = bar_canvas(Wipe(direction="right", duration=2.0, easing="linear"))

        # When: the reveal is sampled at a quarter, a half, and three quarters
        widths = [revealed_width(canvas, time) for time in (0.5, 1.0, 1.5)]

        # Then: the bar measures elapsed time instead of flattering it
        assert widths == [
            pytest.approx(100, abs=3),
            pytest.approx(200, abs=3),
            pytest.approx(300, abs=3),
        ]

    def test_should_keep_the_eased_curve_as_the_default(self):
        """Given no easing, when a bar fills, then it accelerates and settles."""
        # Given: the same wipe without an explicit curve
        canvas = bar_canvas(Wipe(direction="right", duration=2.0))

        # When: the midpoint is compared with the linear equivalent
        eased = revealed_width(canvas, 1.0)

        # Then: the default curve is past halfway at the halfway mark
        assert eased > 250

    def test_should_reject_an_easing_it_cannot_evaluate(self):
        """Given an unknown easing name, when the effect is built, then it is refused."""
        # Given / When / Then: the shared easing vocabulary is enforced
        with pytest.raises(ValidationError):
            Wipe(direction="right", duration=1.0, easing="swoosh")  # ty: ignore[invalid-argument-type]


class TestAbsoluteAnimationStart:
    """An effect should be able to name the moment it plays."""

    def test_should_anchor_an_effect_to_an_absolute_slide_time(self):
        """Given a start time, when the slide plays, then the effect waits for it."""
        # Given: a reveal pinned to two seconds in
        canvas = bar_canvas(Wipe(direction="right", duration=0.5, start=2.0, easing="linear"))

        # When: the slide is sampled either side of that moment
        before = revealed_width(canvas, 1.9)
        after = revealed_width(canvas, 2.6)

        # Then: nothing happens until the named time, and it is done just after
        assert before == 0
        assert after == 400

    def test_should_not_drag_the_chain_along_with_an_anchored_effect(self):
        """Given an anchored effect, when others chain, then they keep their own order."""
        # Given: a late anchored bar declared before a normally chained one
        canvas = (
            Canvas(400, 120)
            .background(color="#101010")
            .shape(
                shape="rectangle",
                position=(0, 20),
                width=400,
                height=20,
                color="#E8A552",
                animation=Wipe(direction="right", duration=0.5, start=3.0, easing="linear"),
            )
            .shape(
                shape="rectangle",
                position=(0, 70),
                width=400,
                height=20,
                color="#F2EFE9",
                animation=Fade(duration=0.5),
            )
        )

        # When: the slide is sampled before the anchored effect fires
        frame = _SlideAnimator(canvas, {}).frame_at(1.0).convert("RGB")

        # Then: the chained fade has already run rather than waiting for the anchor
        assert pixel_channel(frame, (200, 80), 0) > 100
        assert pixel_channel(frame, (200, 30), 0) < 60

    def test_should_extend_the_slide_to_cover_an_anchored_effect(self):
        """Given a late anchor, when the slide is scheduled, then it runs long enough."""
        # Given: an effect anchored well past the other animations
        canvas = bar_canvas(Wipe(direction="right", duration=0.5, start=3.0))

        # When: the animator resolves the slide's settled duration
        duration = _SlideAnimator(canvas, {}).duration

        # Then: the slide lasts until the anchored effect has finished
        assert duration == pytest.approx(3.5)


class TestEasingReachesHtml:
    """The browser runtime should be told which curve to use."""

    @pytest.mark.parametrize(
        ("canonical", "easing", "css"),
        [
            (False, "ease_out_back", "cubic-bezier(0.34,1.56,0.64,1)"),
            (False, "linear", "linear"),
            (False, None, "ease"),
            (True, "linear", "linear"),
            (True, "ease_in_quad", "cubic-bezier(0.11,0,0.5,0)"),
            (True, None, "linear"),
            (True, CubicBezierEasing(points=(0.25, 0, 0.75, 1)), "cubic-bezier(0.25,0,0.75,1)"),
        ],
    )
    @pytest.mark.skipif(shutil.which("node") is None, reason="Node executes the HTML runtime")
    def test_should_publish_the_effect_easing_in_the_html_timeline(self, canonical, easing, css):
        """Preset HTML nodes pass their named or custom timing function to the actual runtime."""
        # Given: canonical or legacy effect data exported through real HTML
        options = {"easing": easing} if easing is not None else {}
        animation = (
            AnimationSpec.fade(duration=1, **options)
            if canonical
            else Wipe(direction="right", duration=1, **options)
        )
        [node] = timelines(bar_canvas(animation).to_html())[0]

        # When: the shipped runtime starts the exported node
        script = r"""
const assert=require('node:assert/strict');
const input=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
const CSS={escape:value=>value};
const timers=[];
function setTimeout(fn,delay){timers.push({fn,delay});}
eval(input.runtime);
const style={opacity:'',setProperty(){}};
const element={style,addEventListener(){},removeEventListener(){}};
const stage={getAttribute:()=>JSON.stringify([input.node]),querySelector:()=>element};
const timeline=new qtTimeline(stage);
timeline.advance();
assert.equal(style.animation,`${input.node.k} 1s ${input.css} both 0s`);
assert.equal(timers[0].delay,1000);
"""
        result = subprocess.run(
            ["node", "-e", script],
            input=json.dumps(
                {
                    "node": node,
                    "css": css,
                    "runtime": files("quickthumb.html").joinpath("timeline.js").read_text(),
                }
            ),
            capture_output=True,
            text=True,
            check=False,
        )

        # Then: CSS playback uses that curve instead of replacing it with default ease
        assert result.returncode == 0, result.stderr
