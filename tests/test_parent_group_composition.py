"""A structural group's own boundary encloses its complete static local paint."""

from typing import Any, cast

import pytest
from PIL import Image
from quickthumb import (
    Align,
    Background,
    BlurTrack,
    Canvas,
    ClipProgressTrack,
    ColorTrack,
    GroupLayer,
    LayerClip,
    LayerMask,
    OpacityTrack,
    RotationTrack,
    ScaleXTrack,
    ScaleYTrack,
    Shadow,
    ShapeLayer,
    TextLayer,
    TextPart,
)
from quickthumb._diagnostic_rules import worst_tile_contrast
from quickthumb._export_video import _SlideAnimator
from quickthumb._measurements import BBox, measure_layers
from quickthumb._parent_render import (
    affine_fragment,
    multiply,
    parent_geometry,
    translate,
)

from tests.test_parent_composition import boundaries, linked
from tests.test_parent_counters import motion, track
from tests.test_parent_diagnostics import FONT, composite, setup


def children(nested=False):
    shape = ShapeLayer(
        type="shape",
        shape="rectangle",
        position=(0, 0),
        width=74,
        height=42,
        color="#CC7722",
        rotation=21,
        effects=[Shadow(color="#112233", offset_x=-8, offset_y=6, blur_radius=2)],
    )
    text = TextLayer(
        type="text",
        content="GROUP",
        font=FONT,
        size=24,
        color="#FFFFFF",
        rotation=-12,
        effects=[Background(color="#225588", padding=9)],
    )
    return [shape, GroupLayer(type="group", children=[text], padding=(5, 7)) if nested else text]


@pytest.mark.parametrize("direction,nested", [("row", False), ("column", False), ("row", True)])
@pytest.mark.parametrize("boundary", ["clip", "both", "invert0", "invert0.4", "invert1", "empty"])
def test_identity_group_boundary_keeps_layout_and_paint(direction, nested, boundary):
    canvas = Canvas(320, 220).group(
        children(nested),
        position=("50%", "50%"),
        align=Align.CENTER,
        direction=direction,
        item_align="center",
        gap=11,
        padding=(5, 9, 12, 7),
        **boundaries(boundary),
    )
    parented = linked(canvas)
    before = parented.to_json()
    assert parented._render_to_image().tobytes() == canvas._render_to_image().tobytes()
    for quality in ("standard", "high"):
        animator = _SlideAnimator(parented, {}, quality=quality)
        expected = _SlideAnimator(canvas, {}, quality=quality).frame_at(0.5)
        assert animator.frame_at(0.5).tobytes() == expected.tobytes()
    assert parented.to_json() == before


@pytest.mark.parametrize("quality", ["standard", "high"])
def test_group_own_motion_recolors_and_composes_once_with_reverse_seeks(quality):
    canvas = Canvas(320, 220).group(
        children(True),
        position=(70, 65),
        direction="row",
        gap=8,
        padding=9,
        clip=LayerClip(position=(85, 55), width=120, height=100, border_radius=12),
        mask=LayerMask(shape="ellipse", position=(75, 50), width=145, height=110, opacity=0.6),
        animation=motion(
            track(RotationTrack, -12, 25),
            track(ScaleXTrack, 0.8, 1.4),
            track(ScaleYTrack, 1.2, 0.7),
            track(OpacityTrack, 0.2, 0.8),
            track(ClipProgressTrack, 0.2, 1),
            track(BlurTrack, 0, 2),
            track(ColorTrack, "#DD6622", "#3366BB"),
        ),
    )
    parented = linked(canvas)
    actual = _SlideAnimator(parented, {}, quality=quality)
    expected = _SlideAnimator(canvas, {}, quality=quality)
    for time in (0, 0.8, 0.3, 1, 0.8):
        assert actual.frame_at(time).tobytes() == expected.frame_at(time).tobytes()


