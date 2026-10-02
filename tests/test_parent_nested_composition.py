"""Static structural boundaries share the top-level group's authored plane."""

import math
from typing import cast

import pytest
from PIL import Image
from quickthumb import (
    Align,
    AnimatedTextValue,
    AnimationSpec,
    Background,
    Canvas,
    ClipProgressTrack,
    ColorTrack,
    ExportPolicy,
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
)
from quickthumb._export_video import _SlideAnimator
from quickthumb._measurements import measure_layers
from quickthumb._parent_render import ParentRenderPlan, affine_fragment, multiply, parent_geometry
from quickthumb.errors import RenderingError

from tests.test_parent_composition import linked
from tests.test_parent_counters import motion, track
from tests.test_parent_diagnostics import FONT


def nested_scene(invert=False, own=True, empty=False):
    """Mix isolated leaves/groups and uncomposed groups in three layout levels."""
    shape = ShapeLayer(
        type="shape",
        shape="rectangle",
        position=(0, 0),
        width=85,
        height=38,
        color="#EF8833",
        rotation=11,
        effects=[Shadow(color="#112233", offset_x=-5, offset_y=4, blur_radius=2)],
        clip=LayerClip(position=("26%", "24%"), width=90, height=80, align=Align.CENTER),
    )
    text = TextLayer(
        type="text",
        content="NESTED",
        font=FONT,
        size=30,
        color="#FFFFFF",
        effects=[Background(color="#224466", padding=12)],
        mask=LayerMask(position=("29%", "45%"), width=64, height=80, opacity=0.45, invert=invert),
    )
    inner = GroupLayer(
        type="group",
        children=[GroupLayer(type="group", children=[text], padding=(3, 9))],
        padding=(4, 6),
        clip=LayerClip(position=("42%", "52%"), width=155, height=80, align=Align.CENTER),
        mask=LayerMask(
            shape="ellipse", position=(72, 63), width=165, height=105, opacity=0.7, invert=invert
        ),
    )
    middle = GroupLayer(
        type="group",
        children=[shape, inner],
        gap=5,
        padding=7,
        mask=LayerMask(
            position=(500, 500) if empty else ("18%", "18%"),
            width=160,
            height=155,
            opacity=0.6,
        ),
    )
    return Canvas(320, 240).group(
        [middle],
        position=("15%", "10%"),
        padding=(5, 11),
        id="group",
        clip=LayerClip(position=(45, 25), width=210, height=175, border_radius=14) if own else None,
        mask=LayerMask(position=(40, 20), width=220, height=185, opacity=0.8) if own else None,
    )


@pytest.mark.parametrize("invert", [False, True])
@pytest.mark.parametrize("own", [False, True])
@pytest.mark.parametrize("empty", [False, True])
def test_identity_nested_boundaries_match_ordinary_pixels(invert, own, empty):
    ordinary = nested_scene(invert, own, empty)
    parented = linked(ordinary)
    before = parented.to_json()
    expected = ordinary._render_to_image()
    assert parented._render_to_image().tobytes() == expected.tobytes()
    assert (expected.getbbox() is None) is empty
    for quality in ("standard", "high"):
        animator = _SlideAnimator(parented, {}, quality=quality)
        assert (
            animator.frame_at(0.5).tobytes()
            == _SlideAnimator(ordinary, {}, quality=quality).frame_at(0.5).tobytes()
        )
    assert parented.to_json() == before


def test_original_percentages_and_align_are_rebased_once_for_every_boundary():
    canvas = linked(nested_scene(True))
    node = ParentRenderPlan(canvas).nodes[id(canvas.layers[-1])]
    offset = (node.padding - node.origin[0], node.padding - node.origin[1])

    def visit(original, prepared):
        for name in ("clip", "mask"):
            boundary = getattr(original, name, None)
            if boundary is None:
                continue
            resolved = getattr(prepared, name)
            expected = tuple(
                int(float(value[:-1]) * extent / 100) if isinstance(value, str) else value
                for value, extent in zip(
                    boundary.position, (canvas.width, canvas.height), strict=True
                )
            )
            assert resolved.position == tuple(a + b for a, b in zip(expected, offset, strict=True))
            assert resolved.align == boundary.align
        for child, source in zip(
            getattr(original, "children", ()), getattr(prepared, "children", ()), strict=True
        ):
            visit(child, source)

    visit(canvas.layers[-1], node.source)


