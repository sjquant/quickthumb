"""Keep raster placement, inspection, and native document text in agreement."""

import pytest
from PIL import Image
from quickthumb import Canvas, TextPart
from quickthumb._export_base import compute_text_layout
from quickthumb.models import TextLayer


@pytest.mark.parametrize("spacing", [-2, 0, 4])
@pytest.mark.parametrize("align", [("left", "top"), ("center", "middle"), ("right", "bottom")])
def test_multiline_measurement_keeps_blank_line_in_native_export(spacing, align):
    canvas = Canvas(400, 300).text(
        "Ag\n\njp", size=32, position=(200, 150), align=align, letter_spacing=spacing
    )
    layer = canvas._layers[0]
    assert isinstance(layer, TextLayer)
    measured = canvas._text.measure_text_layout(layer)
    exported = compute_text_layout(canvas, layer)

    assert measured["wrapped_lines"] == ("Ag", "", "jp")
    assert [len(line) for line in exported.lines] == [1, 0, 1]
    assert measured["size"][1] == sum(exported.line_heights)
    first, last = exported.lines[0][0], exported.lines[2][0]
    assert last.ink_box[1] - first.ink_box[1] == sum(exported.line_heights[:2])


@pytest.mark.parametrize("max_width", [None, 100, "35%"])
@pytest.mark.parametrize("spacing", [-2, 0, 4])
def test_rich_native_runs_follow_raster_paint_positions(monkeypatch, max_width, spacing):
    canvas = Canvas(400, 300).text(
        [
            TextPart(text="Ag\n\n", size=35),
            TextPart(text="jp wide words", size=23, letter_spacing=spacing),
        ],
        position=(200, 150),
        align=("center", "middle"),
        max_width=max_width,
    )
    layer = canvas._layers[0]
    assert isinstance(layer, TextLayer)
    painted = []
    paint = canvas._text._render_text_part

    def record(draw, image, part, font, position):
        painted.append((part, font, position))
        return paint(draw, image, part, font, position)

    monkeypatch.setattr(canvas._text, "_render_text_part", record)
    canvas._text.render_text_layer(Image.new("RGBA", (400, 300)), layer)
    exported = compute_text_layout(canvas, layer)
    measured = canvas._text.measure_text_layout(layer)
    runs = [run for line in exported.lines for run in line]

    assert len(runs) == len(painted)
    assert measured["size"][1] == sum(exported.line_heights)
    assert measured["wrapped_lines"] == tuple(
        "".join(run.text for run in line) for line in exported.lines
    )
    for run, (part, font, (x, y)) in zip(runs, painted, strict=True):
        assert run.text == part["text"]
        assert run.font is font
        if part["letter_spacing"]:
            assert run.ink_box[:2] == (x, y)
        else:
            bbox = font.getbbox(part["text"], anchor="lt")
            assert run.ink_box[:2] == (x + bbox[0], y + bbox[1])


@pytest.mark.parametrize("rotation", [-27, 90])
@pytest.mark.parametrize("rich", [False, True])
def test_rotation_stage_matches_native_transform_and_measured_size(monkeypatch, rotation, rich):
    from quickthumb.models import Shadow

    content = (
        [TextPart(text="Ag jp", size=45), TextPart(text=" tail", size=24)] if rich else "Ag jp"
    )
    canvas = Canvas(400, 300).text(
        content,
        size=45,
        max_width=100,
        max_height=80,
        auto_scale=True,
        position=(200, 150),
        align=("center", "middle"),
        rotation=rotation,
        effects=[Shadow(color="#000000", offset_x=-8, offset_y=3, blur_radius=4)],
    )
    source = canvas._layers[0]
    assert isinstance(source, TextLayer)
    layer = canvas._text.effective_layer(source)
    stages = []
    composites = []
    image = Image.new("RGBA", (400, 300))
    paint = canvas._text._rotate_and_composite_text
    composite = image.alpha_composite

    def record(image, temp_image, layer, **kwargs):
        stages.append(temp_image.size)
        return paint(image, temp_image, layer, **kwargs)

    def record_composite(source, dest=(0, 0), **kwargs):
        composites.append((source.size, dest))
        return composite(source, dest=dest, **kwargs)

    monkeypatch.setattr(canvas._text, "_rotate_and_composite_text", record)
    monkeypatch.setattr(image, "alpha_composite", record_composite)
    canvas._text.render_text_layer(image, layer)
    exported = compute_text_layout(canvas, layer)
    staged_size = stages[0]
    rotated_size, position = composites[0]

    assert canvas._text.measure_text_rendered_size(layer) == rotated_size
    assert exported.rot_center_local == (staged_size[0] / 2, staged_size[1] / 2)
    assert exported.origin == (
        position[0] + (rotated_size[0] - staged_size[0]) / 2,
        position[1] + (rotated_size[1] - staged_size[1]) / 2,
    )


@pytest.mark.parametrize("content", ["AA", "AA\nAA", "AA\n"])
def test_rich_measurement_preserves_negative_line_width(content):
    canvas = Canvas(150, 120).text([TextPart(text=content, letter_spacing=-25)], size=16)
    layer = canvas._layers[0]
    assert isinstance(layer, TextLayer)
    font = canvas._fonts.load_font(layer)
    widths = [canvas._text.measure_text_bounds(line, font, -25)[0] for line in content.split("\n")]
    expected = max(widths)
    if not content.endswith("\n"):
        assert expected < 0
    assert canvas._text.measure_text_size(layer)[0] == expected
    assert canvas._text.rotation_stage(layer).size[0] == expected + 20


@pytest.mark.parametrize("rich", [False, True])
@pytest.mark.parametrize("align", [("center", "middle"), ("right", "bottom")])
@pytest.mark.parametrize("rotation", [27, 1e-14, -1e-14, 89.99999999999999, 90.00000000000001])
def test_rotated_text_keeps_legacy_pillow_alignment(rich, align, rotation):
    from quickthumb._base import apply_alignment

    content = [TextPart(text="AA", letter_spacing=-25)] if rich else "AA"
    canvas = Canvas(150, 120).text(
        content, size=16, position=(100, 90), align=align, rotation=rotation
    )
    layer = canvas._layers[0]
    assert isinstance(layer, TextLayer)
    width, height = canvas._text.measure_text_size(layer)
    staged_size = (width + 20, height + 20)
    staging = Image.new("RGBA", staged_size)
    inner = layer.model_copy(update={"position": (10, 10), "align": None, "rotation": 0})
    canvas._text.render_text_layer(staging, inner)
    rotated = staging.rotate(-rotation, expand=True, resample=Image.Resampling.BICUBIC)
    assert layer.align is not None
    position = apply_alignment(100, 90, rotated.size, layer.align)
    expected = Image.new("RGBA", (150, 120))
    expected.alpha_composite(rotated, position)

    actual = Image.new("RGBA", (150, 120))
    canvas._text.render_text_layer(actual, layer)
    assert actual.tobytes() == expected.tobytes()
    assert canvas._text.measure_text_rendered_size(layer) == rotated.size
    exported = compute_text_layout(canvas, layer)
    assert exported.origin == (
        position[0] + (rotated.width - staged_size[0]) / 2,
        position[1] + (rotated.height - staged_size[1]) / 2,
    )
