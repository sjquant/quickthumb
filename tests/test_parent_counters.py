"""Intrinsic counter paint can change without moving its settled parent frame."""

import math
from io import BytesIO
from typing import Any, cast

import pytest
from PIL import Image
from quickthumb import (
    Align,
    AnimatedTextValue,
    AnimationSpec,
    Background,
    Canvas,
    ExportPolicy,
    GifOptions,
    GroupLayer,
    KeyframeSpec,
    NullLayer,
    RotationTrack,
    ScaleXTrack,
    ScaleYTrack,
    Shadow,
    ShapeLayer,
    TextLayer,
    TimingSpec,
)
from quickthumb._export_video import _SlideAnimator
from quickthumb._measurements import measure_layers
from quickthumb._parent_diagnostics import ParentDiagnosticSources
from quickthumb._parent_render import ParentNode, settled_content
from quickthumb.errors import RenderingError

FONT = "assets/fonts/NotoSerif-Italic.ttf"


def motion(*tracks, duration=1):
    tracks = [
        item.model_copy(
            update={
                "keyframes": [
                    key.model_copy(update={"time": key.time * duration}) for key in item.keyframes
                ]
            }
        )
        for item in tracks
    ]
    return AnimationSpec.timeline(*tracks, timing=TimingSpec(duration=duration), easing="linear")


def track(kind, first, last):
    return kind(keyframes=[KeyframeSpec(time=0, value=first), KeyframeSpec(time=1, value=last)])


def linked_counter(style="plain", **kwargs):
    base = Canvas(500, 320).counter(
        99, 100, 1, position=(230, 140), font=FONT, size=52, style=style, **kwargs
    )
    layer = cast(Any, base.layers[0])
    linked = Canvas(
        500,
        320,
        layers=[
            NullLayer(type="null", id="root"),
            layer.model_copy(update={"parent": "root", "id": "counter", "content": "0"}),
        ],
    )
    return base, linked


@pytest.mark.parametrize("style", ["plain", "odometer", "flip"])
@pytest.mark.parametrize(
    "values,options",
    [
        ((11, 88), {"align": "center"}),
        ((99, 100), {"align": "bottom-right", "rotation": 27}),
        ((100, 99), {"align": "center", "rotation": -19}),
        ((-99.9, 100.1), {"decimals": 1, "prefix": "$", "suffix": " kg", "grouping": True}),
        (
            (1099, -12),
            {
                "align": "center",
                "prefix": "=",
                "suffix": " points",
                "grouping": True,
                "minimum_integer_digits": 3,
            },
        ),
        (
            (-8888, 111),
            {
                "align": "bottom-right",
                "rotation": 21,
                "auto_scale": True,
                "max_width": 170,
                "max_height": 100,
                "suffix": " units",
                "effects": [
                    Shadow(offset_x=-12, offset_y=8, blur_radius=3, color="#AABBFF"),
                    Background(color="#243040", padding=9),
                ],
            },
        ),
        ((1, 12), {"align": "center", "max_width": 150, "prefix": "Total \n", "suffix": " units"}),
    ],
)
def test_identity_parent_keeps_counter_paint_and_reverse_seek_bytes(style, values, options):
    base = Canvas(500, 320).counter(
        values[0],
        values[1],
        1,
        delay=0.2,
        position=(250, 150),
        font=FONT,
        size=44,
        style=style,
        easing="linear",
        **options,
    )
    layer = cast(Any, base.layers[0])
    linked = Canvas(
        500,
        320,
        layers=[
            NullLayer(type="null", id="root"),
            layer.model_copy(update={"content": "0", "parent": "root"}),
        ],
    )
    before = linked.to_json()
    animator = _SlideAnimator(linked, {})
    for instant in (0, 0.2, 0.333, 0.619, 0.817, 1.2, 2, 0.333):
        assert animator.frame_at(instant).tobytes() == base.render_frame(instant).tobytes()
    assert linked._render_to_image().tobytes() == base._render_to_image().tobytes()
    assert linked.to_json() == before


