"""A leaf group's own and structural boundaries travel with partial stagger crops."""

import math
from io import BytesIO
from pathlib import Path
from typing import Any, cast

import pytest
from PIL import Image, ImageFilter
from quickthumb import (
    Align,
    AnimationSpec,
    Background,
    BlurTrack,
    Canvas,
    ClipProgressTrack,
    ColorTrack,
    GroupLayer,
    LayerClip,
    LayerMask,
    OpacityTrack,
    PositionTrack,
    RotationTrack,
    ScaleXTrack,
    ScaleYTrack,
    Shadow,
    ShapeLayer,
    StaggerSpec,
    TextLayer,
    TimingSpec,
)
from quickthumb._export_video import _SlideAnimator, animation_timeline, export_animation_bytes
from quickthumb._parent_render import ParentNode, affine_fragment, parent_geometry

from tests.test_parent_stagger import FONT, motion, track, turn
from tests.test_parent_stagger import group_scene as bare_group_scene


def boundary_options(kind="both"):
    clip = LayerClip(position=(16, 10), width=18, height=84, border_radius=5)
    mask = LayerMask(position=(12, 8), width=26, height=90, opacity=0.6)
    if kind == "clip":
        return {"clip": clip}
    if kind == "mask":
        return {"mask": mask}
    if kind == "percentage":
        clip.position = ("7.5%", "5%")
        return {"clip": clip, "mask": mask}
    if kind.startswith("invert"):
        mask.position, mask.width, mask.height = (23, 42), 16, 18
        mask.shape, mask.invert = "ellipse", True
        mask.opacity = float(kind.removeprefix("invert"))
    return {"clip": clip, "mask": mask}


def group_scene(*, boundary="both", nested=False, **kwargs):
    canvas = bare_group_scene(**kwargs)
    group = cast(GroupLayer, canvas.layers[-1])
    for key, value in boundary_options(boundary).items():
        setattr(group, key, value)
    if nested:
        group.children = [
            GroupLayer(
                type="group",
                children=[
                    child.model_copy(
                        update={
                            "clip": LayerClip(position=(14, 14 + 32 * index), width=22, height=12)
                        }
                    )
                ],
                mask=LayerMask(position=(14, 14 + 32 * index), width=22, height=12, opacity=0.7),
            )
            for index, child in enumerate(group.children)
        ]
    return canvas


NESTED_ROWS = ((20, 44), (60, 91), (105, 181))


def nested_scene(*, own=True, invert=False, animation=None):
    """Three known rows, with composition at leaf, nested and deeper group scopes."""
    if isinstance(animation, AnimationSpec) and animation.stagger:
        animation.stagger.target = "children"
    first = ShapeLayer(
        type="shape",
        shape="rectangle",
        position=(0, 0),
        width=56,
        height=16,
        color="#FFFFFF",
        clip=LayerClip(position=("15%", "12%"), width=42, height=16, align=Align.CENTER),
    )
    middle = GroupLayer(
        type="group",
        direction="row",
        padding=(2, 3),
        children=[
            ShapeLayer(
                type="shape",
                shape="rectangle",
                position=(0, 0),
                width=30,
                height=16,
                color="#FFFFFF",
                opacity=0.7,
                effects=[Shadow(color="#334455", offset_x=8, offset_y=0, blur_radius=0)],
            )
            for _ in range(2)
        ],
        mask=LayerMask(
            position=(47, 68) if invert else ("20%", "28%"),
            width=16 if invert else 82,
            height=10 if invert else 28,
            align=None if invert else Align.CENTER,
            opacity=0.55,
            invert=invert,
        ),
    )
    last = GroupLayer(
        type="group",
        padding=(2, 4),
        clip=LayerClip(position=("10%", "40%"), width=120, height=65),
        children=[
            GroupLayer(
                type="group",
                padding=(3, 5),
                mask=LayerMask(position=(32, 105), width=104, height=60, opacity=0.65),
                children=[
                    TextLayer(
                        type="text",
                        content="THREE",
                        font=FONT,
                        size=20,
                        color="#FFFFFF",
                        effects=[Background(color="#224466", padding=4)],
                    )
                ],
            )
        ],
    )
    return (
        Canvas(320, 260)
        .null((35, 25), id="root")
        .group(
            [first, middle, last],
            position=(20, 18),
            padding=(6, 8),
            gap=24,
            parent="root",
            id="leaf",
            animation=animation
            or AnimationSpec.rise(
                distance=20, duration=0.5, stagger=0.4, target="children", easing="linear"
            ),
            clip=LayerClip(position=(22, 20), width=145, height=170, border_radius=5)
            if own
            else None,
            mask=LayerMask(position=(20, 18), width=150, height=180, opacity=0.8) if own else None,
        )
    )