@pytest.mark.parametrize("empty", [False, True])
def test_group_boundary_keeps_full_parent_frame_and_external_child(empty):
    canvas = (
        Canvas(300, 240)
        .null((75, 50), id="root", rotation=17)
        .group(
            children(True),
            position=(15, 10),
            direction="row",
            padding=15,
            parent="root",
            id="group",
            clip=LayerClip(position=(500, 500) if empty else (30, 30), width=30, height=20),
            animation=motion(track(OpacityTrack, 0, 0), track(ClipProgressTrack, 0, 0)),
        )
        .shape("rectangle", (170, 50), 11, 9, "#00FF00", parent="group")
    )
    group = cast(GroupLayer, canvas.layers[1])
    geometry = parent_geometry(canvas, group)
    bare = parent_geometry(canvas, group.model_copy(update={"clip": None}))
    assert (geometry.origin, geometry.body_size, geometry.body_to_baked) == (
        bare.origin,
        bare.body_size,
        bare.body_to_baked,
    )
    animator = _SlideAnimator(canvas, {})
    node = animator._units[-1].parent_node
    expected = Image.new("RGBA", (300, 240))
    paint = animator._sample_parents(0.5)[id(node)][0]
    fragment = affine_fragment(
        node.image, multiply(paint, translate(-node.padding, -node.padding)), expected.size
    )
    assert fragment is not None
    expected.alpha_composite(*fragment)
    assert animator.frame_at(0.5).tobytes() == expected.tobytes()
    owner = node.plan.nodes[id(group)]
    if empty:
        assert owner.image is None and owner.pivot_box == (0, 0, *geometry.body_size)


@pytest.mark.parametrize("quality", ["standard", "high"])
def test_composed_group_under_three_levels_retains_shear_and_reflection(quality):
    canvas = (
        Canvas(380, 260)
        .null(
            (180, 120),
            id="a",
            animation=motion(
                track(RotationTrack, 0, 30), track(ScaleXTrack, -1, -1.5), track(OpacityTrack, 0, 0)
            ),
        )
        .null(
            (10, 5),
            id="b",
            parent="a",
            rotation=-17,
            animation=motion(track(ScaleYTrack, 1, 0.5)),
        )
        .null((15, 10), id="c", parent="b", rotation=23)
        .group(
            children(True),
            position=(-40, -25),
            parent="c",
            direction="column",
            clip=LayerClip(position=(-45, -20), width=110, height=100, border_radius=10),
            mask=LayerMask(position=(-30, -15), width=75, height=80, opacity=0.4, invert=True),
        )
    )
    animator = _SlideAnimator(canvas, {}, quality=quality)
    node = animator._units[-1].parent_node
    original = canvas.to_json()
    for time in (0.8, 0.2, 1, 0, 0.8):
        samples = animator._sample_parents(time)
        matrix = samples[id(node)][0]
        assert matrix[0] * matrix[4] - matrix[1] * matrix[3] < 0
        if time:
            assert abs(matrix[0] * matrix[1] + matrix[3] * matrix[4]) > 0.01
        assert (
            animator.frame_at(time).tobytes()
            == _SlideAnimator(canvas, {}, quality=quality).frame_at(time).tobytes()
        )
    assert canvas.to_json() == original


def test_group_inspection_intersects_only_aggregate_then_maps_world_boxes(monkeypatch):
    canvas = (
        Canvas(260, 200)
        .null((130, 50), id="root", rotation=90)
        .group(
            [
                ShapeLayer(
                    type="shape",
                    shape="rectangle",
                    position=(0, 0),
                    width=80,
                    height=30,
                    color="#FFFFFF",
                )
            ],
            position=(10, 20),
            padding=10,
            parent="root",
            id="group",
            clip=LayerClip(position=(30, 35), width=20, height=10),
        )
    )
    monkeypatch.setattr(canvas, "_render_layer", lambda *_: pytest.fail("inspection painted"))
    measured = measure_layers(canvas)[1]
    assert measured.bbox == BBox(85, 80, 10, 20)
    assert measured.metadata["layout_bbox"] == BBox(60, 60, 50, 100)
    assert measured.children[0].bbox == BBox(70, 70, 30, 80)