@pytest.mark.parametrize("style", ["plain", "odometer", "flip"])
def test_unpositioned_counter_keeps_ordinary_plain_sampling(style):
    base, linked = linked_counter(style)
    cast(Any, base.layers[0]).position = None
    cast(Any, base.layers[0]).align = None
    cast(Any, linked.layers[1]).position = None
    cast(Any, linked.layers[1]).align = None
    for instant in (0, 0.3, 0.8, 1):
        assert linked.render_frame(instant).tobytes() == base.render_frame(instant).tobytes()


@pytest.mark.parametrize("style", ["plain", "odometer", "flip"])
def test_offcanvas_local_counter_is_clipped_only_after_world_placement(style):
    base, linked = linked_counter(style, align="center", rotation=25)
    cast(Any, linked.layers[0]).position = (430, 180)
    cast(Any, linked.layers[1]).position = (-200, -40)
    for instant in (0, 0.2, 0.55, 1):
        assert linked.render_frame(instant).tobytes() == base.render_frame(instant).tobytes()


def test_ordinary_flip_visibility_probe_is_preserved():
    canvas = Canvas(80, 60).counter(
        99, 100, 1, style="flip", position=(-200, -100), easing="linear"
    )
    assert canvas.render_frame(0.3).getbbox() is None
    layer = cast(Any, canvas.layers[0])
    # Parent-local preparation deliberately keeps these same off-canvas leaves.
    assert canvas._text.counter_paint_layers(layer, 0.3)
    assert not canvas._text.counter_paint_layers(layer, 0.3, viewport=Image.new("RGBA", (80, 60)))


@pytest.mark.parametrize("style", ["plain", "odometer", "flip"])
@pytest.mark.parametrize("quality", ["standard", "high"])
def test_counter_frame_and_visible_child_follow_only_authored_geometry(style, quality):
    _, canvas = linked_counter(style, align="center", rotation=23, auto_scale=True, max_width=90)
    root = cast(Any, canvas.layers[0])
    root.position = (80, 40)
    root.animation = motion(track(ScaleXTrack, 1.2, -1.2), track(RotationTrack, 0, 35))
    canvas.null(
        (15, 10),
        id="arm",
        parent="root",
        animation=motion(track(ScaleYTrack, 1, 0.45), track(RotationTrack, 0, -20)),
    )
    counter = cast(Any, canvas.layers[1])
    counter.parent = "arm"
    counter.position = (60, 30)
    counter.animation = motion(track(RotationTrack, 0, 40))
    counter.opacity = 0
    child = ShapeLayer(
        type="shape",
        shape="rectangle",
        position=(5, 7),
        width=9,
        height=6,
        color="#FF0000",
        parent="counter",
    )
    canvas.layers = [*canvas.layers, child]
    fixed = counter.model_copy(update={"content": counter.value.settled_text(), "value": None})
    reference = Canvas(500, 320, layers=[root, fixed, canvas.layers[2], child])
    actual = _SlideAnimator(canvas, {}, quality=quality)
    expected = _SlideAnimator(reference, {}, quality=quality)
    node = next(
        unit.parent_node
        for unit in actual._units
        if unit.parent_node and unit.parent_node.layer.id == "counter"
    )
    geometry = node.origin, node.body_to_baked, node.pivot_box, node.source_size
    for instant in (0.17, 0.8, 0.5, 1, 0.17):
        assert actual.frame_at(instant).tobytes() == expected.frame_at(instant).tobytes()
        assert (node.origin, node.body_to_baked, node.pivot_box, node.source_size) == geometry
        if instant == 0.5:
            assert actual.frame_at(instant).getbbox() is None
    assert actual.frame_at(0.17).getbbox() is not None


