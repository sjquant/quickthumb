"""Behavioral specifications for deterministic animated numeric text."""

from io import BytesIO

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
    assert (
        before.crop((160, 0, 640, 180)).tobytes()
        == settled.crop((160, 0, 640, 180)).tobytes()
    )


def test_counter_rejects_rich_text_content():
    """Given rich text content, when a value animation is attached, then validation fails."""
    with pytest.raises(ValidationError, match="plain string content"):
        Canvas(320, 120).text(
            content=[{"text": "value", "bold": True}],
            position=(0, 0),
            value={"from": 0, "to": 1, "duration": 1},
        )
