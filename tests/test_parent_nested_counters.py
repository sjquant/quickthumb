"""Counter fragments retain nested isolation without changing settled parent slots."""

import gc
import weakref
from typing import Any, cast

import pytest
from PIL import Image, ImageFilter
from quickthumb import (
    Align,
    AnimatedTextValue,
    AnimationSpec,
    Background,
    BlurTrack,
    Canvas,
    ChartLayer,
    ClipProgressTrack,
    ColorTrack,
    GroupLayer,
    LayerClip,
    LayerMask,
    NullLayer,
    OpacityTrack,
    QRCodeLayer,
    RotationTrack,
    ScaleXTrack,
    Shadow,
    ShapeLayer,
    TextLayer,
)
from quickthumb._color_motion import interpolate_color
from quickthumb._composition import apply_layer_composition
from quickthumb._export_base import _with_motion_color
from quickthumb._export_video import _SlideAnimator
from quickthumb._parent_render import ParentNode, _ParentCounterTextEngine, parent_rendering_problem
from quickthumb.models import BarChartSpec, VideoLayer

from tests.test_parent_counters import (
    FONT,
    _oracle_matrix,
    _oracle_motion,
    _oracle_product,
    motion,
    track,
)
from tests.test_parent_group_counters import freeze


def nested_counter_scene(style="plain", boundary="partial"):
    canvas = Canvas(480, 320).null(id="root")
    counter = TextLayer(
        type="text",
        id="counter",
        content="stale",
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
        clip=LayerClip(position=("16%", "17%"), width=195, height=165, border_radius=8),
        mask=LayerMask(position=("18%", "19%"), width=185, height=155, opacity=0.75),
    )
    inner_shape = ShapeLayer(
        type="shape", shape="rectangle", position=(0, 0), width=7, height=9, color="#44EE88"
    )
    inner = GroupLayer(
        type="group",
        children=[counter, inner_shape],
        padding=5,
        gap=3,
        mask=LayerMask(
            position=("18%", "19%"),
            width=160,
            height=150,
            opacity=0.5,
            invert=boundary == "inverted",
        ),
    )
    middle = GroupLayer(
        type="group",
        children=[inner],
        padding=(3, 4),
        clip=LayerClip(position=("16%", "17%"), width=195, height=175),
        mask=LayerMask(
            position=(65, 45), width=225, height=200, opacity=0 if boundary == "empty" else 0.8
        ),
    )
    sibling = inner_shape.model_copy(update={"width": 17, "height": 23, "color": "#ED4422"})
    canvas.group(
        [middle, sibling],
        position=(75, 55),
        padding=7,
        gap=13,
        direction="row",
        id="group",
        parent="root",
        clip=LayerClip(position=("16%", "17%"), width=225, height=180),
        mask=LayerMask(position=(70, 45), width=230, height=200, opacity=0.6),
    )
    # Independent row/column arithmetic from the settled text dimensions.
    width, height = canvas._text.measure_text_rendered_size(freeze(counter))
    x, y = 75 + 7 + 4 + 5, 55 + 7 + 3 + 5
    placed = [
        counter.model_copy(update={"content": "$17 kg", "position": (x + width, y + height)}),
        inner_shape.model_copy(update={"position": (x, y + height + 3)}),
        sibling.model_copy(update={"position": (75 + 7 + max(width, 7) + 10 + 8 + 13, 55 + 7)}),
    ]
    return canvas, placed


def boundary_image(canvas, surface, layer):
    patch = apply_layer_composition(canvas._ctx, surface, layer)
    result = canvas._create_canvas()
    if patch is not None:
        result.alpha_composite(patch.image, patch.offset)
    return result


def nested_frame(canvas, placed, time, color=None):
    """Combine ordinary fragments in the fixture's known scopes, in authored coordinates."""
    owner = cast(GroupLayer, canvas.layers[-1])
    middle = cast(GroupLayer, owner.children[0])
    inner = cast(GroupLayer, middle.children[0])
    counter, inside, outside = [_with_motion_color(layer, color) for layer in placed]
    paint = canvas._create_canvas()
    for fragment in canvas._text.counter_paint_layers(counter, time):
        # The counter owner clips all fragments together, including their effects.
        canvas._text.render_text_layer(paint, fragment)
    paint = boundary_image(canvas, paint, counter)
    canvas._render_layer(paint, inside)
    paint = boundary_image(canvas, paint, inner)
    paint = boundary_image(canvas, paint, middle)
    canvas._render_layer(paint, outside)
    return boundary_image(canvas, paint, owner)


