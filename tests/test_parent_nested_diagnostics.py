"""Nested parent diagnostics replay ordinary isolation and sibling order."""

import gc
import weakref
from typing import Any, cast

import pytest
from PIL import ImageChops
from quickthumb import Background, Canvas, GroupLayer, LayerClip, LayerMask, TextLayer, TextPart
from quickthumb._composition import _mask_alpha
from quickthumb._diagnostic_rules import visible_leaf_layers, worst_tile_contrast
from quickthumb._measurements import BBox

from tests.test_parent_diagnostics import FONT, composite, setup


def prefix(color):
    return TextLayer(
        type="text",
        content="P",
        font=FONT,
        size=12,
        color="#996633",
        effects=[Background(color=color, padding=80)],
    )


def nested_scene(*, rich=False, leaf=False, invert=False, rotation=0, root_boundary=True):
    background = Background(color="#EEDDFF", padding=8)
    target = TextLayer(
        type="text",
        content=[TextPart(text="MMMM", color="#102030B0", effects=[background])]
        if rich
        else "MMMM",
        font=FONT,
        size=34,
        color="#102030B0",
        opacity=0.8,
        effects=[] if rich else [background],
        mask=LayerMask(position=(70, 40), width=160, height=110, opacity=0.7, invert=invert)
        if leaf
        else None,
    )
    inner = GroupLayer(
        type="group",
        direction="row",
        gap=4,
        children=[prefix("#88CCEE"), target],
        mask=LayerMask(position=(70, 35), width=170, height=140, opacity=0.45, invert=invert),
    )
    # The wrapper is deliberately uncomposed and must not create an isolation.
    middle = GroupLayer(type="group", direction="row", children=[inner], padding=(2, 3))
    outer = GroupLayer(
        type="group",
        direction="row",
        gap=5,
        children=[prefix("#EE9966"), middle],
        clip=LayerClip(position=(15, 30), width=260, height=130, border_radius=9),
        mask=LayerMask(position=(25, 20), width=255, height=150, opacity=0.65),
    )
    return (
        Canvas(360, 230)
        .background(color="#226699")
        .null((0, 0), id="root", rotation=rotation)
        .group(
            [prefix("#66DD88"), outer],
            direction="row",
            position=(30, 60),
            parent="root",
            mask=LayerMask(position=(5, 15), width=300, height=180, opacity=0.8)
            if root_boundary
            else None,
        )
    )


def target_measurement(measured):
    return measured[-1].children[1].children[1].children[0].children[1]


@pytest.mark.parametrize(
    "rich,leaf,invert,rotation,root_boundary",
    [
        (False, False, False, 0, True),
        (True, False, True, 0, True),
        (False, True, False, 0, False),
        (True, True, True, 0, False),
        (False, True, True, 17, True),
        (True, True, False, 17, True),
    ],
)
def test_nested_text_replays_exact_backing_and_solid_glyph_pixels(
    monkeypatch, rich, leaf, invert, rotation, root_boundary
):
    canvas = nested_scene(
        rich=rich, leaf=leaf, invert=invert, rotation=rotation, root_boundary=root_boundary
    )
    before = canvas.to_json()
    sources, measured = setup(canvas)
    target = target_measurement(measured)
    occurrence = sources.occurrences[target.layer_id]
    assert len(occurrence.path) == 3  # root, outer, inner; uncomposed wrapper is flat
    running = canvas._create_canvas()
    canvas._render_layer(running, canvas.layers[0])
    backing, foreground = sources.text_images(running, target)
    actual = canvas._render_to_image()
    assert composite(canvas, sources, measured).tobytes() == actual.tobytes()
    if rotation == 0:
        ordinary = Canvas.from_json(before)
        cast(GroupLayer, ordinary.layers[-1]).parent = None
        assert actual.tobytes() == ordinary._render_to_image().tobytes()

    source = occurrence.text
    assert source is not None
    content = source.content
    if isinstance(content, list):
        content = [part.model_copy(update={"effects": []}) for part in content]
    coverage, _ = sources._text_coverage(
        source.model_copy(update={"content": content, "effects": [], "auto_scale": False}),
        source,
        occurrence,
    )
    points = [
        (x, y)
        for y in range(canvas.height)
        for x in range(canvas.width)
        if coverage.getpixel((x, y)) == 255
        and cast(tuple[int, int, int, int], foreground.getpixel((x, y)))[3]
    ]
    assert len(points) > 20
    for point in points:
        assert (
            cast(tuple[int, int, int, int], foreground.getpixel(point))[:3]
            == cast(tuple[int, int, int, int], actual.getpixel(point))[:3]
        )

    draw_text = canvas._text._draw_text

    def skip_target(draw, text, *args, **kwargs):
        if text != "MMMM":
            draw_text(draw, text, *args, **kwargs)

    monkeypatch.setattr(canvas._text, "_draw_text", skip_target)
    assert backing.tobytes() == canvas._render_to_image().tobytes()
    if rotation == 0:
        ordinary_draw = ordinary._text._draw_text

        def skip_ordinary_target(draw, text, *args, **kwargs):
            if text != "MMMM":
                ordinary_draw(draw, text, *args, **kwargs)

        monkeypatch.setattr(ordinary._text, "_draw_text", skip_ordinary_target)
        assert backing.tobytes() == ordinary._render_to_image().tobytes()
    assert canvas.to_json() == before