def _rotation(degrees):
    angle = math.radians(degrees)
    return (math.cos(angle), -math.sin(angle), 0, math.sin(angle), math.cos(angle), 0)


@pytest.mark.parametrize("time", [0, 0.4, 1])
def test_nested_composite_uses_one_full_affine_warp_of_ordinary_source(time):
    ordinary = nested_scene(invert=True)
    source = ordinary._render_to_image()
    canvas = (
        Canvas(320, 240)
        .null(
            (285, 15),
            id="root",
            animation=motion(track(RotationTrack, 0, 25), track(ScaleXTrack, -1, -1.1)),
        )
        .null(
            (-20, 10),
            parent="root",
            id="inner",
            rotation=-17,
            animation=motion(track(ScaleYTrack, 1, 0.8)),
        )
    )
    canvas.layers = [*canvas.layers, ordinary.layers[0].model_copy(update={"parent": "inner"})]
    # Independent source oracle: ordinary group composition in its authored
    # canvas plane, then the complete ancestor matrix, with no parent prep.
    matrix = multiply(
        (1, 0, 285, 0, 1, 15),
        multiply(_rotation(25 * time), (-1 - 0.1 * time, 0, 0, 0, 1, 0)),
    )
    matrix = multiply(matrix, (1, 0, -20, 0, 1, 10))
    matrix = multiply(matrix, (1, 0, 0, 0, 1 - 0.2 * time, 0))
    matrix = multiply(matrix, _rotation(-17))
    expected = Image.new("RGBA", source.size)
    fragment = affine_fragment(source, matrix, source.size)
    assert fragment is not None
    expected.alpha_composite(*fragment)
    actual = canvas.render_frame(time)
    assert actual.tobytes() == expected.tobytes()
    assert matrix[0] * matrix[4] - matrix[1] * matrix[3] < 0
    if time:
        assert abs(matrix[0] * matrix[1] + matrix[3] * matrix[4]) > 0.01


@pytest.mark.parametrize("empty", [False, True])
def test_nested_boundaries_preserve_body_pivot_and_explicit_child(empty):
    canvas = linked(nested_scene(empty=empty))
    group = cast(GroupLayer, canvas.layers[-1])
    group.animation = motion(track(RotationTrack, -10, 25), track(OpacityTrack, 0, 0))
    canvas.shape("ellipse", (205, 150), 13, 11, "#00FF00", parent="group", id="marker")
    before = canvas.to_json()
    animator = _SlideAnimator(canvas, {})
    node = animator._units[-1].parent_node
    owner = node.plan.nodes[id(group)]
    geometry = parent_geometry(canvas, group)
    bare = Canvas.from_json(before)

    def uncompose(layer):
        layer.clip = layer.mask = None
        for child in getattr(layer, "children", ()):
            uncompose(child)

    uncompose(bare.layers[1])
    plain_geometry = parent_geometry(bare, bare.layers[1])
    assert (geometry.origin, geometry.body_size, geometry.body_to_baked) == (
        plain_geometry.origin,
        plain_geometry.body_size,
        plain_geometry.body_to_baked,
    )
    pivot = owner.pivot_box
    if empty:
        assert owner.image is None and pivot == (0, 0, *geometry.body_size)
    for time in (0.7, 0.2, 1, 0.7):
        expected = Image.new("RGBA", (canvas.width, canvas.height))
        paint = animator._sample_parents(time)[id(node)][0]
        fragment = affine_fragment(
            node.image, multiply(paint, (1, 0, -node.padding, 0, 1, -node.padding)), expected.size
        )
        assert fragment is not None
        expected.alpha_composite(*fragment)
        assert animator.frame_at(time).tobytes() == expected.tobytes()
        assert owner.pivot_box == pivot
    assert canvas.to_json() == before


