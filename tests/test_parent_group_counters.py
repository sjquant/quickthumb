"""A group boundary follows sampled counters without changing settled layout."""

from io import BytesIO
from typing import Any, cast

import pytest
from PIL import Image, ImageFilter
from quickthumb import (
    Align,
    AnimatedTextValue,
    Background,
    BlurTrack,
    Canvas,
    ClipProgressTrack,
    ColorTrack,
    ExportPolicy,
    GifOptions,
    GroupLayer,
    LayerClip,
    LayerMask,
    NullLayer,
    OpacityTrack,
    RotationTrack,
    ScaleXTrack,
    ShapeLayer,
    TextLayer,
)
from quickthumb._color_motion import interpolate_color
from quickthumb._composition import apply_layer_composition
from quickthumb._export_base import _with_motion_color
from quickthumb._export_html import HtmlExporter
from quickthumb._export_video import _SlideAnimator
from quickthumb._measurements import measure_layers
from quickthumb._parent_diagnostics import ParentDiagnosticSources
from quickthumb._parent_render import ParentNode
from quickthumb.errors import RenderingError

from tests.test_parent_counters import (
    FONT,
    _oracle_matrix,
    _oracle_motion,
    _oracle_product,
    motion,
    track,
)
from tests.test_parent_documents import embedded_png


def freeze(layer):
    """Build the ordinary authored-still control without parent preparation."""
    if isinstance(layer, GroupLayer):
        return layer.model_copy(update={"children": [freeze(child) for child in layer.children]})
    if isinstance(layer, TextLayer) and layer.value is not None:
        return layer.model_copy(update={"content": layer.value.settled_text(), "value": None})
    return layer


def counter_scene(style="plain", layout="row", boundary="both"):
    canvas = Canvas(480, 320).null(id="root")
    counter = TextLayer(
        type="text",
        content="stale",
        id="counter",
        font=FONT,
        size=32,
        color="#FFFFFF",
        align=Align.BOTTOM_RIGHT,
        rotation=13,
        effects=[Background(color="#225588", padding=7)],
        value=AnimatedTextValue.model_validate(
            {
                "from": -8888,
                "to": 17,
                "duration": 1,
                "style": style,
                "prefix": "$",
                "suffix": " kg",
                "grouping": True,
                "easing": "linear",
            }
        ),
    )
    assert counter.value is not None
    sibling = ShapeLayer(
        type="shape",
        shape="rectangle",
        position=(0, 0),
        width=17,
        height=23,
        color="#ED4422",
        id="sibling",
    )
    # Work out these few slots independently of GroupEngine and ParentNode.
    width, height = canvas._text.measure_text_rendered_size(freeze(counter))
    x, y = 82, 62  # group position (75, 55) plus seven-pixel padding
    children: list[Any] = [counter, sibling]
    placed = []
    if layout == "nested":
        inner = sibling.model_copy(update={"width": 7, "height": 9, "id": "inner"})
        children = [
            GroupLayer(type="group", children=[counter, inner], padding=5, gap=3),
            sibling,
        ]
        x, y = x + 5, y + 5
        placed.append(inner.model_copy(update={"position": (x, y + height + 3)}))
        sibling_position = (82 + max(width, 7) + 10 + 13, 62)
    else:
        sibling_position = (x, y + height + 13) if layout == "column" else (x + width + 13, y)
    placed.insert(
        0,
        counter.model_copy(
            update={"content": counter.value.settled_text(), "position": (x + width, y + height)}
        ),
    )
    placed.append(sibling.model_copy(update={"position": sibling_position}))
    options: dict[str, Any] = {}
    if boundary in {"clip", "both"}:
        options["clip"] = LayerClip(
            position=("18%", "17%"), width=165, height=120, border_radius=17
        )
    if boundary in {"partial", "both", "inverted"}:
        options["mask"] = LayerMask(
            shape="ellipse",
            position=("22%", "26%"),
            width=140,
            height=115,
            align=Align.CENTER,
            opacity=0.4,
            invert=boundary == "inverted",
        )
    canvas.group(
        children,
        position=(75, 55),
        padding=7,
        gap=13,
        direction="column" if layout == "column" else "row",
        parent="root",
        id="group",
        **options,
    )
    return canvas, placed


