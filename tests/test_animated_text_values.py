"""Behavioral specifications for deterministic animated numeric text."""

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from quickthumb import Canvas, ValidationError


def _gif_frames(data: bytes) -> list[bytes]:
    image = Image.open(BytesIO(data))
    frames = []
    for index in range(getattr(image, "n_frames", 1)):
        image.seek(index)
        frames.append(image.convert("RGBA").tobytes())
    return frames


def test_counter_samples_values_and_round_trips_through_json():
    """Given a counter, when it is sampled and serialized, then its value is stable."""
    canvas = Canvas(320, 120).counter(
        0,
        100,
        1.0,
        position=(160, 60),
        align="center",
        size=48,
        prefix="$",
        grouping=True,
    )

    restored = Canvas.from_json(canvas.to_json())
    value = restored.layers[0].value

    assert value is not None
    assert value.text_at(0) == "$0"
    assert value.text_at(0.5) == "$75"
    assert value.text_at(1.0) == "$100"
    assert restored.render_frame(0).tobytes() != restored.render_frame(0.5).tobytes()


def test_counter_settles_on_its_final_value_wherever_there_is_no_timeline():
    """Given a counter, when rendered as a still, then it reads the number it lands on."""
    # Given: a counter that climbs from 96 to 148 after a delay
    canvas = (
        Canvas(600, 300)
        .background(color="#000000")
        .counter(
            96, 148, 1.0, delay=0.4, position=(40, 80), size=90, color="#FFFFFF", style="plain"
        )
    )

    # When: the composition is asked for its untimed, settled representation
    layer = canvas.layers[1]
    svg = canvas.to_svg()

    # Then: the still shows the value the count finished on, not the one it began from
    assert layer.content == "148"
    assert ">148<" in svg
    assert ">96<" not in svg

    # Then: a timed sample still reports where the count actually is
    assert layer.value is not None
    assert layer.value.text_at(0.0) == "96"
    assert layer.value.text_at(0.4) == "96"


def test_counter_duration_and_export_fallback_are_inspectable():
    """Given a counter, inspection exposes duration and static fallbacks."""
    canvas = Canvas(320, 120).counter(
        0,
        3,
        1.25,
        position=(160, 60),
        align="center",
        size=48,
        suffix=" exports",
    )

    assert canvas.inspect_motion(target="video").duration == pytest.approx(1.25)
    diagnostics = canvas.validate_export("pptx")
    assert diagnostics[0].feature == "animated_text_value"
    assert diagnostics[0].fallback == "static"


def test_counter_gif_contains_multiple_deterministic_states():
    """Given an odometer counter, when GIF is exported, then sampled states change reproducibly."""
    canvas = Canvas(320, 120).counter(
        0,
        9,
        0.8,
        position=(160, 60),
        align="center",
        size=48,
        color="#ffffff",
        minimum_integer_digits=2,
    )

    first = _gif_frames(canvas.to_gif(fps=10, hold=0))
    second = _gif_frames(canvas.to_gif(fps=10, hold=0))

    assert first == second
    assert len(set(first)) > 2


def test_large_odometer_range_reaches_a_fixed_width_target():
    """Given a large counter, when it settles, then the padded target is stable."""
    canvas = Canvas(640, 180).counter(
        1,
        100,
        1.4,
        position=(120, 90),
        size=68,
        minimum_integer_digits=3,
        style="odometer",
    )

    value = canvas.layers[0].value

    assert value is not None
    assert value.text_at(0.0) == "001"
    assert value.text_at(1.4) == "100"
    assert canvas.render_frame(0.7).tobytes() != canvas.render_frame(1.4).tobytes()


def _glyph_spans(canvas, time: float) -> list[tuple[int, int]]:
    """Return the horizontal ink span of each rendered glyph, left to right."""
    frame = canvas.render_frame(time).convert("L")
    lit = [
        any(frame.getpixel((x, y)) > 60 for y in range(frame.height)) for x in range(frame.width)
    ]
    spans, start = [], None
    for index, column in enumerate(lit):
        if column and start is None:
            start = index
        elif not column and start is not None:
            spans.append((start, index))
            start = None
    return spans