@pytest.mark.parametrize(
    "kind",
    [
        "animation",
        "ancestor_animation",
        "inner_animation",
        "descendant_stagger",
        "deep_stagger",
    ],
)
def test_descendant_boundary_guards_preflight_every_observation_and_export(
    monkeypatch, tmp_path, kind
):
    canvas = linked(nested_scene())
    group = cast(GroupLayer, canvas.layers[-1])
    middle = cast(GroupLayer, group.children[0])
    if kind in {"animation", "ancestor_animation", "inner_animation"}:
        cast(ShapeLayer, middle.children[0]).animation = AnimationSpec.fade(duration=1)
        if kind == "ancestor_animation":
            canvas.layers[0].animation = motion(track(OpacityTrack, 0, 1))
        elif kind == "inner_animation":
            middle.animation = motion(track(OpacityTrack, 0, 1))
        expected = "cannot animate descendants"
    else:
        group.animation = motion(track(OpacityTrack, 0, 1))
        if kind == "descendant_stagger":
            middle.animation = [AnimationSpec.rise(stagger=0, target="children")]
        else:
            inner = cast(GroupLayer, middle.children[1])
            wrapper = cast(GroupLayer, inner.children[0])
            cast(TextLayer, wrapper.children[0]).animation = [
                AnimationSpec.fade(duration=1),
                AnimationSpec.rise(stagger=0.1, target="characters"),
            ]
        expected = "cannot use stagger on structural descendants"
    monkeypatch.setattr(canvas, "_render_layer", lambda *_a, **_k: pytest.fail("preflight painted"))
    monkeypatch.setattr(
        canvas._groups, "render_group_layer", lambda *_a, **_k: pytest.fail("preflight painted")
    )
    for observe in (
        canvas.inspect,
        canvas.diagnose,
        canvas._render_to_image,
        lambda: canvas.render_frame(0),
    ):
        with pytest.raises(RenderingError, match=expected):
            observe()
    for target in ("raster", "video", "html", "pptx"):
        diagnostic = next(
            item for item in canvas.validate_export(target) if item.feature == "parent"
        )
        assert expected in diagnostic.message
        assert diagnostic.support == "unsupported"
        # A separately animated ancestor may trigger its own strict capability
        # error first; the parent row still reports the exact source guard.
        with pytest.raises(RenderingError):
            canvas.validate_export(target, ExportPolicy(unsupported_motion="error"))
    for kind in ("png", "gif", "html", "svg", "pdf", "pptx"):
        path = tmp_path / ("existing." + kind)
        path.write_bytes(b"existing")
        with pytest.raises(RenderingError, match=expected):
            canvas.render(str(path))
        assert path.read_bytes() == b"existing"


def test_nested_static_boundary_guards_do_not_affect_unrelated_linked_siblings():
    canvas = linked(nested_scene())
    canvas.text(
        "12",
        font=FONT,
        size=20,
        position=(250, 20),
        parent="root",
        value=AnimatedTextValue.model_validate({"from": 1, "to": 12, "duration": 1}),
        mask=LayerMask(position=(240, 0), width=70, height=60),
    )
    canvas.group(
        [TextLayer(type="text", content="ROW", font=FONT, size=15)],
        position=(250, 100),
        parent="root",
        clip=LayerClip(position=(240, 80), width=80, height=100),
        animation=AnimationSpec.rise(stagger=0.1, target="children"),
    )
    assert canvas.render_frame(0.5).getbbox() is not None
    assert measure_layers(canvas)[-1].children
    assert all(item.support != "unsupported" for item in canvas.validate_export("video"))


@pytest.mark.parametrize("quality", ["standard", "high"])
def test_nested_source_root_motion_recolors_and_reveals_once_across_seeks(quality):
    ordinary = nested_scene(invert=True)
    cast(GroupLayer, ordinary.layers[0]).animation = motion(
        track(RotationTrack, -12, 20),
        track(ScaleXTrack, 0.8, 1.2),
        track(OpacityTrack, 0.4, 0.9),
        track(ClipProgressTrack, 0.2, 1),
        track(ColorTrack, "#BB4422", "#2255CC"),
    )
    parented = linked(ordinary)
    expected = _SlideAnimator(ordinary, {}, quality=quality)
    actual = _SlideAnimator(parented, {}, quality=quality)
    before = parented.to_json()
    for time in (0.8, 0, 0.3, 1, 0.8):
        assert actual.frame_at(time).tobytes() == expected.frame_at(time).tobytes()
    assert parented.to_json() == before
