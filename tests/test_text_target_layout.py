"""Word and line motion uses the authored static text placement."""

import json
from io import BytesIO
from typing import cast
from zipfile import ZipFile

import jsonschema
import pytest
from PIL import Image, ImageColor
from quickthumb import (
    AnimationSpec,
    Canvas,
    ColorTrack,
    GifOptions,
    KeyframeSpec,
    OpacityTrack,
    PositionTrack,
    RangeSelector,
    RenderingError,
    RotationTrack,
    ScaleTrack,
    StaggerSpec,
    TimingSpec,
    canvas_json_schema,
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


@pytest.mark.parametrize(
    "shape,weights",
    [
        ("square", [1, 1]),
        ("ramp", [0.25, 0.75]),
        ("triangle", [0.5, 0.5]),
        ("smooth", [0.15625, 0.84375]),
    ],
)
def test_selector_shapes_survive_json_sampling_and_gif(shape, weights, tmp_path):
    """Word-center selector weights control actual opacity in restored frames and encoded GIF."""
    # Given: a fully transparent target value blended by a static range shape
    scene = text_scene(
        "ONE TWO",
        AnimationSpec.timeline(
            OpacityTrack(keyframes=[KeyframeSpec(time=0, value=0)]),
            selector=RangeSelector(shape=shape),
        ),
    )
    payload = json.loads(scene.to_json())
    jsonschema.validate(payload, canvas_json_schema())
    restored = Canvas.from_json(json.dumps(payload))

    # When: the same scene is sampled, inspected and encoded through public APIs
    frame = restored.render_frame(0).convert("RGB")
    sequence = restored.sample([0])
    assert sequence.frames[0].to_image().convert("RGB").tobytes() == frame.tobytes()
    output = tmp_path / "selector.gif"
    restored.export(output, animation=GifOptions(fps=10, hold=0.1))
    with Image.open(output) as image:
        decoded = image.convert("RGB")

    # Then: both static-layout words show the independently expected strengths
    for index, bounds in enumerate([(0, 0, 90, 180), (90, 0, 320, 180)]):
        expected = round(255 * (1 - weights[index]))
        assert frame.crop(bounds).getchannel("R").getextrema()[1] == pytest.approx(expected, abs=1)
        assert decoded.crop(bounds).getchannel("R").getextrema()[1] == pytest.approx(
            expected, abs=2
        )
    layer = restored.inspect_motion().slides[0].layers[1]
    assert layer.events[0].selector_weights == weights
    assert [target.source_range for target in layer.targets] == [(0, 3), (4, 7)]
    assert [target.samples[0]["opacity"] for target in layer.targets] == [1 - w for w in weights]


def test_selector_composition_keeps_document_indices_with_reverse_stagger(tmp_path):
    """Reverse delay changes execution rank while overlapping selectors blend in document order."""
    # Given: first-word suppression followed by a weighted opacity restoration
    first = AnimationSpec.timeline(
        OpacityTrack(keyframes=[KeyframeSpec(time=0, value=0)]),
        timing=TimingSpec(start=0.2),
        selector=RangeSelector(end=50),
    )
    second = AnimationSpec(
        tracks=[OpacityTrack(keyframes=[KeyframeSpec(time=0, value=1)])],
        timing=TimingSpec(start=0.2),
        selector=RangeSelector(shape="ramp"),
        stagger=StaggerSpec(delay=0.2, target="words", order="reverse"),
    )
    scene = text_scene("ONE TWO", [first, second])
    static = text_scene("ONE TWO").render_frame().convert("RGB")
    # When: before any event, between target turns and after both have run
    before, middle, final = [scene.render_frame(t).convert("RGB") for t in [0.1, 0.3, 0.5]]
    # Then: unselected text stays visible and the first word restores at 25%, not 75%
    assert before.tobytes() == static.tobytes()
    assert middle.crop((0, 0, 90, 180)).getbbox() is None
    assert final.crop((0, 0, 90, 180)).getchannel("R").getextrema()[1] == pytest.approx(64, abs=1)
    assert final.crop((90, 0, 320, 180)).tobytes() == static.crop((90, 0, 320, 180)).tobytes()
    inspected = scene.inspect_motion(fps=10).slides[0].layers[1]
    sample_index = inspected.sample_times.index(0.5)
    by_source = {
        target.source_range: target.samples[sample_index]["opacity"] for target in inspected.targets
    }
    assert by_source == {(0, 3): 0.25, (4, 7): 1.0}
    assert inspected.duration == pytest.approx(0.9)
    assert inspected.sample_times[-1] == pytest.approx(0.9)
    receipt = scene.export(tmp_path / "reverse.gif", animation=GifOptions(fps=10, hold=0.1))
    assert receipt.timing_metrics.duration == pytest.approx(inspected.duration + 0.1)


@pytest.mark.parametrize("start,end,offset", [(0, 50, 50), (50, 50, 0), (0, 100, 100)])
def test_shifted_and_empty_ranges_preserve_unselected_text(start, end, offset):
    """Translated ranges do not wrap, and zero-width ranges affect no words."""
    # Given: a range that either reaches only the last word or selects nothing
    scene = text_scene(
        "ONE TWO",
        AnimationSpec.timeline(
            OpacityTrack(keyframes=[KeyframeSpec(time=0, value=0)]),
            selector=RangeSelector(start=start, end=end, offset=offset),
        ),
    )
    # When/Then: static paint remains outside the translated half-open interval
    static = text_scene("ONE TWO").render_frame().convert("RGB")
    actual = scene.render_frame(0).convert("RGB")
    assert actual.crop((0, 0, 90, 180)).tobytes() == static.crop((0, 0, 90, 180)).tobytes()
    if end > start and offset == 50:
        assert actual.crop((90, 0, 320, 180)).getbbox() is None
    else:
        assert actual.tobytes() == static.tobytes()


def test_selected_line_geometry_settles_without_layout_shift():
    """Selected line geometry changes independently and returns to the exact authored layout."""
    # Given: the first of three lines selected, including an empty semantic line
    motion = AnimationSpec.timeline(
        PositionTrack(
            keyframes=[KeyframeSpec(time=0, value=(0, 4)), KeyframeSpec(time=0.2, value=(0, 0))]
        ),
        RotationTrack(keyframes=[KeyframeSpec(time=0, value=30), KeyframeSpec(time=0.2, value=0)]),
        ScaleTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=0.2, value=1)]),
        selector=RangeSelector(target="lines", end=33),
    )
    scene, static = text_scene("ONE\n\nTWO", motion), text_scene("ONE\n\nTWO").render_frame()
    # When/Then: movement affects the first row and settled paint restores the source exactly
    moving = scene.render_frame(0)
    assert moving.tobytes() != static.tobytes()
    assert moving.crop((0, 0, 320, 50)).convert("RGB").getbbox() is None
    with Image.open(BytesIO(scene.to_gif(fps=10, hold=0.1))) as image:
        assert image.convert("RGB").crop((0, 0, 320, 50)).getbbox() is None
        assert image.convert("RGB").crop((0, 80, 320, 180)).getbbox() is not None
    assert moving.crop((0, 80, 320, 180)).tobytes() == static.crop((0, 80, 320, 180)).tobytes()
    assert (
        scene.render_frame(0.1).crop((0, 80, 320, 180)).tobytes()
        == static.crop((0, 80, 320, 180)).tobytes()
    )
    assert scene.render_frame(0.2).tobytes() == static.tobytes()
    single = text_scene(
        "ONE",
        AnimationSpec.timeline(
            OpacityTrack(keyframes=[KeyframeSpec(time=0, value=0)]),
            selector=RangeSelector(),
        ),
    )
    assert single.render_frame(0).convert("RGB").getbbox() is None