# A face whose `1` is far narrower than its widest digit, which is where a slot's
# reserve is wide enough to be seen. The bundled test fonts set a near-tabular 1.
DISPLAY_FONT = str(Path(__file__).parent.parent / "assets" / "fonts" / "Pretendard-Black.woff2")


def _odometer(settled: int, started: int):
    return (
        Canvas(520, 200)
        .background(color="#000000")
        .counter(
            started,
            settled,
            0.5,
            position=(40, 40),
            size=110,
            color="#FFFFFF",
            font=DISPLAY_FONT,
            style="odometer",
        )
    )


def test_odometer_carries_every_digit_on_the_same_slot_centre():
    """Given digits of different widths, when settled, then each sits mid-slot."""
    # Given: two readings that differ only in the width of their middle glyph
    narrow = _odometer(818, 800)
    wide = _odometer(888, 800)

    # When: the middle glyph of each is measured
    narrow_span = _glyph_spans(narrow, 3.0)[1]
    wide_span = _glyph_spans(wide, 3.0)[1]

    # Then: the narrow glyph is carried near the middle of its slot rather than
    # against one edge of it, which is where the whole reserve would otherwise go
    narrow_centre = sum(narrow_span) / 2
    wide_centre = sum(wide_span) / 2
    assert narrow_span[1] - narrow_span[0] < wide_span[1] - wide_span[0]
    # Left-aligning the narrow glyph puts the whole reserve on one side and moves
    # its centre roughly twice this far off its neighbour's at this type size.
    assert abs(narrow_centre - wide_centre) <= 8


def test_odometer_keeps_suffix_static_while_numeric_window_rolls():
    """Given a suffix, when digits roll, then only the numeric window changes."""
    canvas = Canvas(640, 180).counter(
        0,
        3,
        0.9,
        position=(120, 90),
        size=48,
        color="#d0a464",
        suffix=" formats ready",
    )

    before = canvas.render_frame(0.0)
    middle = canvas.render_frame(0.5)

    assert before.crop((160, 0, 640, 180)).tobytes() == middle.crop((160, 0, 640, 180)).tobytes()
    assert before.crop((100, 0, 160, 180)).tobytes() != middle.crop((100, 0, 160, 180)).tobytes()


def test_odometer_keeps_rolling_digits_inside_one_numeric_window():
    """Given an odometer, when digits roll, then they stay inside one visual row."""
    canvas = Canvas(640, 180).counter(
        1,
        100,
        1.4,
        position=(120, 90),
        size=48,
        minimum_integer_digits=3,
        style="odometer",
    )

    frame = canvas.render_frame(0.7)
    bbox = frame.getchannel("A").getbbox()

    assert bbox is not None
    assert bbox[3] - bbox[1] < 70


def test_odometer_keeps_digit_baseline_when_glyph_shape_changes():
    """Given 1-to-8 motion, when it settles, then the visible baseline is stable."""
    canvas = Canvas(320, 120).counter(
        1,
        8,
        1.0,
        position=(20, 20),
        size=48,
        style="odometer",
    )

    start_bbox = canvas.render_frame(0.0).getchannel("A").getbbox()
    end_bbox = canvas.render_frame(1.0).getchannel("A").getbbox()

    assert start_bbox is not None
    assert end_bbox is not None
    assert start_bbox[3] == end_bbox[3]


def test_flip_style_serializes_and_reaches_the_target_without_suffix_motion():
    """Given flip motion, when settled, then the target and label are stable."""
    canvas = Canvas(640, 180).counter(
        0,
        3,
        1.0,
        position=(120, 90),
        size=48,
        color="#d0a464",
        suffix=" formats ready",
        style="flip",
    )

    restored = Canvas.from_json(canvas.to_json())
    before = restored.render_frame(0.0)
    settled = restored.render_frame(1.0)

    assert restored.layers[0].value.style == "flip"
    assert restored.layers[0].value.text_at(1.0) == "3 formats ready"
    assert before.crop((160, 0, 640, 180)).tobytes() == settled.crop((160, 0, 640, 180)).tobytes()


def test_counter_rejects_rich_text_content():
    """Given rich text content, when a value animation is attached, then validation fails."""
    with pytest.raises(ValidationError, match="plain string content"):
        Canvas(320, 120).text(
            content=[{"text": "value", "bold": True}],
            position=(0, 0),
            value={"from": 0, "to": 1, "duration": 1},
        )