def static_source(canvas, *, color=None, reference=False):
    """Independent ordinary renderer, without parent preparation or target splitting."""
    group = cast(GroupLayer, canvas.layers[-1]).model_copy(
        deep=True, update={"parent": None, "animation": None}
    )

    def recolor(layer):
        layer.animation = None
        if reference and hasattr(layer, "opacity"):
            layer.opacity = 1
        if isinstance(layer, GroupLayer):
            for child in layer.children:
                recolor(child)
        else:
            if color is not None or reference:
                layer.color = "#FFFFFF" if reference else color

    recolor(group)
    return Canvas(canvas.width, canvas.height, layers=[group])._render_to_image()


@pytest.mark.parametrize(
    "boundary", ["clip", "mask", "both", "percentage", "invert0", "invert0.4", "invert1"]
)
@pytest.mark.parametrize("nested", [False, True])
def test_band_crops_are_cut_from_complete_composed_static_group(boundary, nested):
    canvas = group_scene(boundary=boundary, nested=nested)
    before = canvas.to_json()
    animator = _SlideAnimator(canvas, {})
    node = animator._units[-1].parent_node
    expected = static_source(canvas)
    assert len(node.unit.target_images) == 3
    for index, (source, offset) in enumerate(node.unit.target_images):
        # Authored shapes occupy known layout rows, independently of the adapter.
        strip = expected.crop((0, 14 + index * 32, canvas.width, 26 + index * 32))
        bounds = strip.getbbox()
        assert bounds is not None
        assert source.tobytes() == strip.crop(bounds).tobytes()
        assert offset == (
            bounds[0] - 10 + node.padding,
            14 + index * 32 + bounds[1] - 10 + node.padding,
        )
    assert canvas.to_json() == before


@pytest.mark.parametrize("own", [False, True])
@pytest.mark.parametrize("invert", [False, True])
def test_nested_bands_match_independent_ordinary_rows_and_preserve_body(own, invert):
    canvas = nested_scene(own=own, invert=invert)
    before = canvas.to_json()
    animator = _SlideAnimator(canvas, {})
    node = animator._units[-1].parent_node
    expected = static_source(canvas)
    assert node.origin == (20, 18) and node.padding > 2
    assert len(node.unit.target_images) == 3
    for (top, bottom), (source, offset) in zip(NESTED_ROWS, node.unit.target_images, strict=True):
        strip = expected.crop((0, top, canvas.width, bottom))
        bounds = strip.getbbox()
        assert bounds is not None
        assert source.tobytes() == strip.crop(bounds).tobytes()
        assert offset == (bounds[0] - 20 + node.padding, top + bounds[1] - 18 + node.padding)
    bare = Canvas.from_json(before)

    def uncompose(layer):
        layer.clip = layer.mask = None
        for child in getattr(layer, "children", ()):
            uncompose(child)

    uncompose(bare.layers[-1])
    geometry = parent_geometry(canvas, canvas.layers[-1])
    plain = parent_geometry(bare, bare.layers[-1])
    assert (geometry.origin, geometry.body_size, geometry.body_to_baked) == (
        plain.origin,
        plain.body_size,
        plain.body_to_baked,
    )
    assert canvas.to_json() == before