@pytest.mark.parametrize("format", ["html", "pptx"])
def test_selector_document_fallback_is_authored_static(format):
    """Presentation documents retain authored text and declare static selector fallback."""
    if format == "pptx":
        pytest.importorskip("pptx")
    # Given: a selected word whose raster motion would remove its paint
    scene = text_scene(
        "ONE TWO",
        AnimationSpec.timeline(
            OpacityTrack(keyframes=[KeyframeSpec(time=0, value=0)]),
            selector=RangeSelector(end=50),
        ),
    )
    # When: presentation output is produced through its supported convenience boundary
    data = scene.to_html() if format == "html" else scene.to_pptx()
    # Then: the authored text remains and no runtime selector motion is attached
    if format == "html":
        assert "ONE TWO" in data and "visibility:hidden" not in data
    else:
        with ZipFile(BytesIO(data)) as archive:
            xml = archive.read("ppt/slides/slide1.xml").decode()
        assert "ONE TWO" in xml and "<p:timing" not in xml
    diagnostic = next(
        item for item in scene.validate_export(format) if item.feature == "text_selector"
    )
    assert diagnostic.fallback == "static"


def test_unsupported_selector_paths_cannot_write_approximate_output(tmp_path):
    """Unsupported target layouts fail before approximate output is written."""
    # Given: an existing output and rotated text outside exact target ownership
    output = tmp_path / "protected.gif"
    output.write_bytes(b"original")
    motion = AnimationSpec.timeline(
        OpacityTrack(keyframes=[KeyframeSpec(time=0, value=0)]),
        selector=RangeSelector(),
    )
    scene = text_scene("ONE TWO", motion, rotation=10)
    # When/Then: sampling and encoding reject the layout before replacing output
    with pytest.raises(RenderingError, match="plain separable words/lines"):
        scene.render_frame(0)
    with pytest.raises(RenderingError, match="plain separable words/lines"):
        scene.export(output, animation=GifOptions(fps=10, hold=0.1))
    assert output.read_bytes() == b"original"