def group_scene():
    value = AnimatedTextValue.model_validate(
        {
            "from": 99,
            "to": 105,
            "duration": 1.2,
            "delay": 0.5,
            "style": "odometer",
            "easing": "linear",
        }
    )
    return (
        Canvas(260, 160)
        .null((20, 15), id="root")
        .group(
            [
                GroupLayer(
                    type="group",
                    children=[
                        TextLayer(
                            type="text",
                            content="0",
                            font=FONT,
                            size=36,
                            color="#FFFFFF",
                            value=value,
                            align=Align.CENTER,
                            animation=motion(track(RotationTrack, 0, 150)),
                        )
                    ],
                    padding=8,
                ),
                ShapeLayer(
                    type="shape",
                    shape="rectangle",
                    position=(0, 0),
                    width=10,
                    height=18,
                    color="#FF0000",
                ),
            ],
            position=(20, 20),
            direction="row",
            gap=11,
            parent="root",
            id="group",
            animation=motion(track(RotationTrack, 0, 0), duration=0.2),
        )
    )


def test_nested_counter_layout_stays_settled_and_suppressed_motion_keeps_value():
    canvas = group_scene()
    original = canvas.to_json()
    reference_group = settled_content(canvas.layers[1]).model_copy(
        update={"parent": None, "position": (40, 35)}
    )
    reference = Canvas(260, 160, layers=[reference_group])
    animator = _SlideAnimator(canvas, {})
    node = animator._units[-1].parent_node
    geometry = node.origin, node.body_to_baked, node.pivot_box
    frames = []
    for instant in (0, 0.6, 0.87, 1.4, 1.7, 0.87):
        frame = animator.frame_at(instant)
        frames.append(frame.tobytes())
        expected = reference._create_canvas()
        reference._groups.render_group_layer(
            expected, reference_group, time=instant, sample_values=True
        )
        assert frame.tobytes() == expected.tobytes()
        assert (node.origin, node.body_to_baked, node.pivot_box) == geometry
    assert len(set(frames)) >= 4
    assert canvas.to_json() == original


def test_actual_gif_samples_group_value_after_ancestor_motion_finishes():
    canvas = group_scene()
    animator = _SlideAnimator(canvas, {})
    assert animator.duration == pytest.approx(1.7)
    assert animator.segments(0.2, 2) == [(0.2, 0.5, False), (0.5, 1.7, True), (1.7, 2, False)]
    with Image.open(BytesIO(canvas.to_gif(fps=10, hold=0))) as image:
        time = 0
        later = []
        for index in range(getattr(image, "n_frames", 1)):
            image.seek(index)
            if 0.5 <= time < 1.6:
                later.append(image.convert("RGBA").tobytes())
            time += image.info.get("duration", 0) / 1000
    assert len(set(later)) >= 5


@pytest.mark.parametrize("quality", ["standard", "high"])
def test_counter_gif_spawn_matches_serial(tmp_path, quality):
    canvas = group_scene()
    one, two = tmp_path / "one.gif", tmp_path / "two.gif"
    canvas.render(str(one), animation=GifOptions(fps=5, quality=quality))
    canvas.render(str(two), animation=GifOptions(fps=5, quality=quality, workers=2))
    assert one.read_bytes() == two.read_bytes()


def test_settled_inspection_never_paints_or_mutates_authored_value(monkeypatch):
    _, canvas = linked_counter(
        "odometer", align="center", rotation=21, auto_scale=True, max_width=85
    )
    original = canvas.to_json()
    reference_layer = cast(Any, canvas.layers[1]).model_copy(
        update={"content": "100", "value": None}
    )
    reference = Canvas(500, 320, layers=[canvas.layers[0], reference_layer]).inspect()
    monkeypatch.setattr(ParentNode, "render_source", lambda *args, **kwargs: pytest.fail("paint"))
    monkeypatch.setattr(canvas, "_render_layer", lambda *args: pytest.fail("paint"))
    actual = canvas.inspect()
    assert actual == reference
    assert canvas.to_json() == original