def placed_frame(canvas, placed, time, *, color=None, composed=True):
    """Render ordinary static counter fragments on the authored canvas once."""
    frame = canvas._create_canvas()
    for layer in placed:
        layer = _with_motion_color(layer, color)
        fragments = (
            canvas._text.counter_paint_layers(layer, time)
            if isinstance(layer, TextLayer)
            else [layer]
        )
        for fragment in fragments:
            canvas._render_layer(frame, fragment)
    if composed:
        patch = apply_layer_composition(canvas._ctx, frame, canvas.layers[-1])
        frame = canvas._create_canvas()
        if patch is not None:
            frame.alpha_composite(patch.image, patch.offset)
    return frame


@pytest.mark.parametrize("style", ["plain", "odometer", "flip"])
@pytest.mark.parametrize("layout", ["row", "column", "nested"])
@pytest.mark.parametrize("boundary", ["clip", "partial", "both", "inverted"])
def test_sampled_group_matches_independent_settled_slots_and_single_boundary(
    style, layout, boundary
):
    canvas, placed = counter_scene(style, layout, boundary)
    bare = Canvas.from_json(canvas.to_json())
    cast(GroupLayer, bare.layers[-1]).clip = cast(GroupLayer, bare.layers[-1]).mask = None
    animator = _SlideAnimator(canvas, {})
    node = animator._units[-1].parent_node
    geometry = node.origin, node.body_to_baked, node.pivot_box, node.source_size
    original = canvas.to_json()
    frames = []
    for instant in (0, 0.349, 0.817, 1, 0.349):
        expected = placed_frame(canvas, placed, instant)
        actual = animator.frame_at(instant)
        assert actual.tobytes() == expected.tobytes()
        assert (
            bare.render_frame(instant).tobytes()
            == placed_frame(canvas, placed, instant, composed=False).tobytes()
        )
        assert (node.origin, node.body_to_baked, node.pivot_box, node.source_size) == geometry
        frames.append(actual.tobytes())
    assert len(set(frames)) >= 3
    assert canvas.to_json() == original


@pytest.mark.parametrize("style", ["plain", "odometer", "flip"])
def test_counter_outside_settled_body_survives_empty_prepared_source(style):
    canvas = Canvas(280, 160).null(id="root")
    counter = TextLayer(
        type="text",
        content="stale",
        font=FONT,
        size=40,
        align=Align.BOTTOM_RIGHT,
        color="#FFFFFF",
        value=AnimatedTextValue.model_validate(
            {"from": -88888, "to": 1, "duration": 1, "style": style, "easing": "linear"}
        ),
    )
    canvas.group(
        [counter],
        position=(180, 65),
        parent="root",
        id="group",
        mask=LayerMask(position=(70, 50), width=65, height=75, opacity=0.6),
    )
    width, height = canvas._text.measure_text_rendered_size(freeze(counter))
    placed = [counter.model_copy(update={"content": "1", "position": (180 + width, 65 + height)})]
    animator = _SlideAnimator(canvas, {})
    node = animator._units[-1].parent_node
    assert node.image is None
    assert node.unit.component_duration == 1
    assert node.pivot_box == (0, 0, width, height)
    image, offset = node.render_sample(0, None)
    assert image is not None and image.getbbox() is not None
    assert offset[0] < 0
    for instant in (0, 0.23, 1, 0):
        assert (
            animator.frame_at(instant).tobytes() == placed_frame(canvas, placed, instant).tobytes()
        )
    assert animator.frame_at(0).getbbox() is not None
    assert animator.frame_at(1).getbbox() is None


@pytest.mark.parametrize("style", ["plain", "odometer", "flip"])
def test_static_sibling_and_external_child_ignore_counter_width_and_boundary(style):
    canvas, _ = counter_scene(style, "nested", "both")
    group = cast(GroupLayer, canvas.layers[-1])
    nested = cast(GroupLayer, group.children[0])
    counter = cast(TextLayer, nested.children[0])
    counter.opacity = 0
    counter.effects = []
    canvas.shape("ellipse", (220, 75), 13, 11, "#22EE88", parent="group", id="marker")
    reference = Canvas(
        canvas.width, canvas.height, layers=[freeze(layer) for layer in canvas.layers]
    )
    animator = _SlideAnimator(canvas, {})
    marker = animator._units[-1].parent_node
    for instant in (0, 0.6, 0.9, 1, 0.6):
        assert animator.frame_at(instant).tobytes() == reference.render_frame(instant).tobytes()
        assert animator.frame_at(instant).getpixel((300, 135)) == (34, 238, 136, 255)
        assert marker.plan.sample(instant)[id(marker)][1] == (1, 0, 295, 0, 1, 130)