@pytest.mark.parametrize("quality", ["standard", "high"])
@pytest.mark.parametrize("invert", [False, True])
def test_nested_color_clocks_use_independent_reference_crops_and_output_effects(quality, invert):
    canvas = nested_scene(
        invert=invert,
        animation=motion(
            track(ColorTrack, "#000000", "#FFFFFF"),
            track(PositionTrack, (20, 0), (0, 0)),
            track(OpacityTrack, 0.2, 1),
            track(ClipProgressTrack, 0.2, 1),
            track(BlurTrack, 0, 2),
            stagger=0.4,
        ),
    )
    before = canvas.to_json()
    animator = _SlideAnimator(canvas, {}, quality=quality)
    node = animator._units[-1].parent_node
    reference = static_source(canvas, reference=True)
    crops = []
    for (top, bottom), (prepared, offset) in zip(NESTED_ROWS, node.unit.target_images, strict=True):
        strip = reference.crop((0, top, canvas.width, bottom))
        box = strip.getbbox()
        assert box is not None
        crops.append((box[0], top + box[1], box[2], top + box[3]))
        assert prepared.tobytes() == strip.crop(box).tobytes()
        assert offset == (box[0] - 20 + node.padding, top + box[1] - 18 + node.padding)
    assert len(crops) == 3
    stable = [(image.tobytes(), offset) for image, offset in node.unit.target_images]
    cache, pivot = canvas._ctx.measure_cache, node.pivot_box
    measurements = dict(cache)
    for instant in (0, 0.6, 1.8, 0.2, 1, 0.6):
        scale = 2 if quality == "high" else 1
        expected = Image.new("RGBA", (canvas.width * scale, canvas.height * scale))
        for index, box in enumerate(crops):
            if instant < index * 0.4:
                continue
            elapsed = min(1, instant - index * 0.4)
            # Black-to-white Oklab has L=t and a=b=0. Encode its linear t**3
            # luminance independently; no timeline sampling or color helper.
            linear = elapsed**3
            channel = round(
                255
                * (12.92 * linear if linear <= 0.0031308 else 1.055 * linear ** (1 / 2.4) - 0.055)
            )
            source = static_source(canvas, color="#" + f"{channel:02X}" * 3)
            patch = source.crop(box)
            opacity = 1 if elapsed == 1 else 0.2 + 0.8 * elapsed
            alpha = patch.getchannel("A").point(
                lambda value, opacity=opacity: round(value * opacity)
            )
            if elapsed < 1:
                cutoff = min(patch.width, round(patch.width * opacity) + 1)
                alpha.paste(0, (cutoff, 0, patch.width, patch.height))
            patch.putalpha(alpha)
            padded = Image.new("RGBA", (patch.width + 4, patch.height + 4))
            padded.paste(patch, (2, 2))
            blur = 2 * elapsed
            fragment = affine_fragment(
                padded,
                (1, 0, 35 + box[0] + 20 * (1 - elapsed) - 2, 0, 1, 25 + box[1] - 2),
                expected.size,
                render_scale=scale,
                margin=math.ceil(3 * blur * scale),
            )
            assert fragment is not None
            patch, offset = fragment
            if blur:
                spread = max(1, math.ceil(blur * scale * 3))
                padded = Image.new("RGBA", (patch.width + 2 * spread, patch.height + 2 * spread))
                padded.alpha_composite(patch, (spread, spread))
                patch = padded.filter(ImageFilter.GaussianBlur(blur * scale))
                offset = offset[0] - spread, offset[1] - spread
            expected.alpha_composite(patch, offset)
        if scale == 2:
            expected = expected.resize((canvas.width, canvas.height), Image.Resampling.LANCZOS)
        assert animator.frame_at(instant).tobytes() == expected.tobytes()
    assert stable == [(image.tobytes(), offset) for image, offset in node.unit.target_images]
    assert node.pivot_box == pivot and canvas._ctx.measure_cache is cache and cache == measurements
    assert canvas.to_json() == before


@pytest.mark.parametrize(
    "case,visible_bands",
    [
        ("row", 1),
        ("touching", 1),
        ("two", 2),
        ("one", 1),
        ("zero", 0),
        ("blank", 0),
        ("nested_extra", 4),
        ("cut_band", 4),
    ],
)
def test_changed_band_cardinality_retains_whole_source_fallback(case, visible_bands):
    canvas = group_scene(boundary="mask")
    group = cast(GroupLayer, canvas.layers[-1])
    group.mask = LayerMask(position=(0, 0), width=220, height=170, opacity=0.5)
    if case == "row":
        group.direction = "row"
    elif case == "touching":
        group.gap = 0
    elif case in {"two", "one", "zero"}:
        group.clip = LayerClip(
            position=(0, 0), width=100, height={"two": 65, "one": 33, "zero": 5}[case]
        )
    elif case == "cut_band":
        group.mask = LayerMask(position=(0, 18), width=200, height=3, invert=True)
    elif case == "blank":
        for child in group.children:
            cast(Any, child).opacity = 0
    else:
        group.children[1] = GroupLayer(
            type="group", children=[group.children[1], group.children[1].model_copy()], gap=10
        )
    animator = _SlideAnimator(canvas, {})
    unit = animator._units[-1]
    assert len(unit.target_timelines) == 3 and not unit.target_images
    source = static_source(canvas)
    occupied = [
        source.getchannel("A").crop((0, y, canvas.width, y + 1)).getbbox() is not None
        for y in range(canvas.height)
    ]
    assert (
        sum(value and (y == 0 or not occupied[y - 1]) for y, value in enumerate(occupied))
        == visible_bands
    )
    for instant in (0.2, 0.6, 1.3, 0.6):
        assert animator.frame_at(instant).tobytes() == canvas.render_frame(instant).tobytes()
    assert (animator.frame_at(1.3).getbbox() is None) is (visible_bands == 0)