def silence(layer):
    if isinstance(layer, GroupLayer):
        for child in layer.children:
            silence(child)
    else:
        layer.opacity = 0


@pytest.mark.parametrize("path", [(1,), (1, 1), (1, 1, 0), (1, 1, 0, 1)])
def test_nested_alpha_has_all_enclosing_boundaries_without_sibling_prefixes(path):
    canvas = nested_scene(leaf=True, invert=True, rotation=19)
    sources, measured = setup(canvas)
    target = measured[-1]
    reference = Canvas.from_json(canvas.to_json())
    layer = cast(GroupLayer, reference.layers[-1])
    for index in path:
        target = target.children[index]
        for sibling_index, sibling in enumerate(layer.children):
            if sibling_index != index:
                silence(sibling)
        layer = cast(GroupLayer, layer.children[index])
    reference.layers = reference.layers[1:]
    world = reference._render_to_image().getchannel("A")
    box = target.bbox
    assert box is not None
    assert (
        sources.alpha(target).tobytes()
        == world.crop((box.x, box.y, box.right, box.bottom)).tobytes()
    )


def test_prefix_cache_is_depth_bounded_released_and_rebuilt_on_backward_observations():
    groups = [
        GroupLayer(
            type="group",
            direction="row",
            children=[prefix("#88CCEE"), TextLayer(type="text", content="T", font=FONT, size=12)],
            mask=LayerMask(position=(0, 0), width=500, height=500, opacity=0.5),
        )
        for _ in range(16)
    ]
    canvas = Canvas(220, 420).null(id="root").group(groups, parent="root")
    sources, measured = setup(canvas)
    texts = [group.children[-1] for group in measured[-1].children]
    scopes = [sources.occurrences[text.layer_id].path[-1][0] for text in texts]
    running = canvas._create_canvas()
    first = sources.text_images(running, texts[0])
    prefixes = [
        scope.prefix.tobytes() for scope in sources._active_path if scope.prefix is not None
    ]
    warm = sources.text_images(running, texts[0])
    assert [image.tobytes() for image in warm] == [image.tobytes() for image in first]
    assert prefixes == [
        scope.prefix.tobytes() for scope in sources._active_path if scope.prefix is not None
    ]
    for index, text in enumerate(texts):
        sources.text_images(running, text)
        assert sum(scope.prefix is not None for scope in scopes) == 1
        assert scopes[index].prefix is not None
        assert len(sources._active_path) == 2
    replay = sources.text_images(running, texts[0])
    assert [image.tobytes() for image in replay] == [image.tobytes() for image in first]
    sources.alpha(measured[-1])
    assert all(scope.prefix is None for scope in scopes)


def test_diagnostic_sources_and_prefix_pixels_release_without_cyclic_collection():
    # Disable collection before decoration so a cycle cannot disappear by chance
    # during subsequent rendering. Preserve the caller's original GC setting.
    enabled = gc.isenabled()
    gc.disable()
    try:
        canvas = nested_scene()
        sources, measured = setup(canvas)
        target = target_measurement(measured)
        sources.text_images(canvas._create_canvas(), target)
        occurrence = sources.occurrences[target.layer_id]
        references = [weakref.ref(sources)]
        references.extend(weakref.ref(scope) for scope, _ in occurrence.path)
        references.extend(
            weakref.ref(scope.prefix) for scope, _ in occurrence.path if scope.prefix is not None
        )
        assert len(references) == 7  # sources, three scopes, three cached images
        del occurrence, sources
        assert all(reference() is None for reference in references)
    finally:
        if enabled:
            gc.enable()