@pytest.mark.parametrize("quality", ["standard", "high"])
@pytest.mark.parametrize("style", ["plain", "odometer", "flip"])
def test_group_effects_under_three_ancestors_match_independent_affine_and_reverse_seeks(
    style, quality, monkeypatch
):
    canvas, placed = counter_scene(style, "nested", "both")
    group = cast(GroupLayer, canvas.layers[-1])
    group.parent = "c"
    group.animation = motion(
        track(RotationTrack, -10, 20),
        track(ScaleXTrack, 0.8, 1.2),
        track(OpacityTrack, 0.3, 0.9),
        track(ClipProgressTrack, 0.2, 1),
        track(BlurTrack, 0.5, 1.5),
        track(ColorTrack, "#3388DD", "#DD8833"),
    )
    canvas.layers = [
        NullLayer(type="null", id="a", position=(380, 80), animation=_oracle_motion(20, -0.8, 1.1)),
        NullLayer(
            type="null",
            id="b",
            parent="a",
            position=(10, 5),
            animation=_oracle_motion(-15, 1.2, 0.6),
        ),
        NullLayer(type="null", id="c", parent="b", position=(5, 3), rotation=10),
        group,
    ]
    ancestor = _oracle_product(
        _oracle_product(
            _oracle_matrix(380, 80, 20, -0.8, 1.1), _oracle_matrix(10, 5, -15, 1.2, 0.6)
        ),
        _oracle_matrix(5, 3, 10, 1, 1),
    )
    reference = placed_frame(canvas, placed, None, color="#FFFFFF")
    bounds = reference.getbbox()
    assert bounds is not None
    left, top, right, bottom = bounds
    cx, cy = (left + right) / 2, (top + bottom) / 2
    animator = _SlideAnimator(canvas, {}, quality=quality)
    node = animator._units[-1].parent_node
    assert node.pivot_box == (left - 75, top - 55, right - left, bottom - top)
    scale = 2 if quality == "high" else 1
    times = (0.81, 0.23, 1, 0.47, 0.81)
    originals = []
    for instant in times:
        own = _oracle_product(
            _oracle_matrix(cx, cy, -10 + 30 * instant, 0.8 + (1.2 - 0.8) * instant, 1),
            _oracle_matrix(-cx, -cy, 0, 1, 1),
        )
        matrix = _oracle_product(ancestor, own)
        expected_paint = _oracle_product(matrix, _oracle_matrix(75, 55, 0, 1, 1))
        assert node.plan.sample(instant)[id(node)][0] == pytest.approx(expected_paint)
        a, b, c, d, e, f = (value * scale for value in matrix)
        determinant = a * e - b * d
        assert determinant < 0 and abs(a * b + d * e) > 0.01
        color = interpolate_color("#3388DD", "#DD8833", instant)
        image = placed_frame(canvas, placed, instant, color=color)
        opacity = 0.9 if instant == 1 else 0.3 + (0.9 - 0.3) * instant
        alpha = image.getchannel("A").point(lambda value, opacity=opacity: round(value * opacity))
        cutoff = left + round((right - left) * (0.2 + 0.8 * instant)) + 1
        if instant < 1:
            alpha.paste(0, (cutoff, 0, image.width, image.height))
        image.putalpha(alpha)
        inverse = (
            e / determinant,
            -b / determinant,
            (b * f - e * c) / determinant,
            -d / determinant,
            a / determinant,
            (d * c - a * f) / determinant,
        )
        expected = Image.new("RGBA", (canvas.width * scale, canvas.height * scale))
        warped = image.transform(
            expected.size, Image.Transform.AFFINE, inverse, resample=Image.Resampling.BICUBIC
        )
        # The ordinary blur staging clears colors in fully transparent pixels.
        blurred = expected.copy()
        blurred.alpha_composite(warped)
        expected.alpha_composite(blurred.filter(ImageFilter.GaussianBlur((0.5 + instant) * scale)))
        if scale != 1:
            expected = expected.resize((canvas.width, canvas.height), Image.Resampling.LANCZOS)
        actual = animator.frame_at(instant)
        assert actual.tobytes() == expected.tobytes()
        originals.append(actual.tobytes())
    # A different transient buffer extent cannot move the root mask or reveal.
    original_sample = node.render_sample

    def padded(time, color):
        image, offset = original_sample(time, color)
        extra = Image.new("RGBA", (image.width + 74, image.height + 58))
        extra.paste(image, (31, 19))
        return extra, (offset[0] - 31, offset[1] - 19)

    monkeypatch.setattr(node, "render_sample", padded)
    assert [animator.frame_at(instant).tobytes() for instant in times] == originals