def test_whole_source_fallback_keeps_last_geometry_and_averaged_arrival_alpha_reveal():
    canvas = group_scene(
        direction="row",
        boundary="mask",
        animation=motion(
            track(PositionTrack, (0, 0), (30, 0)), track(OpacityTrack, 0.4, 1), stagger=0.4
        ),
    )
    group = cast(GroupLayer, canvas.layers[-1])
    group.mask = LayerMask(position=(0, 0), width=200, height=80, opacity=0.6)
    animator = _SlideAnimator(canvas, {})
    node = animator._units[-1].parent_node
    assert not node.unit.target_images
    for instant in (0.2, 0.6, 1.0, 1.8, 0.6):
        latest = max(0, min(1, instant - 0.8))
        arrival = sum(max(0, min(1, instant - index * 0.4)) for index in range(3)) / 3
        sample = node.plan.sample(instant)[id(node)]
        state = sample[2].canonical
        assert (state.layer.position or (0, 0)) == pytest.approx((30 * latest, 0))
        opacity = 1 if instant < 0.8 or latest == 1 else 0.4 + 0.6 * latest
        assert state.layer.opacity == pytest.approx(opacity)
        assert state.alpha_scale == pytest.approx(arrival)
        assert state.clip_scale == pytest.approx(arrival)
        expected = static_source(canvas)
        alpha = expected.getchannel("A").point(
            lambda value, opacity=opacity, arrival=arrival: round(value * opacity * arrival)
        )
        left, top, right, bottom = expected.getbbox()
        width = round((right - left) * arrival)
        alpha.paste(0, (left + width + 1, 0, expected.width, expected.height))
        expected.putalpha(alpha)
        result = Image.new("RGBA", expected.size)
        result.alpha_composite(expected, (35 + round(30 * latest), 25))
        assert animator.frame_at(instant).tobytes() == result.tobytes()


@pytest.mark.parametrize(
    "case,visible_bands", [("erased", 2), ("split", 4), ("joined", 1), ("empty", 0)]
)
def test_nested_cardinality_fallback_uses_independent_whole_source_arithmetic(case, visible_bands):
    canvas = nested_scene(
        animation=motion(
            track(PositionTrack, (0, 0), (30, 0)), track(OpacityTrack, 0.4, 1), stagger=0.4
        )
    )
    group = cast(GroupLayer, canvas.layers[-1])
    middle = cast(GroupLayer, group.children[1])
    if case == "split":
        middle.mask = LayerMask(position=(0, 72), width=320, height=3, invert=True)
    elif case == "joined":

        def join(layer):
            if layer.clip:
                layer.clip = LayerClip(position=(0, 0), width=320, height=260)
            if layer.mask:
                layer.mask = LayerMask(position=(0, 0), width=320, height=260, opacity=0.6)
            if isinstance(layer, GroupLayer):
                layer.padding = 0
                layer.gap = 0
                for child in layer.children:
                    join(child)

        join(group)
    else:
        cast(ShapeLayer, group.children[0]).clip = LayerClip(
            position=(500, 500), width=20, height=20
        )
        if case == "empty":
            for child in group.children[1:]:
                cast(GroupLayer, child).clip = LayerClip(position=(500, 500), width=20, height=20)
    before = canvas.to_json()
    animator = _SlideAnimator(canvas, {})
    node = animator._units[-1].parent_node
    assert len(node.unit.target_timelines) == 3 and not node.unit.target_images
    source = static_source(canvas)
    occupied = [
        source.getchannel("A").crop((0, y, canvas.width, y + 1)).getbbox() is not None
        for y in range(canvas.height)
    ]
    assert (
        sum(value and (y == 0 or not occupied[y - 1]) for y, value in enumerate(occupied))
        == visible_bands
    )
    if not visible_bands:
        assert node.image is None
        assert node.pivot_box == (0, 0, *parent_geometry(canvas, group).body_size)
    for instant in (0.2, 0.6, 1, 1.8, 0.6):
        latest = min(1, max(0, instant - 0.8))
        arrival = sum(min(1, max(0, instant - index * 0.4)) for index in range(3)) / 3
        opacity = 1 if instant < 0.8 or latest == 1 else 0.4 + 0.6 * latest
        state = node.plan.sample(instant)[id(node)][2].canonical
        assert (state.layer.position or (0, 0)) == pytest.approx((30 * latest, 0))
        assert state.layer.opacity == pytest.approx(opacity)
        assert (state.alpha_scale, state.clip_scale) == pytest.approx((arrival, arrival))
        expected = Image.new("RGBA", source.size)
        if visible_bands:
            patch = source.copy()
            alpha = patch.getchannel("A").point(
                lambda value, opacity=opacity, arrival=arrival: round(value * opacity * arrival)
            )
            left, _, right, _ = source.getbbox()
            alpha.paste(
                0, (left + round((right - left) * arrival) + 1, 0, source.width, source.height)
            )
            patch.putalpha(alpha)
            expected.alpha_composite(patch, (35 + round(30 * latest), 25))
        assert animator.frame_at(instant).tobytes() == expected.tobytes()
    assert canvas.to_json() == before