def test_nested_composed_group_is_atomic_for_occlusion_and_children_keep_layout_boxes():
    canvas = nested_scene(root_boundary=False)
    sources, measured = setup(canvas)
    leaves = list(visible_leaf_layers(measured[-1:]))
    outer = measured[-1].children[1]
    assert [item.layer_id for item in leaves] == [measured[-1].children[0].layer_id, outer.layer_id]
    target = target_measurement(measured)
    box = target.bbox
    assert box is not None
    blank = canvas._create_canvas()
    sources.composite(blank, target)
    pixels = blank.getchannel("A").crop((box.x, box.y, box.right, box.bottom))
    assert ImageChops.difference(pixels, sources.alpha(target)).getbbox() is None
    # A fully clipped parent never clips descendant inspection/layout geometry.
    outer_layer = cast(GroupLayer, cast(GroupLayer, canvas.layers[-1]).children[1])
    outer_layer.clip = LayerClip(position=(500, 500), width=10, height=10)
    changed, changed_measured = setup(canvas)
    child = target_measurement(changed_measured)
    assert child.bbox == box
    assert changed.alpha(child).getbbox() is None
    canvas.diagnose()


@pytest.mark.parametrize("level", range(4))
def test_text_sampling_excludes_antialiased_edges_at_every_scope_and_the_leaf(level):
    canvas = nested_scene(leaf=True, invert=True)
    root = cast(GroupLayer, canvas.layers[-1])
    outer = cast(GroupLayer, root.children[1])
    wrapper = cast(GroupLayer, outer.children[1])
    inner = cast(GroupLayer, wrapper.children[0])
    leaf = cast(TextLayer, inner.children[1])
    owners = [root, outer, inner, leaf]
    for owner in owners:
        owner.clip = None
        owner.mask = LayerMask(position=(0, 0), width=10, height=10, opacity=0, invert=True)
    boundary = LayerMask(
        shape="ellipse", position=(85, 52), width=80, height=40, opacity=0.6, invert=True
    )
    owners[level].mask = boundary
    sources, measured = setup(canvas)
    target = target_measurement(measured)
    running = canvas._create_canvas()
    canvas._render_layer(running, canvas.layers[0])
    _, foreground = sources.text_images(running, target)
    occurrence = sources.occurrences[target.layer_id]
    source = occurrence.text
    assert source is not None
    coverage, safe = sources._text_coverage(
        source.model_copy(update={"effects": [], "auto_scale": False}), source, occurrence
    )
    edge = _mask_alpha(canvas._ctx, running.size, boundary.model_copy(update={"opacity": 1}))
    points = [
        (x, y)
        for y in range(canvas.height)
        for x in range(canvas.width)
        if 12 < cast(int, edge.getpixel((x, y))) < 243
        and cast(int, coverage.getpixel((x, y))) >= 64
    ]
    assert len(points) > 3
    for point in points:
        assert safe.getpixel(point) == 0
        assert cast(tuple[int, int, int, int], foreground.getpixel(point))[3] == 0


@pytest.mark.parametrize("boundary", ["empty", "zero", "invert_zero", "partial"])
def test_nested_thin_text_keeps_glyph_normalization_and_partial_inverted_attenuation(boundary):
    options: dict[str, Any] = (
        {"clip": LayerClip(position=(500, 500), width=10, height=10)}
        if boundary == "empty"
        else {
            "mask": LayerMask(
                position=(0, 0),
                width=35,
                height=140,
                opacity=0.9 if boundary == "partial" else 0,
                invert=boundary in {"partial", "invert_zero"},
            )
        }
    )
    canvas = Canvas(260, 150).background(color="#FFFFFF").null((60, 40), id="root", rotation=23)
    canvas.group(
        [
            GroupLayer(
                type="group",
                children=[TextLayer(type="text", content="thin mini lill", font=FONT, size=10)],
                **options,
            )
        ],
        position=(0, 0),
        parent="root",
        clip=LayerClip(position=(-100, -100), width=500, height=400),
    )
    sources, measured = setup(canvas)
    running = canvas._create_canvas()
    canvas._render_layer(running, canvas.layers[0])
    backing, foreground = sources.text_images(running, measured[-1].children[0].children[0])
    contrast = worst_tile_contrast(backing, foreground, BBox(0, 0, 260, 150), tile_size=260)
    if boundary in {"empty", "zero"}:
        assert contrast is None and foreground.getbbox() is None
    elif boundary == "invert_zero":
        assert contrast is not None and contrast.contrast > 15
    else:
        assert contrast is not None and contrast.contrast < 1.5