@pytest.mark.parametrize("style", ["plain", "odometer", "flip"])
@pytest.mark.parametrize("boundary", ["partial", "inverted", "empty"])
def test_nested_counter_matches_manual_scopes_and_settled_slots(style, boundary):
    canvas, placed = nested_counter_scene(style, boundary)
    animator = _SlideAnimator(canvas, {})
    node = animator._units[-1].parent_node
    geometry = node.origin, node.body_to_baked, node.pivot_box, node.source_size
    original = canvas.to_json()
    cache, count = canvas._ctx.measure_cache, len(canvas._ctx.measure_cache)
    frames = []
    for instant in (0, 0.349, 0.817, 1, 0.349):
        frame = animator.frame_at(instant)
        assert frame.tobytes() == nested_frame(canvas, placed, instant).tobytes()
        assert (node.origin, node.body_to_baked, node.pivot_box, node.source_size) == geometry
        assert canvas._ctx.measure_cache is cache and len(cache) == count
        assert canvas._ctx.motion_time is None
        frames.append(frame.tobytes())
    assert frames[1] == frames[-1]
    assert len(set(frames)) >= (1 if boundary == "empty" else 3)
    assert canvas.to_json() == original


def test_overlapping_backgrounds_are_masked_once_as_one_scope():
    canvas = Canvas(160, 120).null(id="root")
    counter = TextLayer(
        type="text",
        content="2",
        font=FONT,
        size=20,
        color="#FFFFFF",
        effects=[Background(color="#FF0000", padding=20)],
        value=AnimatedTextValue.model_validate({"from": 1, "to": 2, "duration": 1}),
    )
    static = counter.model_copy(
        update={"value": None, "effects": [Background(color="#0000FF", padding=20)]}
    )
    inner = GroupLayer(
        type="group",
        direction="row",
        children=[counter, static],
        mask=LayerMask(position=(0, 0), width=160, height=120, opacity=0.5),
    )
    canvas.group([inner], position=(40, 40), parent="root")
    image = canvas.render_frame(0.3)
    assert cast(tuple, image.getpixel((55, 40)))[3] == 128
    assert image.getchannel("A").getextrema() == (0, 128)


@pytest.mark.parametrize("style", ["plain", "odometer", "flip"])
def test_dynamic_ink_survives_empty_settled_scope_with_fixed_child_frame(style):
    canvas = Canvas(300, 180).null(id="root")
    counter = TextLayer(
        type="text",
        content="stale",
        font=FONT,
        size=40,
        align=Align.BOTTOM_RIGHT,
        value=AnimatedTextValue.model_validate(
            {"from": 888888, "to": 1, "duration": 1, "style": style}
        ),
    )
    inner = GroupLayer(
        type="group", children=[counter], clip=LayerClip(position=(30, 60), width=125, height=70)
    )
    canvas.group([inner], position=(180, 65), parent="root", id="group")
    canvas.shape("rectangle", (8, 12), 9, 7, "#00FF00", parent="group", id="child")
    animator = _SlideAnimator(canvas, {})
    node = animator._units[-2].parent_node
    assert node.image is None
    width, height = canvas._text.measure_text_rendered_size(freeze(counter))
    assert node.pivot_box == (0, 0, width, height)
    placed = counter.model_copy(update={"position": (180 + width, 65 + height), "content": "1"})
    child = animator._units[-1].parent_node
    initial = node.plan.sample(0)[id(child)][0]
    for time in (0, 0.1, 1, 0):
        paint = canvas._create_canvas()
        for fragment in canvas._text.counter_paint_layers(placed, time):
            canvas._text.render_text_layer(paint, fragment)
        expected = boundary_image(canvas, paint, inner)
        canvas._render_layer(
            expected,
            cast(ShapeLayer, canvas.layers[-1]).model_copy(
                update={"position": (188, 77), "parent": None}
            ),
        )
        assert animator.frame_at(time).tobytes() == expected.tobytes()
        assert node.plan.sample(time)[id(child)][0] == initial
    assert animator.frame_at(0).tobytes() != animator.frame_at(1).tobytes()