def test_accidental_matching_count_keeps_horizontal_band_approximation():
    canvas = nested_scene()
    group = cast(GroupLayer, canvas.layers[-1])
    # A first child disappears while the second supplies two bands. Three
    # immediate children still declare three clocks; bands have no child IDs.
    cast(ShapeLayer, group.children[0]).clip = LayerClip(position=(500, 500), width=20, height=20)
    cast(GroupLayer, group.children[1]).mask = LayerMask(
        position=(0, 72), width=320, height=3, invert=True
    )
    unit = _SlideAnimator(canvas, {})._units[-1]
    assert len(unit.target_timelines) == len(unit.target_images) == 3
    source = static_source(canvas)
    node = unit.parent_node
    for (top, bottom), (image, offset) in zip(
        ((60, 73), (74, 91), NESTED_ROWS[2]), unit.target_images, strict=True
    ):
        strip = source.crop((0, top, canvas.width, bottom))
        box = strip.getbbox()
        assert box is not None
        assert image.tobytes() == strip.crop(box).tobytes()
        assert offset == (box[0] - 20 + node.padding, top + box[1] - 18 + node.padding)
    assert [timeline.events[0].start for timeline in unit.target_timelines] == [0, 0.4, 0.8]


@pytest.mark.parametrize("count", [1, 3])
@pytest.mark.parametrize("delay", [0, 0.4])
@pytest.mark.parametrize("scene", [group_scene, nested_scene])
def test_single_and_zero_delay_declarations_keep_existing_target_rules(count, delay, scene):
    canvas = scene(animation=motion(track(PositionTrack, (0, 0), (10, 0)), stagger=delay))
    cast(GroupLayer, canvas.layers[-1]).children = cast(GroupLayer, canvas.layers[-1]).children[
        :count
    ]
    animator = _SlideAnimator(canvas, {})
    unit = animator._units[-1]
    assert len(unit.target_timelines) == max(1, count)
    assert len(unit.target_images) == (3 if count == 3 else 0)
    assert animator.duration == pytest.approx(1 + max(0, count - 1) * delay)
    assert (
        animator.frame_at(animator.duration).tobytes()
        == animator.frame_at(animator.duration + 1).tobytes()
    )


@pytest.mark.parametrize("quality", ["standard", "high"])
@pytest.mark.parametrize("transparent", [False, True])
def test_recoloring_uses_stable_composed_reference_crops_with_per_target_appearance(
    quality, transparent
):
    canvas = group_scene(
        animation=motion(
            track(ColorTrack, "#FF0000", "#FF0000"),
            track(OpacityTrack, 0.2, 1),
            track(ClipProgressTrack, 0.2, 1),
            track(BlurTrack, 0, 2),
            track(PositionTrack, (20, 0), (0, 0)),
            stagger=0.4,
        )
    )
    if transparent:
        for child in cast(GroupLayer, canvas.layers[-1]).children:
            cast(Any, child).color = "#00000000"
    animator = _SlideAnimator(canvas, {}, quality=quality)
    node = animator._units[-1].parent_node
    assert (node.image is None) is transparent
    assert len(node.unit.target_images) == 3
    before = [(source.tobytes(), offset, source.size) for source, offset in node.unit.target_images]
    source = static_source(canvas, color="#FF0000")
    cache = canvas._ctx.measure_cache
    measurements = dict(cache)
    # The ordinary static compositor supplies each composed band; independent
    # arithmetic supplies its clock, alpha, reveal, placement and blur.
    for instant in (0, 0.6, 1.8, 0.2, 0.6):
        scale = 2 if quality == "high" else 1
        expected = Image.new("RGBA", (source.width * scale, source.height * scale))
        for index in range(3):
            if instant < index * 0.4:
                continue
            elapsed = max(0, min(1, instant - index * 0.4))
            opacity = 1 if elapsed == 1 else 0.2 + 0.8 * elapsed
            band = source.crop((0, 14 + index * 32, source.width, 26 + index * 32))
            box = band.getbbox()
            assert box is not None
            patch = band.crop(box)
            alpha = patch.getchannel("A").point(
                lambda value, opacity=opacity: round(value * opacity)
            )
            if elapsed < 1:
                cutoff = round(patch.width * opacity) + 1
                alpha.paste(0, (min(cutoff, patch.width), 0, patch.width, patch.height))
            patch.putalpha(alpha)
            padded = Image.new("RGBA", (patch.width + 4, patch.height + 4))
            padded.paste(patch, (2, 2))
            blur = elapsed * 2
            fragment = affine_fragment(
                padded,
                (
                    1,
                    0,
                    35 + box[0] + 20 * (1 - elapsed) - 2,
                    0,
                    1,
                    25 + 14 + index * 32 + box[1] - 2,
                ),
                expected.size,
                render_scale=2 if quality == "high" else 1,
                margin=math.ceil(3 * blur * (2 if quality == "high" else 1)),
            )
            assert fragment is not None
            patch, offset = fragment
            if blur:
                spread = max(1, math.ceil(blur * (2 if quality == "high" else 1) * 3))
                padded = Image.new("RGBA", (patch.width + 2 * spread, patch.height + 2 * spread))
                padded.alpha_composite(patch, (spread, spread))
                patch = padded.filter(
                    ImageFilter.GaussianBlur(blur * (2 if quality == "high" else 1))
                )
                offset = offset[0] - spread, offset[1] - spread
            expected.alpha_composite(patch, offset)
        if scale == 2:
            expected = expected.resize(source.size, Image.Resampling.LANCZOS)
        assert animator.frame_at(instant).tobytes() == expected.tobytes()
    assert before == [
        (image.tobytes(), offset, image.size) for image, offset in node.unit.target_images
    ]
    assert canvas._ctx.measure_cache is cache and cache == measurements