def test_settled_diagnostic_foreground_and_background_match_static_text():
    _, canvas = linked_counter(
        "flip",
        align="center",
        rotation=24,
        auto_scale=True,
        max_width=110,
        effects=[
            Background(color="#FFFFFF", padding=10),
            Shadow(offset_x=8, offset_y=3, blur_radius=3, color="#AABBFF"),
        ],
    )
    layer = cast(Any, canvas.layers[1])
    reference = Canvas(
        500,
        320,
        layers=[canvas.layers[0], layer.model_copy(update={"content": "100", "value": None})],
    )
    pairs = []
    for scene in (canvas, reference):
        measured = measure_layers(scene)
        sources = ParentDiagnosticSources(scene, measured)
        pairs.append(sources.text_images(scene._create_canvas(), measured[1]))
        assert measured[1].metadata["content"] == "100"
    for counter, fixed in zip(pairs[0], pairs[1], strict=True):
        assert counter.tobytes() == fixed.tobytes()
    assert canvas._render_to_image().tobytes() == reference._render_to_image().tobytes()


@pytest.mark.parametrize("style", ["plain", "odometer", "flip", "group"])
def test_sample_sources_restore_context_and_do_not_accumulate_layout_cache(style, monkeypatch):
    canvas = group_scene() if style == "group" else linked_counter(style)[1]
    animator = _SlideAnimator(canvas, {})
    cache = canvas._ctx.measure_cache
    count = len(cache)
    for instant in (0.3, 0.7, 0.4):
        animator.frame_at(instant)
        assert canvas._ctx.motion_time is None
        assert canvas._ctx.measure_cache is cache and len(cache) == count
    monkeypatch.setattr(
        canvas, "_render_layer", lambda *args: (_ for _ in ()).throw(RuntimeError("paint"))
    )
    with pytest.raises(RuntimeError, match="paint"):
        animator.frame_at(0.5)
    assert canvas._ctx.motion_time is None
    assert canvas._ctx.measure_cache is cache and len(cache) == count


@pytest.mark.parametrize("kind", ["html", "svg", "pptx", "pdf"])
def test_documents_freeze_settled_counters_and_report_both_capabilities(tmp_path, kind):
    from tests.test_parent_documents import embedded_png

    _, canvas = linked_counter("odometer", align="center", rotation=19)
    canvas.layers = [*Canvas(500, 320).background(color="#FFFFFF").layers, *canvas.layers]
    expected = canvas._render_to_image()
    assert expected.tobytes() != canvas.render_frame(1).tobytes()
    if kind == "pdf":
        import pypdfium2

        with pypdfium2.PdfDocument(canvas.to_pdf()) as document:
            page = document[0]
            bitmap = page.render(scale=1)
            actual = bitmap.to_pil().convert("RGB")
            assert actual.tobytes() == expected.convert("RGB").tobytes()
            bitmap.close()
            page.close()
    else:
        actual = embedded_png(getattr(canvas, "to_" + kind)(), kind)
        assert actual.tobytes() == expected.tobytes()
    path = tmp_path / ("counter." + kind)
    report = canvas.export(path)
    features = {item.feature for item in report.capability_report}
    assert {"parent", "animated_text_value"} <= features
    assert all(item.fallback == "static" for item in report.capability_report)
    path.write_bytes(b"existing")
    with pytest.raises(RenderingError):
        canvas.export(path, policy=ExportPolicy(unsupported_motion="error"))
    assert path.read_bytes() == b"existing"
    assert all(item.support == "full" for item in canvas.validate_export("video"))


@pytest.mark.parametrize("style", ["plain", "odometer", "flip"])
@pytest.mark.parametrize("legacy", [False, True])
def test_reveal_color_opacity_and_blur_ignore_extra_sample_buffer(style, legacy, monkeypatch):
    from quickthumb import BlurTrack, ClipProgressTrack, ColorTrack, OpacityTrack, Wipe

    _, canvas = linked_counter(style, align="center", rotation=17)
    layer = cast(Any, canvas.layers[1])
    layer.value = layer.value.model_copy(update={"from_": 1, "to": 1000})
    layer.animation = (
        Wipe(duration=1, direction="right")
        if legacy
        else motion(
            track(ClipProgressTrack, 0.1, 1),
            track(ColorTrack, "#FF0000", "#00AAFF"),
            track(OpacityTrack, 0.4, 1),
            track(BlurTrack, 1, 3),
            track(RotationTrack, 0, 20),
        )
    )
    animator = _SlideAnimator(canvas, {})
    node = animator._units[-1].parent_node
    original = node.render_sample
    times = (0.13, 0.37, 0.81)
    expected = [animator.frame_at(instant).tobytes() for instant in times]

    def padded(time, color):
        image, offset = original(time, color)
        assert image is not None
        extra = Image.new("RGBA", (image.width + 74, image.height + 58))
        extra.paste(image, (31, 19))
        return extra, (offset[0] - 31, offset[1] - 19)

    monkeypatch.setattr(node, "render_sample", padded)
    assert [animator.frame_at(instant).tobytes() for instant in times] == expected
    assert len(set(expected)) == len(times)