def clock_scene():
    def child(delay, duration, suffix, style):
        return TextLayer(
            type="text",
            content="stale",
            font=FONT,
            size=24,
            color="#FFFFFF",
            value=AnimatedTextValue.model_validate(
                {
                    "from": -99,
                    "to": 100,
                    "duration": duration,
                    "delay": delay,
                    "suffix": suffix,
                    "style": style,
                    "easing": "linear",
                }
            ),
        )

    return (
        Canvas(180, 140)
        .null((20, 10), id="root", animation=motion(track(RotationTrack, -5, 5), duration=0.2))
        .group(
            [
                child(0.4, 0.5, "A", "plain"),
                GroupLayer(type="group", children=[child(1.1, 0.6, "B", "odometer")]),
            ],
            position=(15, 20),
            parent="root",
            id="group",
            gap=5,
            mask=LayerMask(position=(0, 0), width=150, height=110, opacity=0.7),
            animation=motion(track(RotationTrack, 0, 4), duration=0.3),
        )
    )


def test_multiple_counter_clocks_extend_active_windows_and_actual_gif():
    canvas = clock_scene()
    animator = _SlideAnimator(canvas, {})
    assert animator.duration == pytest.approx(1.7)
    late_end = 1.1 + 0.6
    assert animator.segments(0.3, 2) == [
        (0.3, 0.4, False),
        (0.4, 0.9, True),
        (0.9, 1.1, False),
        (1.1, late_end, True),
        (late_end, 2, False),
    ]
    with Image.open(BytesIO(canvas.to_gif(fps=10, hold=0))) as gif:
        time = 0
        first, second = [], []
        for index in range(getattr(gif, "n_frames", 1)):
            gif.seek(index)
            if 0.4 <= time < 0.9:
                first.append(gif.convert("RGBA").tobytes())
            if 1.1 <= time < 1.7:
                second.append(gif.convert("RGBA").tobytes())
            time += gif.info.get("duration", 0) / 1000
    assert len(set(first)) >= 4 and len(set(second)) >= 4


@pytest.mark.parametrize("quality", ["standard", "high"])
def test_masked_counter_group_serial_and_spawn_gif_match(tmp_path, quality):
    canvas = clock_scene()
    serial, spawn = tmp_path / "serial.gif", tmp_path / "spawn.gif"
    canvas.render(str(serial), animation=GifOptions(fps=5, quality=quality))
    canvas.render(str(spawn), animation=GifOptions(fps=5, quality=quality, workers=2))
    assert serial.read_bytes() == spawn.read_bytes()


@pytest.mark.parametrize("kind", ["html", "svg", "pdf", "pptx"])
def test_counter_group_documents_freeze_whole_scene_and_protect_destination(tmp_path, kind):
    canvas = clock_scene().shape(
        "rectangle",
        (150, 120),
        12,
        10,
        "#FF0000",
        id="unlinked",
        animation=motion(track(OpacityTrack, 0.2, 0.8)),
    )
    canvas.layers = [*Canvas(180, 140).background(color="#FFFFFF").layers, *canvas.layers]
    expected = canvas._render_to_image()
    assert expected.tobytes() != canvas.render_frame(0).tobytes()
    assert expected.tobytes() != canvas.render_frame(1.7).tobytes()
    if kind == "pdf":
        import pypdfium2

        with pypdfium2.PdfDocument(canvas.to_pdf()) as document:
            page = document[0]
            bitmap = page.render(scale=1)
            assert bitmap.to_pil().convert("RGB").tobytes() == expected.convert("RGB").tobytes()
            bitmap.close()
            page.close()
    else:
        assert embedded_png(getattr(canvas, "to_" + kind)(), kind).tobytes() == expected.tobytes()
    if kind == "html":
        stage = HtmlExporter(canvas).render_stage()
        assert not stage.timeline and not stage.keyframes
    path = tmp_path / ("counters." + kind)
    report = canvas.export(path).capability_report
    assert {"parent", "animated_text_value"} <= {item.feature for item in report}
    assert any(item.layer_id == "unlinked" for item in report)
    assert all(item.support == "fallback" and item.fallback == "static" for item in report)
    for method in (canvas.render, canvas.export):
        path.write_bytes(b"existing")
        with pytest.raises(RenderingError, match="authored-static"):
            method(str(path), policy=ExportPolicy(unsupported_motion="error"))
        assert path.read_bytes() == b"existing"
    assert all(item.support == "full" for item in canvas.validate_export("video"))