@pytest.mark.parametrize("style", ["plain", "odometer", "flip"])
def test_distant_shadow_reaches_leaf_clip_outside_logical_text_body(style):
    canvas = Canvas(420, 140).null(id="root")
    counter = TextLayer(
        type="text",
        content="2",
        font=FONT,
        size=24,
        value=AnimatedTextValue.model_validate({"from": 1, "to": 2, "duration": 1, "style": style}),
        effects=[Shadow(offset_x=-75, offset_y=0, blur_radius=2, color="#FF0000")],
        clip=LayerClip(position=(10, 10), width=285, height=120),
    )
    canvas.group([counter], position=(330, 45), parent="root")
    expected = canvas._create_canvas()
    placed = counter.model_copy(update={"position": (330, 45)})
    for fragment in canvas._text.counter_paint_layers(placed, 0.35):
        canvas._text.render_text_layer(expected, fragment)
    expected = boundary_image(canvas, expected, counter)
    assert expected.getbbox() is not None
    assert canvas.render_frame(0.35).tobytes() == expected.tobytes()


def test_tiny_displaced_flip_keeps_ink_without_a_viewport_probe(monkeypatch):
    canvas = Canvas(100, 100).null(id="root")
    counter = TextLayer(
        type="text",
        content="1",
        font=FONT,
        size=1,
        value=AnimatedTextValue.model_validate(
            {"from": 1, "to": 2, "duration": 1, "style": "flip", "easing": "linear"}
        ),
        clip=LayerClip(position=(0, 0), width=100, height=100),
    )
    canvas.group([counter], position=(40, 40), parent="root")
    original = _ParentCounterTextEngine.counter_paint_layers

    def no_probe(self, layer, time, *, viewport=None):
        assert viewport is None
        return original(self, layer, time)

    monkeypatch.setattr(_ParentCounterTextEngine, "counter_paint_layers", no_probe)
    expected = canvas._create_canvas()
    for fragment in canvas._text.counter_paint_layers(
        counter.model_copy(update={"position": (40, 40)}), 0.49
    ):
        canvas._text.render_text_layer(expected, fragment)
    assert expected.getbbox() is not None
    assert canvas.render_frame(0.49).tobytes() == expected.tobytes()


@pytest.mark.parametrize("quality", ["standard", "high"])
@pytest.mark.parametrize("style", ["plain", "odometer", "flip"])
def test_nested_scopes_match_independent_affine_reveal_color_and_buffer_padding(
    style, quality, monkeypatch
):
    canvas, placed = nested_counter_scene(style)
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
        NullLayer(
            type="null", id="a", position=(380, 140), animation=_oracle_motion(20, -0.8, 1.1)
        ),
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
            _oracle_matrix(380, 140, 20, -0.8, 1.1), _oracle_matrix(10, 5, -15, 1.2, 0.6)
        ),
        _oracle_matrix(5, 3, 10, 1, 1),
    )
    reference = nested_frame(canvas, placed, None, color="#FFFFFF")
    left, top, right, bottom = reference.getbbox()
    cx, cy = (left + right) / 2, (top + bottom) / 2
    animator = _SlideAnimator(canvas, {}, quality=quality)
    node = animator._units[-1].parent_node
    assert node.pivot_box == (left - 75, top - 55, right - left, bottom - top)
    scale = 2 if quality == "high" else 1
    times = (0.81, 0.23, 1, 0.47, 0.81)
    originals = []
    for instant in times:
        own = _oracle_product(
            _oracle_matrix(cx, cy, -10 + 30 * instant, 0.8 + 0.4 * instant, 1),
            _oracle_matrix(-cx, -cy, 0, 1, 1),
        )
        matrix = _oracle_product(ancestor, own)
        a, b, c, d, e, f = (value * scale for value in matrix)
        determinant = a * e - b * d
        assert determinant < 0 and abs(a * b + d * e) > 0.01
        image = nested_frame(
            canvas, placed, instant, interpolate_color("#3388DD", "#DD8833", instant)
        )
        opacity = 0.9 if instant == 1 else 0.3 + (0.9 - 0.3) * instant
        alpha = image.getchannel("A").point(lambda value, opacity=opacity: round(value * opacity))
        if instant < 1:
            cutoff = left + round((right - left) * (0.2 + 0.8 * instant)) + 1
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
        blurred = expected.copy()
        blurred.alpha_composite(warped)
        expected.alpha_composite(blurred.filter(ImageFilter.GaussianBlur((0.5 + instant) * scale)))
        if scale != 1:
            expected = expected.resize((canvas.width, canvas.height), Image.Resampling.LANCZOS)
        actual = animator.frame_at(instant)
        assert actual.tobytes() == expected.tobytes()
        originals.append(actual.tobytes())
    original_sample = node.render_sample

    def padded(time, color):
        image, offset = original_sample(time, color)
        extra = Image.new("RGBA", (image.width + 74, image.height + 58))
        extra.paste(image, (31, 19))
        return extra, (offset[0] - 31, offset[1] - 19)

    monkeypatch.setattr(node, "render_sample", padded)
    assert [animator.frame_at(instant).tobytes() for instant in times] == originals