def test_nested_group_suppresses_image_and_qr_motion_but_keeps_counter(tmp_path):
    from quickthumb import ImageLayer, QRCodeLayer, ScaleTrack

    path = tmp_path / "strip.png"
    strip = Image.new("RGB", (60, 24), "blue")
    strip.paste("red", (0, 0, 20, 24))
    strip.save(path)
    canvas = group_scene()
    group = cast(GroupLayer, canvas.layers[1])
    nested = cast(GroupLayer, group.children[0])
    nested.children.extend(
        [
            ImageLayer(
                type="image",
                path=str(path),
                position=(0, 0),
                width=60,
                height=24,
                animation=motion(track(ScaleTrack, 1, 2)),
            ),
            QRCodeLayer(
                type="qr_code", data="counter", size=48, animation=AnimationSpec.qr_reveal()
            ),
        ]
    )
    reference = Canvas(
        260, 160, layers=[canvas.layers[0], canvas._groups._without_child_animation(group)]
    )
    # Keep the same root override and immutable settled group layout.
    cast(Any, reference.layers[1]).animation = group.animation
    frames = []
    for instant in (0, 0.25, 0.75, 1.5):
        actual = canvas.render_frame(instant)
        assert actual.tobytes() == reference.render_frame(instant).tobytes()
        frames.append(actual.tobytes())
    assert len(set(frames)) >= 3


def test_intrinsic_counter_coverage_does_not_mark_children_or_siblings_as_moving():
    canvas = group_scene()
    group = cast(GroupLayer, canvas.layers[1])
    group.animation = None
    counter = cast(TextLayer, cast(GroupLayer, group.children[0]).children[0])
    counter.animation = None
    counter.id = "nested_counter"
    group.children[1].id = "sibling"
    canvas.counter(0, 100, 1, position=(180, 100), parent="root", id="counter")
    canvas.shape("rectangle", (0, 0), 3, 3, "#FF0000", id="child", parent="counter")
    measurements = measure_layers(canvas)
    sources = ParentDiagnosticSources(canvas, measurements)
    assert sources.occurrences["group"].animated
    assert sources.occurrences["nested_counter"].animated
    assert sources.occurrences["counter"].animated
    assert not sources.occurrences["sibling"].animated
    assert not sources.occurrences["child"].animated


def test_changing_counter_background_cannot_certify_permanent_occlusion():
    canvas = (
        Canvas(180, 100)
        .shape("rectangle", (60, 20), 5, 5, "#00FF00", id="lower")
        .null((10, 10), id="root")
        .counter(
            0,
            999,
            1,
            position=(0, 0),
            size=30,
            style="plain",
            parent="root",
            effects=[Background(color="#FFFFFF", padding=10)],
        )
    )
    assert canvas.render_frame(0).getpixel((62, 22)) == (0, 255, 0, 255)
    assert canvas.render_frame(1).getpixel((62, 22)) == (255, 255, 255, 255)
    assert not any(
        finding.code == "layer-hidden" and finding.layer_id == "lower"
        for finding in canvas.diagnose().findings
    )