def test_composed_counter_group_preflight_accepts_counter_without_paint(monkeypatch):
    canvas, _ = counter_scene()
    monkeypatch.setattr(canvas, "_render_layer", lambda *_: pytest.fail("preflight painted"))
    for target in ("raster", "video"):
        assert all(item.support == "full" for item in canvas.validate_export(target))
    for target in ("html", "pptx"):
        assert all(item.fallback == "static" for item in canvas.validate_export(target))


@pytest.mark.parametrize("boundary", ["both", "inverted"])
def test_static_observations_use_settled_counter_with_prefix_and_own_background(
    boundary, monkeypatch
):
    canvas, _ = counter_scene("odometer", "nested", boundary)
    group = cast(GroupLayer, canvas.layers[-1])
    group.children.insert(
        0,
        TextLayer(
            type="text",
            content="P",
            font=FONT,
            size=20,
            color="#EEBB77",
            effects=[Background(color="#AACCFF", padding=80)],
        ),
    )
    canvas.layers = [*Canvas(480, 320).background(color="#FFFFFF").layers, *canvas.layers]
    reference = Canvas(480, 320, layers=[freeze(layer) for layer in canvas.layers])
    original = canvas.to_json()
    assert canvas.inspect() == reference.inspect()
    assert canvas._render_to_image().tobytes() == reference._render_to_image().tobytes()
    assert (
        canvas._render_to_image(debug=True).tobytes()
        == reference._render_to_image(debug=True).tobytes()
    )
    assert canvas.diagnose().model_dump() == reference.diagnose().model_dump()
    pairs = []
    for scene in (canvas, reference):
        measured = measure_layers(scene)
        sources = ParentDiagnosticSources(scene, measured)
        text = measured[-1].children[1].children[0]
        assert text.metadata["content"] == "$17 kg"
        running = scene._create_canvas()
        scene._render_layer(running, scene.layers[0])
        first = sources.text_images(running, text)
        occurrence = sources.occurrences["counter"]
        source = occurrence.text
        assert source is not None
        coverage = Image.new("RGBA", occurrence.root.node.source_size)
        scene._text.render_text_layer(
            coverage,
            source.model_copy(update={"color": "#FFFFFF", "opacity": 1, "effects": []}),
            staging_reference=source,
        )
        world = scene._create_canvas()
        sources._composite_surface(world, coverage, occurrence.root)
        actual = scene._render_to_image()
        points = [
            (x, y)
            for y in range(scene.height)
            for x in range(scene.width)
            if cast(tuple, world.getpixel((x, y)))[3] == 255
            and cast(tuple, first[1].getpixel((x, y)))[3]
        ]
        assert len(points) > 20
        for point in points:
            assert (
                cast(tuple, first[1].getpixel(point))[:3] == cast(tuple, actual.getpixel(point))[:3]
            )
        prefix = sources._prefix(occurrence).tobytes()
        for _ in range(2):
            repeated = sources.text_images(running, text)
            assert [image.tobytes() for image in repeated] == [image.tobytes() for image in first]
            assert sources._prefix(sources.occurrences["counter"]).tobytes() == prefix
        pairs.append([image.tobytes() for image in first])
    assert pairs[0] == pairs[1]
    animator = _SlideAnimator(canvas, {})
    cache, count = canvas._ctx.measure_cache, len(canvas._ctx.measure_cache)
    for instant in (0.8, 0.2, 0.8):
        animator.frame_at(instant)
        assert canvas._ctx.motion_time is None
        assert canvas._ctx.measure_cache is cache and len(cache) == count
    monkeypatch.setattr(
        ParentNode, "render_source", lambda *args, **kwargs: pytest.fail("inspection painted")
    )
    assert canvas.inspect() == reference.inspect()
    assert canvas.to_json() == original


def test_counter_group_visual_snapshot():
    from pathlib import Path

    from examples.parent_group_counters import snapshot

    actual = snapshot()
    expected = Image.open(Path(__file__).parent / "snapshots/parent_group_counters.png").convert(
        "RGBA"
    )
    assert actual.size == expected.size and actual.tobytes() == expected.tobytes()