def test_sample_context_restores_on_replay_exception(monkeypatch):
    canvas, _ = nested_counter_scene()
    animator = _SlideAnimator(canvas, {})
    node = animator._units[-1].parent_node
    cache = canvas._ctx.measure_cache
    canvas._ctx.motion_time = 7.5

    def fail(*_args, **_kwargs):
        raise RuntimeError("paint failed")

    monkeypatch.setattr(_ParentCounterTextEngine, "render_text_layer", fail)
    with pytest.raises(RuntimeError, match="paint failed"):
        node.render_sample(0.5, "#CCFF88")
    assert canvas._ctx.measure_cache is cache and canvas._ctx.motion_time == 7.5


def test_replay_helpers_and_scope_buffers_release_without_cyclic_collection(monkeypatch):
    canvas, _ = nested_counter_scene("odometer")
    group = cast(GroupLayer, canvas.layers[-1])
    group.children = [group.children[0].model_copy(deep=True) for _ in range(16)]
    # Repeated ids are irrelevant to this private rendering lifetime check.
    for middle in group.children:
        cast(
            TextLayer, cast(GroupLayer, cast(GroupLayer, middle).children[0]).children[0]
        ).id = None
    animator = _SlideAnimator(canvas, {})
    node = animator._units[-1].parent_node
    engines, images = [], []
    initialize = _ParentCounterTextEngine.__init__
    allocate = Image.Image._new

    def engine(self, *args, **kwargs):
        initialize(self, *args, **kwargs)
        engines.append(weakref.ref(self))

    def image(self, *args, **kwargs):
        result = allocate(self, *args, **kwargs)
        images.append(weakref.ref(result))
        return result

    monkeypatch.setattr(_ParentCounterTextEngine, "__init__", engine)
    monkeypatch.setattr(Image.Image, "_new", image)
    enabled = gc.isenabled()
    gc.disable()
    try:
        for instant in (0.7, 0.2, 0.9, 0.2):
            result, _ = node.render_sample(instant, None)
            assert len(engines) > 0 and all(reference() is None for reference in engines)
            assert all(reference() is None or reference() is result for reference in images)
            del result
            assert all(reference() is None for reference in images)
    finally:
        if enabled:
            gc.enable()


@pytest.mark.parametrize(
    "kind",
    [
        "video",
        "unknown",
        "root_stagger",
        "child_stagger",
        "zero_stagger",
        "one_stagger",
        "independent",
    ],
)
def test_new_admission_preserves_remaining_render_free_guards(monkeypatch, kind):
    canvas, _ = nested_counter_scene()
    group = cast(GroupLayer, canvas.layers[-1])
    counter = cast(
        TextLayer, cast(GroupLayer, cast(GroupLayer, group.children[0]).children[0]).children[0]
    )
    if kind == "video":
        group.children.append(
            cast(Any, VideoLayer.model_construct(type="video", path="unused.mp4"))
        )
    elif kind == "unknown":
        inner = cast(GroupLayer, cast(GroupLayer, group.children[0]).children[0])
        inner.children[0] = counter.model_copy(update={"value": object()})
    elif kind == "root_stagger":
        group.animation = AnimationSpec.rise(stagger=0.2, target="children")
    elif kind in {"child_stagger", "zero_stagger", "one_stagger"}:
        group.animation = motion(track(OpacityTrack, 0, 1))
        if kind == "one_stagger":
            counter.content = "1"
            counter.value = AnimatedTextValue.model_validate({"from": 1, "to": 2, "duration": 1})
        counter.animation = [
            AnimationSpec.rise(
                stagger=0 if kind == "zero_stagger" else 0.2,
                target="characters",
            )
        ]
    else:
        counter.animation = AnimationSpec.fade(duration=1)
    monkeypatch.setattr(canvas, "_render_layer", lambda *_a, **_k: pytest.fail("preflight painted"))
    assert parent_rendering_problem(canvas) is not None