def test_structural_alpha_and_running_composite_use_group_boundary_once():
    canvas = (
        Canvas(260, 200)
        .null((65, 30), id="root", rotation=19)
        .group(
            children(True),
            position=(0, 0),
            direction="row",
            parent="root",
            id="group",
            clip=LayerClip(position=(20, 5), width=100, height=90),
            mask=LayerMask(position=(10, 0), width=140, height=100, opacity=0.4),
        )
    )
    sources, measured = setup(canvas)
    assert composite(canvas, sources, measured).tobytes() == canvas._render_to_image().tobytes()
    for item in (measured[-1], *measured[-1].children, measured[-1].children[1].children[0]):
        occurrence = sources.occurrences[item.layer_id]
        raw = Image.new("RGBA", occurrence.root.node.source_size)
        for operation in (
            occurrence.root.operations[occurrence.start : occurrence.end]
            if not occurrence.top
            else occurrence.root.operations
        ):
            sources._paint_operation(raw, operation)
        composed = occurrence.root.node.compose_source(raw)
        world = Image.new("RGBA", (260, 200))
        fragment = affine_fragment(composed, occurrence.root.matrix, world.size)
        if fragment:
            world.alpha_composite(*fragment)
        box = item.bbox
        assert box is not None
        assert (
            sources.alpha(item).tobytes()
            == world.getchannel("A").crop((box.x, box.y, box.right, box.bottom)).tobytes()
        )
    assert canvas._render_to_image(debug=True).size == (260, 200)
    canvas.diagnose()


@pytest.mark.parametrize("invert", [False, True])
@pytest.mark.parametrize("color", ["#000000", "#00000080"])
@pytest.mark.parametrize("opacity", [0.4, 1])
@pytest.mark.parametrize("rich", [False, True])
def test_composed_group_text_matches_actual_solid_glyphs_with_prefix_and_background(
    invert, color, opacity, rich
):
    background = Background(color="#EEFFFF", padding=8)
    content = [TextPart(text="MMMM", color=color, effects=[background])] if rich else "MMMM"
    canvas = (
        Canvas(400, 220)
        .background(color="#226699")
        .null((20, 10), id="root")
        .group(
            [
                TextLayer(
                    type="text",
                    content="P",
                    font=FONT,
                    size=40,
                    color="#DD8855",
                    effects=[Background(color="#FFDD88", padding=100)],
                ),
                GroupLayer(
                    type="group",
                    children=[
                        TextLayer(
                            type="text",
                            content=content,
                            font=FONT,
                            size=45,
                            color=color,
                            opacity=opacity,
                            effects=[] if rich else [background],
                        )
                    ],
                ),
            ],
            direction="row",
            gap=5,
            position=(30, 55),
            parent="root",
            id="group",
            mask=LayerMask(position=(10, 0), width=340, height=200, opacity=0.6, invert=invert),
        )
    )
    sources, measured = setup(canvas)
    text = measured[-1].children[1].children[0]
    occurrence = sources.occurrences[text.layer_id]
    running = canvas._create_canvas()
    canvas._render_layer(running, canvas.layers[0])
    backing, foreground = sources.text_images(running, text)
    source = occurrence.text
    assert source is not None
    content = source.content
    if isinstance(content, list):
        content = [part.model_copy(update={"color": "#FFFFFF", "effects": []}) for part in content]
    geometric = source.model_copy(
        update={"content": content, "color": "#FFFFFF", "opacity": 1, "effects": []}
    )
    coverage = Image.new("RGBA", occurrence.root.node.source_size)
    canvas._text.render_text_layer(coverage, geometric, staging_reference=source)
    world = Image.new("RGBA", running.size)
    sources._composite_surface(world, coverage, occurrence.root)
    actual = Image.new("RGBA", running.size, "white")
    actual.alpha_composite(canvas._render_to_image())
    points = [
        (x, y)
        for y in range(220)
        for x in range(400)
        if cast(tuple[int, int, int, int], world.getpixel((x, y)))[3] == 255
        and cast(tuple[int, int, int, int], foreground.getpixel((x, y)))[3]
    ]
    assert len(points) > 20
    for point in points:
        assert (
            cast(tuple[int, int, int, int], foreground.getpixel(point))[:3]
            == cast(tuple[int, int, int, int], actual.getpixel(point))[:3]
        )
    before = sources._prefix(occurrence).tobytes()
    for _ in range(2):
        repeated = sources.text_images(running, text)
        assert repeated[0].tobytes() == backing.tobytes()
        assert repeated[1].tobytes() == foreground.tobytes()
        assert sources._prefix(occurrence).tobytes() == before