@pytest.mark.parametrize(
    "scene,options",
    [
        (group_scene, {"boundary": "clip"}),
        (group_scene, {"boundary": "both"}),
        (group_scene, {"boundary": "invert0.4"}),
        (nested_scene, {}),
        (nested_scene, {"invert": True}),
    ],
)
def test_each_composed_crop_inherits_three_analytic_ancestor_frames(scene, options, monkeypatch):
    from quickthumb import _parent_render as renderer

    canvas = scene(
        **options,
        animation=motion(
            track(PositionTrack, (0, 8), (12, -3)),
            track(RotationTrack, -10, 25),
            track(ScaleXTrack, 0.8, 1.4),
            track(ScaleYTrack, 1, 0.7),
            stagger=0.4,
        ),
    )
    group = cast(GroupLayer, canvas.layers[-1])
    authored_origin = cast(tuple[int, int], group.position)
    group.anchor = (0.2, 0.8)
    root = cast(Any, canvas.layers[0])
    root.position = (130, 100)
    root.animation = motion(
        track(ScaleXTrack, -1, -1.8),
        track(RotationTrack, 0, 35),
        track(OpacityTrack, 0, 0),
        track(BlurTrack, 5, 5),
        track(ClipProgressTrack, 0, 0),
    )
    canvas.null(
        (14, 8),
        id="middle",
        parent="root",
        rotation=17,
        animation=motion(track(ScaleYTrack, 1, 0.6), track(RotationTrack, 0, -22)),
    )
    canvas.null((9, 6), id="inner", parent="middle", rotation=-13)
    group.parent = "inner"
    animator = _SlideAnimator(canvas, {})
    node = animator._units[1].parent_node
    calls = []
    original = renderer.affine_fragment

    def capture(image, matrix, size, **kwargs):
        calls.append((image.size, matrix))
        return original(image, matrix, size, **kwargs)

    monkeypatch.setattr(renderer, "affine_fragment", capture)
    for instant in (0, 0.61, 1.8, 0.23, 0.61):
        calls.clear()
        animator.frame_at(instant)
        visible = [index for index in range(3) if instant >= index * 0.4]
        assert len(calls) == len(visible)
        parent_t = min(1, instant)
        for index, (padded_size, matrix) in zip(visible, calls, strict=True):
            image, offset = node.unit.target_images[index]
            assert padded_size == (image.width + 4, image.height + 4)
            elapsed = min(1, instant - 0.4 * index)
            anchor = (image.width * 0.2, image.height * 0.8)
            for point in ((0, 0), image.size):
                local = turn(
                    (point[0] - anchor[0], point[1] - anchor[1]),
                    (12 * elapsed + anchor[0], 8 - 11 * elapsed + anchor[1]),
                    -10 + 35 * elapsed,
                    0.8 + 0.6 * elapsed,
                    1 - 0.3 * elapsed,
                )
                local = (
                    local[0] + authored_origin[0] + offset[0] - node.padding,
                    local[1] + authored_origin[1] + offset[1] - node.padding,
                )
                local = turn(local, (9, 6), -13, 1, 1)
                local = turn(local, (0, 0), 17, 1, 1)
                local = turn(local, (14, 8), -22 * parent_t, 1, 1 - 0.4 * parent_t)
                expected = turn(local, (130, 100), 35 * parent_t, -1 - 0.8 * parent_t, 1)
                actual = (
                    matrix[0] * (point[0] + 2) + matrix[1] * (point[1] + 2) + matrix[2],
                    matrix[3] * (point[0] + 2) + matrix[4] * (point[1] + 2) + matrix[5],
                )
                assert actual == pytest.approx(expected, abs=1e-10)
            assert matrix[0] * matrix[4] - matrix[1] * matrix[3] < 0
            if instant:
                assert abs(matrix[0] * matrix[1] + matrix[3] * matrix[4]) > 0.01