@pytest.mark.parametrize("kind", ["chart", "qr"])
def test_root_override_suppresses_component_motion_but_retains_counter_clocks(kind):
    canvas, placed = nested_counter_scene()
    owner = cast(GroupLayer, canvas.layers[-1])
    middle = cast(GroupLayer, owner.children[0])
    inner = cast(GroupLayer, middle.children[0])
    counter = cast(TextLayer, inner.children[0])
    counter.animation = AnimationSpec.fade(duration=60, delay=20)
    component = (
        ChartLayer(
            type="chart",
            spec=BarChartSpec(data=[1, 3]),
            width=65,
            height=40,
            animation=AnimationSpec.bar_grow(duration=50, delay=30),
        )
        if kind == "chart"
        else QRCodeLayer(
            type="qr_code",
            data="counter",
            size=48,
            animation=AnimationSpec.qr_reveal(duration=50, delay=30),
        )
    )
    inner.children[1] = component
    assert "cannot animate descendants" in (parent_rendering_problem(canvas) or "")
    owner.animation = motion(track(OpacityTrack, 1, 1), duration=0.2)
    # Explicitly remove authored specs in a control; retain every value clock.
    reference = Canvas.from_json(canvas.to_json())
    reference_inner = cast(
        GroupLayer, cast(GroupLayer, cast(GroupLayer, reference.layers[-1]).children[0]).children[0]
    )
    cast(TextLayer, reference_inner.children[0]).animation = None
    cast(ChartLayer | QRCodeLayer, reference_inner.children[1]).animation = None
    animator = _SlideAnimator(canvas, {})
    assert animator.duration == 1
    frames = []
    for instant in (0, 0.35, 0.85, 1, 0.35):
        frame = animator.frame_at(instant)
        assert frame.tobytes() == reference.render_frame(instant).tobytes()
        frames.append(frame.tobytes())
    assert len(set(frames)) >= 3


@pytest.mark.parametrize("overridden", [False, True])
def test_new_nested_counter_admission_is_render_free(monkeypatch, overridden):
    canvas, _ = nested_counter_scene()
    if overridden:
        cast(GroupLayer, canvas.layers[-1]).animation = AnimationSpec.fade(duration=1)
    monkeypatch.setattr(canvas, "_render_layer", lambda *_a, **_k: pytest.fail("preflight painted"))
    monkeypatch.setattr(
        canvas._groups, "render_group_layer", lambda *_a, **_k: pytest.fail("preflight painted")
    )
    for target in ("raster", "video"):
        assert all(item.support == "full" for item in canvas.validate_export(target))
    for target in ("html", "pptx"):
        assert all(item.fallback == "static" for item in canvas.validate_export(target))


def test_static_and_root_only_counter_sources_keep_existing_paths(monkeypatch):
    canvas, _ = nested_counter_scene()
    frozen = Canvas(canvas.width, canvas.height, layers=[freeze(layer) for layer in canvas.layers])
    expected = frozen.render_frame(0.5).tobytes()
    monkeypatch.setattr(
        ParentNode,
        "_render_nested_counter_sample",
        lambda *_a, **_k: pytest.fail("new replay used"),
    )
    assert frozen.render_frame(0.5).tobytes() == expected
    group = cast(GroupLayer, canvas.layers[-1])
    counter = cast(
        TextLayer, cast(GroupLayer, cast(GroupLayer, group.children[0]).children[0]).children[0]
    )
    group.children = [counter.model_copy(update={"clip": None, "mask": None})]
    assert canvas.render_frame(0.5).getbbox() is not None