@pytest.mark.parametrize("boundary", ["empty", "zero", "invert_zero"])
def test_group_mask_preserves_thin_text_or_removes_all_samples(boundary):
    options: dict[str, Any] = (
        {"clip": LayerClip(position=(500, 500), width=20, height=20)}
        if boundary == "empty"
        else {
            "mask": LayerMask(
                position=(20, 20), width=3, height=50, opacity=0, invert=boundary == "invert_zero"
            )
        }
    )
    canvas = (
        Canvas(220, 130)
        .background(color="#FFFFFF")
        .null((60, 40), id="root", rotation=23)
        .group(
            [TextLayer(type="text", content="thin mini lill", font=FONT, size=10, color="#DDDDDD")],
            position=(0, 0),
            parent="root",
            **options,
        )
    )
    sources, measured = setup(canvas)
    running = canvas._create_canvas()
    canvas._render_layer(running, canvas.layers[0])
    backing, foreground = sources.text_images(running, measured[-1].children[0])
    contrast = worst_tile_contrast(backing, foreground, BBox(0, 0, 220, 130), tile_size=220)
    if boundary == "invert_zero":
        assert contrast is not None and contrast.contrast < 2
    else:
        assert foreground.getbbox() is None and contrast is None


def test_clipped_away_group_does_not_overlap_lower_layer():
    canvas = (
        Canvas(200, 120)
        .shape("rectangle", (90, 40), 20, 20, "#FF0000", id="lower")
        .null(id="root")
        .group(
            [
                ShapeLayer(
                    type="shape",
                    shape="rectangle",
                    position=(0, 0),
                    width=100,
                    height=60,
                    color="#FFFFFF",
                )
            ],
            position=(40, 20),
            parent="root",
            clip=LayerClip(position=(40, 20), width=20, height=60),
        )
    )
    assert not any(
        item.code in {"layer-hidden", "layer-overlap"} for item in canvas.diagnose().findings
    )


@pytest.mark.parametrize(
    "kind", ["counter_stagger", "independent", "descendant", "nested_mask", "backdrop"]
)
def test_composed_group_unsupported_combinations_are_guarded_without_rendering(monkeypatch, kind):
    from quickthumb import AnimatedTextValue, AnimationSpec, BackdropBlur, ExportPolicy
    from quickthumb.errors import RenderingError

    child = TextLayer(
        type="text",
        content="12",
        font=FONT,
        size=20,
        value=AnimatedTextValue.model_validate({"from": 1, "to": 12, "duration": 1}),
    )
    animation = None
    expected = (
        "static text or group"
        if kind == "counter_stagger"
        else "independent"
        if kind == "independent"
        else "descendant boundaries require static content"
        if kind in {"descendant", "nested_mask"}
        else "backdrop"
    )
    if kind == "counter_stagger":
        animation = AnimationSpec.rise(stagger=0.2, target="children")
    elif kind == "independent":
        child.animation = motion(track(RotationTrack, 0, 30))
    elif kind == "descendant":
        child.clip = LayerClip(position=(0, 0), width=20, height=20)
    children = (
        [
            GroupLayer(
                type="group", children=[child], mask=LayerMask(position=(0, 0), width=80, height=40)
            )
        ]
        if kind == "nested_mask"
        else [child]
    )
    canvas = (
        Canvas(180, 120)
        .null(id="root")
        .group(
            children,
            parent="root",
            clip=LayerClip(position=(0, 0), width=100, height=80),
            animation=animation,
        )
    )
    if kind == "backdrop":
        canvas.shape("rectangle", (0, 0), 100, 80, "#FFFFFF", effects=[BackdropBlur(radius=3)])
    monkeypatch.setattr(canvas, "_render_layer", lambda *_: pytest.fail("preflight painted"))
    for target in ("raster", "video", "html", "pptx"):
        with pytest.raises(RenderingError, match=expected):
            canvas.validate_export(target, ExportPolicy(unsupported_motion="error"))