@pytest.mark.parametrize("target", ["words", "lines"])
@pytest.mark.parametrize(
    "authored,color,selector,opacity,colors",
    [
        (None, "#00000000", RangeSelector(shape="ramp"), 1, ["#000000BF", "#00000040"]),
        ("#FF000040", "#FF0000C0", RangeSelector(shape="ramp"), 0.5, ["#FF000030", "#FF000050"]),
        ("#FF000040", "#FF0000C0", RangeSelector(end=50), 1, ["#FF0000C0", "#FF000040"]),
        ("#FF000000", "#FF0000FF", RangeSelector(shape="ramp"), 1, ["#FF000040", "#FF0000BF"]),
        ("#FF0000", "#0000FF", RangeSelector(shape="ramp"), 1, ["#C6496DFF", "#5147D2FF"]),
        ("#FF000040", "#0000FFC0", RangeSelector(shape="ramp"), 1, ["#8C53A260", "#2930EDA0"]),
    ],
)
def test_color_selectors_preserve_authored_paint_and_alpha(
    target, authored, color, selector, opacity, colors
):
    """Selected colors preserve authored/default paint through JSON, sampling and GIF."""
    # Given: perceptual hue/alpha blends, including default and invisible source paint
    selector = selector.model_copy(update={"target": target})
    scene = Canvas(320, 180).text(
        "ONE TWO" if target == "words" else "ONE\nTWO",
        font=FONT,
        size=40,
        color=authored,
        opacity=opacity,
        position=(10, 10),
        animation=AnimationSpec.timeline(
            ColorTrack(keyframes=[KeyframeSpec(time=0, value=color)]),
            timing=TimingSpec(start=0.2, duration=0.2),
            selector=selector,
        ),
    )
    restored = Canvas.from_json(scene.to_json())
    boxes = (
        [(0, 0, 90, 180), (90, 0, 320, 180)]
        if target == "words"
        else [
            (0, 0, 320, 50),
            (0, 50, 320, 180),
        ]
    )

    # When: a frame is sampled before/after the event and decoded from the default GIF palette
    before, after = restored.render_frame(0.1), restored.render_frame(0.2)
    with Image.open(BytesIO(restored.to_gif(fps=10, hold=0.1, matte="#FFFFFF"))) as image:
        image.seek(int(getattr(image, "n_frames", 1)) - 1)
        decoded = image.convert("RGB")

    # Then: authored alpha is not multiplied twice and zero-weight targets retain their own paint
    source_alpha = 255 if authored is None or len(authored) == 7 else int(authored[-2:], 16)
    expected = [
        cast(tuple[int, int, int, int], ImageColor.getcolor(value, "RGBA")) for value in colors
    ]
    alphas = [value[3] for value in expected]
    for bounds, rgba in zip(boxes, expected, strict=True):
        assert before.crop(bounds).getchannel("A").getextrema()[1] == round(source_alpha * opacity)
        crop = after.crop(bounds)
        core = max(
            cast(tuple[tuple[int, int, int, int], ...], crop.get_flattened_data()),
            key=lambda pixel: pixel[3],
        )
        assert core == rgba
        matte_rgb = tuple(round(channel * rgba[3] / 255 + 255 - rgba[3]) for channel in rgba[:3])
        assert any(
            max(abs(actual - wanted) for actual, wanted in zip(pixel, matte_rgb, strict=True)) <= 2
            for pixel in cast(
                tuple[tuple[int, int, int], ...], decoded.crop(bounds).get_flattened_data()
            )
        )
    matte = Image.alpha_composite(Image.new("RGBA", after.size, "#FFFFFF"), after)
    assert (
        restored.sample([0.2], matte="#FFFFFF").frames[0].to_image().convert("RGBA").tobytes()
        == matte.tobytes()
    )
    layer = restored.inspect_motion(fps=10).slides[0].layers[0]
    index = layer.sample_times.index(0.2)
    sampled_colors = [item.samples[index]["color"] for item in layer.targets]
    assert [
        round((int(value[-2:], 16) if len(value) == 9 else 255) * opacity)
        for value in sampled_colors
    ] == alphas


def test_color_selectors_compose_from_the_incoming_color():
    """Later weighted color selectors blend from earlier target paint in authored order."""
    # Given: first-word recoloring followed by a ramp over both words
    first = AnimationSpec.timeline(
        ColorTrack(keyframes=[KeyframeSpec(time=0, value="#FF000040")]),
        timing=TimingSpec(start=0),
        selector=RangeSelector(end=50),
    )
    second = AnimationSpec.timeline(
        ColorTrack(keyframes=[KeyframeSpec(time=0, value="#FF0000FF")]),
        timing=TimingSpec(start=0),
        selector=RangeSelector(shape="ramp"),
    )
    scene = Canvas(320, 180).text(
        "ONE TWO",
        font=FONT,
        size=40,
        color="#FF0000C0",
        position=(10, 10),
        animation=[first, second],
    )
    # When/Then: each word's resulting alpha reflects its incoming, not original, paint
    frame = scene.render_frame(0)
    assert frame.crop((0, 0, 90, 180)).getchannel("A").getextrema()[1] == 112
    assert frame.crop((90, 0, 320, 180)).getchannel("A").getextrema()[1] == 239