@pytest.mark.parametrize("quality", ["standard", "high"])
@pytest.mark.parametrize("scene", [group_scene, nested_scene])
def test_early_composed_targets_survive_last_target_collapse_but_not_ancestor_collapse(
    quality, scene
):
    canvas = scene(animation=motion(track(ScaleXTrack, 0, 1), stagger=0.4))
    animator = _SlideAnimator(canvas, {}, quality=quality)
    node = animator._units[-1].parent_node
    assert node.plan.sample(0.8)[id(node)][3]
    assert animator.frame_at(0).getbbox() is None
    for instant in (0.2, 0.6, 0.8):
        assert animator.frame_at(instant).getbbox() is not None
    cast(Any, canvas.layers[0]).animation = motion(track(ScaleYTrack, 0, 0))
    collapsed = _SlideAnimator(canvas, {}, quality=quality)
    for instant in (0.2, 1, 1.8):
        assert collapsed.frame_at(instant).getbbox() is None


@pytest.mark.parametrize("scene", [group_scene, nested_scene])
def test_static_composed_crops_are_cached_without_repainting(monkeypatch, scene):
    animator = _SlideAnimator(scene(), {})
    before = [(image.tobytes(), offset) for image, offset in animator._units[-1].target_images]
    monkeypatch.setattr(ParentNode, "render_source", lambda *a, **k: pytest.fail("repaint"))
    frames = [animator.frame_at(t).tobytes() for t in (0.1, 0.6, 1.3, 2, 0.6)]
    assert frames[1] == frames[-1] and frames[2] == frames[3]
    assert before == [
        (image.tobytes(), offset) for image, offset in animator._units[-1].target_images
    ]


@pytest.mark.parametrize("scene", [group_scene, nested_scene])
def test_composed_specs_keep_existing_cardinality_duration_and_overlap(scene):
    canvas = scene(
        animation=[
            AnimationSpec.rise(
                distance=20, duration=0.5, stagger=0.4, target="children", easing="linear"
            ),
            AnimationSpec.fade(duration=0.2, easing="linear"),
        ]
    )
    animator = _SlideAnimator(canvas, {})
    unit = animator._units[-1]
    assert not unit.target_images and len(unit.target_timelines) == 1
    assert [event.start for event in unit.target_timelines[0].events] == [0, 0.5]
    assert animator.duration == pytest.approx(0.7)
    assert animator.frame_at(0.7).tobytes() == animator.frame_at(2).tobytes()


def test_group_override_still_suppresses_nested_descendant_motion():
    canvas = group_scene(nested=True, child_motion=True)
    fixed = group_scene(nested=True)
    for instant in (0.1, 0.6, 1.3, 0.6):
        assert canvas.render_frame(instant).tobytes() == fixed.render_frame(instant).tobytes()