@pytest.mark.parametrize("counter", [False, True])
def test_composed_group_animation_still_overrides_nested_descendant_animation(counter):
    from quickthumb import AnimatedTextValue

    child = TextLayer(
        type="text",
        content="STILL",
        font=FONT,
        size=30,
        color="#FFFFFF",
        animation=motion(track(RotationTrack, 0, 180)),
        value=AnimatedTextValue.model_validate({"from": -100, "to": 12, "duration": 1})
        if counter
        else None,
    )
    canvas = (
        Canvas(220, 150)
        .null((25, 20), id="root")
        .group(
            [GroupLayer(type="group", children=[child])],
            position=(15, 15),
            parent="root",
            mask=LayerMask(position=(10, 10), width=140, height=80, opacity=0.5),
            animation=motion(track(OpacityTrack, 0.2, 1)),
        )
    )
    original = canvas.to_json()
    reference = Canvas.from_json(original)
    cast(
        TextLayer, cast(GroupLayer, cast(GroupLayer, reference.layers[-1]).children[0]).children[0]
    ).animation = None
    for time in (0, 0.8, 0.3, 1, 0.8):
        assert canvas.render_frame(time).tobytes() == reference.render_frame(time).tobytes()
    assert canvas.to_json() == original


@pytest.mark.parametrize("size,rotation", [(8, 23), (10, 45)])
@pytest.mark.parametrize("color", ["#000000", "#DDDDDD"])
@pytest.mark.parametrize("invert_zero", [False, True])
def test_identity_group_boundary_keeps_thin_rotated_text_contrast(
    size, rotation, color, invert_zero
):
    canvas = (
        Canvas(260, 140)
        .background(color="#FFFFFF")
        .null((70, 50), id="root", rotation=rotation)
        .group(
            [
                TextLayer(
                    type="text", content="thin mini lill ill", font=FONT, size=size, color=color
                )
            ],
            position=(0, 0),
            parent="root",
            clip=LayerClip(position=(-100, -100), width=500, height=400),
            mask=LayerMask(position=(0, 0), width=3, height=80, invert=True, opacity=0)
            if invert_zero
            else None,
        )
    )
    findings = [item for item in canvas.diagnose().findings if item.code == "low-contrast"]
    assert bool(findings) is (color == "#DDDDDD")


@pytest.mark.parametrize("invert", [False, True])
def test_group_partial_mask_contrast_keeps_inside_and_outside_treatment(invert):
    canvas = (
        Canvas(400, 160)
        .background(color="#FFFFFF")
        .null((20, 0), id="root")
        .group(
            [TextLayer(type="text", content="MMMMMMMM", font=FONT, size=45, color="#000000")],
            position=(20, 35),
            parent="root",
            mask=LayerMask(
                position=(20, 20),
                width=120,
                height=100,
                opacity=0.9 if invert else 0.1,
                invert=invert,
            ),
        )
    )
    sources, measured = setup(canvas)
    running = canvas._create_canvas()
    canvas._render_layer(running, canvas.layers[0])
    backing, foreground = sources.text_images(running, measured[-1].children[0])
    inside = worst_tile_contrast(backing, foreground, BBox(50, 40, 90, 55), tile_size=90)
    assert inside is not None and inside.contrast < 1.5
    outside = worst_tile_contrast(backing, foreground, BBox(165, 40, 140, 55), tile_size=140)
    if invert:
        assert outside is not None and outside.contrast > 15
    else:
        assert outside is None
