"""GIF facts describe the bytes written after palette normalization and merging."""

from io import BytesIO

import pytest
from PIL import Image, ImageSequence
from quickthumb._gif import write_gif_frames
from quickthumb.errors import RenderingError


def _frame(index):
    image = Image.new("RGB", (20, 20), (20, 40, 60))
    image.paste((200, 80, 100), (index, 2, index + 5, 12))
    return image.quantize()


def _assert_facts_and_bytes(frames, durations, expected_facts):
    expected = BytesIO()
    frames[0].save(
        expected,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=3,
        optimize=True,
    )
    output = BytesIO()
    facts = write_gif_frames(zip(frames, durations, strict=True), output, 3)
    assert output.getvalue() == expected.getvalue()
    with Image.open(BytesIO(output.getvalue())) as image:
        parsed_durations = [
            frame.info.get("duration", 0) for frame in ImageSequence.Iterator(image)
        ]
        assert facts == (len(parsed_durations), sum(parsed_durations))
    assert facts == expected_facts


@pytest.mark.parametrize("duration", [0, 1, 9, 10, 19, 27, 655359])
def test_single_frame_facts_match_encoded_bytes(duration):
    _assert_facts_and_bytes([_frame(0)], [duration], (1, duration // 10 * 10))


@pytest.mark.parametrize(
    ("indices", "durations", "expected_facts"),
    [
        ([0, 0, 0], [13, 13, 13], (1, 30)),
        ([0, 0], [6, 6], (1, 10)),
        ([0, 1, 2], [13, 13, 13], (3, 30)),
        ([0, 1, 2], [9, 1, 0], (3, 0)),
        ([0, 0, 1, 1, 2], [6, 6, 19, 12, 9], (3, 40)),
        ([0, 1, 1], [19, 6, 6], (2, 20)),
        ([0, 1, 0], [17, 28, 39], (3, 60)),
    ],
)
def test_distinct_and_duplicate_frame_facts_match_encoded_bytes(indices, durations, expected_facts):
    _assert_facts_and_bytes([_frame(index) for index in indices], durations, expected_facts)


@pytest.mark.parametrize("include_distinct", [False, True])
def test_equivalent_palettes_merge_before_counting_frames_and_duration(include_distinct):
    colors = [(20, 40, 60), (200, 80, 100), (40, 200, 80), (100, 60, 200)]
    first = Image.new("P", (16, 20))
    first.putpalette([channel for color in colors for channel in color])
    first.putdata([0, 1, 2, 3] * 80)
    equivalent = Image.new("P", first.size)
    equivalent.putpalette([channel for color in reversed(colors) for channel in color])
    equivalent.putdata([3, 2, 1, 0] * 80)
    assert first.tobytes() != equivalent.tobytes()
    assert first.convert("RGB").tobytes() == equivalent.convert("RGB").tobytes()

    frames, durations = [first, equivalent], [6, 6]
    expected_facts = (1, 10)
    if include_distinct:
        distinct = first.copy()
        distinct.putpixel((1, 3), 2)
        frames.extend([distinct, distinct.copy(), equivalent])
        durations.extend([16, 16, 29])
        expected_facts = (3, 60)
    _assert_facts_and_bytes(frames, durations, expected_facts)


@pytest.mark.parametrize("indices", [[0], [0, 1]])
@pytest.mark.parametrize("operation", ["write", "flush"])
def test_output_failure_does_not_return_facts(indices, operation):
    class FailingOutput(BytesIO):
        def write(self, data):
            if operation == "write":
                raise OSError("output write failed")
            return super().write(data)

        def flush(self):
            if operation == "flush":
                raise OSError("output flush failed")
            return super().flush()

    facts = None
    with pytest.raises(OSError, match=f"output {operation} failed"):
        facts = write_gif_frames(((_frame(index), 20) for index in indices), FailingOutput(), 0)
    assert facts is None


def test_producer_failure_does_not_return_facts():
    def frames():
        yield _frame(0), 20
        yield _frame(1), 20
        raise RuntimeError("producer failed")

    output = BytesIO()
    facts = None
    with pytest.raises(RuntimeError, match="producer failed"):
        facts = write_gif_frames(frames(), output, 0)
    assert facts is None
    assert output.getvalue().startswith(b"GIF89a")


def test_empty_input_does_not_return_facts():
    output = BytesIO()
    facts = None
    with pytest.raises(RenderingError, match="no frames"):
        facts = write_gif_frames([], output, 0)
    assert facts is None
    assert output.getvalue() == b""