@pytest.mark.parametrize("grouped", [False, True])
def test_ordinary_counter_export_keeps_existing_sample_grid(grouped):
    from quickthumb._export_video import _slide_samples

    canvas = Canvas(100, 80).counter(0, 100, 1, delay=0.15, position=(10, 20), style="plain")
    if grouped:
        canvas = Canvas(100, 80).group(
            [cast(TextLayer, canvas.layers[0]).model_copy(update={"position": None})],
            animation=motion(track(ScaleXTrack, 1, 2), duration=2),
        )
    animator = _SlideAnimator(canvas, {})
    duration, count = (2, 20) if grouped else (1.15, 12)
    assert animator.segments(0, duration) == [(0, duration, True)]
    samples = list(_slide_samples(animator, 0, duration, 10))
    assert len(samples) == count
    assert samples[1][0] == pytest.approx(duration / count)


def test_parent_counter_visual_snapshot():
    from pathlib import Path

    from examples.parent_counters import build_scene

    canvas = build_scene()
    strip = Image.new("RGBA", (1800, 280))
    for index, instant in enumerate((0, 0.49, 1.4)):
        strip.paste(canvas.render_frame(instant), (index * 600, 0))
    expected = Image.open(Path(__file__).parent / "snapshots/parent_counters.png").convert("RGBA")
    assert strip.size == expected.size and strip.tobytes() == expected.tobytes()


def _oracle_motion(angle, sx, sy):
    return AnimationSpec.timeline(
        *[
            kind(keyframes=[KeyframeSpec(time=0, value=value)])
            for kind, value in ((RotationTrack, angle), (ScaleXTrack, sx), (ScaleYTrack, sy))
        ],
        timing=TimingSpec(duration=1),
    )


def _oracle_matrix(x, y, angle, sx, sy):
    radians = math.radians(angle)
    return (
        math.cos(radians) * sx,
        -math.sin(radians) * sy,
        x,
        math.sin(radians) * sx,
        math.cos(radians) * sy,
        y,
    )


def _oracle_product(left, right):
    a, b, c, d, e, f = left
    g, h, i, j, k, n = right
    return (
        a * g + b * j,
        a * h + b * k,
        a * i + b * n + c,
        d * g + e * j,
        d * h + e * k,
        d * i + e * n + f,
    )


@pytest.mark.parametrize("reflection", [1, -1, 0])
@pytest.mark.parametrize("style", ["plain", "odometer", "flip"])
def test_visible_counter_matches_independent_full_canvas_affine(reflection, style):
    base = Canvas(650, 500).counter(
        0,
        1234,
        2,
        position=(100, 100),
        suffix="%",
        size=50,
        font="assets/fonts/NotoSerif-Italic.ttf",
        style=style,
        rotation=17,
        align="center",
        auto_scale=True,
        max_width=95,
        max_height=70,
    )
    linked = Canvas(
        650,
        500,
        layers=[
            NullLayer(
                type="null", id="a", position=(220, 90), animation=_oracle_motion(23, 1.4, 0.7)
            ),
            NullLayer(
                type="null",
                id="b",
                parent="a",
                position=(30, 20),
                animation=_oracle_motion(35, 0.8 * reflection, 1.3),
            ),
            cast(TextLayer, base.layers[0]).model_copy(update={"parent": "b"}),
        ],
    )
    # Compute the full mapping independently of ParentRenderPlan and its helpers.
    a, b, c, d, e, f = _oracle_product(
        _oracle_matrix(220, 90, 23, 1.4, 0.7),
        _oracle_matrix(30, 20, 35, 0.8 * reflection, 1.3),
    )
    determinant = a * e - b * d
    for time in (0.23, 0.73, 2):
        if determinant == 0:
            expected = Image.new("RGBA", (650, 500))
        else:
            inverse = (
                e / determinant,
                -b / determinant,
                (b * f - e * c) / determinant,
                -d / determinant,
                a / determinant,
                (d * c - a * f) / determinant,
            )
            expected = base.render_frame(time).transform(
                (650, 500),
                Image.Transform.AFFINE,
                inverse,
                resample=Image.Resampling.BICUBIC,
            )
        assert linked.render_frame(time).tobytes() == expected.tobytes()
