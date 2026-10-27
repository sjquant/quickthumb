"""Word and line motion uses the authored static text placement."""

import pytest
from quickthumb import (
    AnimationSpec,
    Canvas,
    KeyframeSpec,
    OpacityTrack,
    PositionTrack,
    StaggerSpec,
    TimingSpec,
)

FONT = "assets/fonts/Roboto-Regular.ttf"


def text_scene(content, motion=None, **options):
    return (
        Canvas(320, 180)
        .background(color="#000000")
        .text(
            content,
            font=FONT,
            size=40,
            color="#FFFFFF",
            position=(10, 10),
            animation=motion,
            **options,
        )
    )


@pytest.mark.parametrize("order", ["document", "reverse"])
def test_words_arrive_at_their_authored_positions(order):
    """Each word arrives independently in the requested order without shifting its final layout."""
    # Given: a delayed word entrance and the matching unanimated text
    motion = AnimationSpec(
        tracks=[
            OpacityTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=0.1, value=1)])
        ],
        timing=TimingSpec(start=0.2, duration=0.1),
        stagger=StaggerSpec(delay=0.5, target="words", order=order),
        easing="linear",
    )
    scene = text_scene("ONE TWO", motion)
    static = text_scene("ONE TWO").render_frame()

    # When: observing before the start, between word arrivals and after settling
    times = [0, 0.45, 1]
    frames = [item.to_image() for item in scene.sample(time=times, hold=0.5).frames]

    # Then: only the selected word is visible before both settle at the static positions
    assert frames[0].convert("RGB").getbbox() is None
    left, right = (0, 0, 90, 180), (90, 0, 320, 180)
    visible, hidden = (left, right) if order == "document" else (right, left)
    assert frames[1].crop(visible).tobytes() == static.crop(visible).tobytes()
    assert frames[1].crop(visible).convert("RGB").getbbox() is not None
    assert frames[1].crop(hidden).convert("RGB").getbbox() is None
    assert frames[-1].tobytes() == static.tobytes()
    for time, frame in zip(times, frames, strict=True):
        assert scene.render_frame(time).tobytes() == frame.tobytes()


@pytest.mark.parametrize("target", ["words", "lines"])
def test_wrapped_targets_keep_full_layout_and_independent_motion(target):
    """Wrapped word and line targets keep their measured row positions while moving separately."""
    # Given: two words wrapped to separate rows with per-target vertical motion
    motion = AnimationSpec(
        tracks=[
            PositionTrack(
                keyframes=[
                    KeyframeSpec(time=0, value=(0, 20)),
                    KeyframeSpec(time=0.2, value=(0, 0)),
                ]
            )
        ],
        timing=TimingSpec(duration=0.2),
        stagger=StaggerSpec(delay=0.5, target=target),
        easing="linear",
    )
    scene = text_scene("ONE TWO", motion, max_width=100)
    static = text_scene("ONE TWO", max_width=100).render_frame()

    # When: sampling during the first target, before the second, and at rest
    times = [0.1, 0.3, 0.8]
    frames = [item.to_image() for item in scene.sample(time=times, hold=0.5).frames]

    # Then: the second row waits while the first moves, and settled pixels equal static text
    assert frames[0].convert("RGB").getbbox()[1] > static.convert("RGB").getbbox()[1]
    assert frames[1].crop((0, 0, 320, 50)).tobytes() == static.crop((0, 0, 320, 50)).tobytes()
    assert frames[1].crop((0, 50, 320, 180)).convert("RGB").getbbox() is None
    assert frames[-1].tobytes() == static.tobytes()
    for time, frame in zip(times, frames, strict=True):
        assert scene.render_frame(time).tobytes() == frame.tobytes()


def test_blank_line_keeps_its_turn_in_the_timeline():
    """An empty line consumes its authored stagger delay without painting or shifting later text."""
    # Given: a blank line between two visible lines
    motion = AnimationSpec(
        tracks=[
            OpacityTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=0.1, value=1)])
        ],
        timing=TimingSpec(duration=0.1),
        stagger=StaggerSpec(delay=0.5, target="lines"),
        easing="linear",
    )
    scene = text_scene("ONE\n\nTWO", motion)
    static = text_scene("ONE\n\nTWO").render_frame()

    # When: the blank line has arrived but the last line has not
    frames = [item.to_image() for item in scene.sample(time=[0.75, 1.3], hold=0.5).frames]

    # Then: only the first line is visible, and the last line later reaches its original row
    assert frames[0].crop((0, 50, 320, 180)).convert("RGB").getbbox() is None
    assert frames[0].crop((0, 0, 320, 50)).tobytes() == static.crop((0, 0, 320, 50)).tobytes()
    assert frames[1].tobytes() == static.tobytes()
    assert scene.render_frame(0.75).tobytes() == frames[0].tobytes()