@pytest.mark.parametrize("quality", ["standard", "high"])
def test_root_stagger_suppresses_nested_specs_without_changing_source_or_schedule(quality):
    from tests.test_parent_nested_overrides import stripped_reference

    canvas = nested_scene(
        invert=True,
        animation=motion(
            track(PositionTrack, (15, 0), (0, 0)),
            track(ColorTrack, "#FF0000", "#0000FF"),
            track(RotationTrack, -12, 12),
            stagger=0.4,
        ),
    )
    canvas.layers[0].animation = AnimationSpec.rise(distance=0, duration=0.1)
    suppressed = AnimationSpec.timeline(
        track(PositionTrack, (200, 100), (-200, -100)),
        track(ScaleXTrack, -2, 2),
        track(ColorTrack, "#00FF00", "#FF00FF"),
        timing=TimingSpec(duration=80, delay=40),
    )

    def animate_descendants(layer):
        for child in getattr(layer, "children", ()):
            child.animation = [
                suppressed.model_copy(deep=True),
                AnimationSpec.fade(duration=60, delay=30),
            ]
            animate_descendants(child)

    animate_descendants(canvas.layers[-1])
    before = canvas.to_json()
    reference = stripped_reference(canvas)
    actual = _SlideAnimator(canvas, {}, quality=quality)
    expected = _SlideAnimator(reference, {}, quality=quality)
    node, fixed = actual._units[-1].parent_node, expected._units[-1].parent_node
    assert node.image.tobytes() == fixed.image.tobytes()
    assert (node.origin, node.source_size, node.pivot_box) == (
        fixed.origin,
        fixed.source_size,
        fixed.pivot_box,
    )
    assert actual.duration == expected.duration == pytest.approx(1.8)
    assert actual.segments(0, 2) == expected.segments(0, 2)
    assert actual.segments(0, 2)[-1] == (1.8, 2, False)
    assert animation_timeline([canvas], [None], 0.2) == ([0.0], 2)
    crops = [(image.tobytes(), offset) for image, offset in node.unit.target_images]
    assert len(crops) == 3
    cache, measurements = canvas._ctx.measure_cache, dict(canvas._ctx.measure_cache)
    for instant in (0.9, 0.2, 1.5, 1.8, 0, 0.9):
        assert actual.frame_at(instant).tobytes() == expected.frame_at(instant).tobytes()
    assert crops == [(image.tobytes(), offset) for image, offset in node.unit.target_images]
    assert canvas._ctx.measure_cache is cache and cache == measurements
    assert canvas.inspect() == reference.inspect()
    assert canvas.diagnose() == reference.diagnose()
    assert canvas.inspect_motion(target="video", max_samples=2).duration > 100
    assert reference.inspect_motion(target="video", max_samples=2).duration == 1
    payload = export_animation_bytes(
        [canvas], [None], "gif", fps=5, slide_duration=0.2, quality=quality
    )
    assert payload == export_animation_bytes(
        [reference], [None], "gif", fps=5, slide_duration=0.2, quality=quality
    )
    with Image.open(BytesIO(payload)) as gif:
        duration = 0
        for index in range(getattr(gif, "n_frames", 1)):
            gif.seek(index)
            duration += gif.info.get("duration", 0)
        assert duration == 2000
    assert canvas.to_json() == before


def test_group_stagger_visual_snapshot():
    from examples.parent_group_stagger import build_scene, snapshot

    animator = _SlideAnimator(build_scene(), {})
    groups = [unit for unit in animator._units if isinstance(unit.layers[0], GroupLayer)]
    assert [len(unit.target_images) for unit in groups] == [3, 3, 0]
    assert animator.duration == pytest.approx(1.4)
    actual = snapshot()
    expected = Image.open(Path(__file__).parent / "snapshots/parent_group_stagger.png").convert(
        "RGBA"
    )
    assert (actual.size, actual.tobytes()) == (expected.size, expected.tobytes())


@pytest.mark.parametrize("target", ["lines", "words", "characters"])
@pytest.mark.parametrize("scene", [group_scene, nested_scene])
def test_non_child_declarations_keep_the_existing_single_group_target(target, scene):
    canvas = scene()
    cast(Any, canvas.layers[-1]).animation.stagger.target = target
    unit = _SlideAnimator(canvas, {})._units[-1]
    assert len(unit.target_timelines) == 1 and not unit.target_images


@pytest.mark.parametrize("order", ["document", "top_to_bottom", "left_to_right", "reverse"])
@pytest.mark.parametrize("scene", [group_scene, nested_scene])
def test_declared_order_keeps_existing_top_to_bottom_band_clocks(order, scene):
    canvas = scene()
    cast(Any, canvas.layers[-1]).animation.stagger = StaggerSpec(
        delay=0.4, target="children", order=order
    )
    animator = _SlideAnimator(canvas, {})
    unit = animator._units[-1]
    assert [timeline.events[0].start for timeline in unit.target_timelines] == [0, 0.4, 0.8]
    assert [offset[1] for _, offset in unit.target_images] == sorted(
        offset[1] for _, offset in unit.target_images
    )
    assert animator.frame_at(0.2).tobytes() == scene().render_frame(0.2).tobytes()


def test_each_color_clock_repaints_one_composed_source_with_stable_crops():
    canvas = group_scene(animation=motion(track(ColorTrack, "#FF0000", "#0000FF"), stagger=0.4))
    animator = _SlideAnimator(canvas, {})
    unit = animator._units[-1]
    bounds = [(image.size, offset) for image, offset in unit.target_images]
    frame = animator.frame_at(1)
    colors = [
        cast(tuple[int, int, int, int], frame.getpixel((57, 45 + 32 * index))) for index in range(3)
    ]
    assert colors[0] == (0, 0, 255, 153)
    assert all(color[3] == 153 for color in colors)
    assert colors[0][0] < colors[1][0] < colors[2][0]
    assert colors[0][2] > colors[1][2] > colors[2][2]
    assert animator.frame_at(1.8).tobytes() == animator.frame_at(2).tobytes()
    assert animator.frame_at(1).tobytes() == frame.tobytes()
    assert [(image.size, offset) for image, offset in unit.target_images] == bounds
