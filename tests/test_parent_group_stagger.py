"""A leaf group's own boundary travels with the existing partial stagger crops."""

import math
from pathlib import Path
from typing import Any, cast

import pytest
from PIL import Image, ImageFilter
from quickthumb import (
    AnimationSpec,
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
    StaggerSpec,
)
from quickthumb._export_video import _SlideAnimator
from quickthumb._parent_render import ParentNode, affine_fragment

from tests.test_parent_stagger import group_scene as bare_group_scene
from tests.test_parent_stagger import motion, track, turn


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
        group.children = [GroupLayer(type="group", children=[child]) for child in group.children]
    return canvas


def static_source(canvas, *, color=None):
    """Independent ordinary renderer, without parent preparation or target splitting."""
    group = cast(GroupLayer, canvas.layers[-1]).model_copy(
        deep=True, update={"parent": None, "animation": None}
    )

    def recolor(layer):
        if isinstance(layer, GroupLayer):
            for child in layer.children:
                recolor(child)
        else:
            layer.animation = None
            if color is not None:
                layer.color = color

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


@pytest.mark.parametrize("count", [1, 3])
@pytest.mark.parametrize("delay", [0, 0.4])
def test_single_and_zero_delay_declarations_keep_existing_target_rules(count, delay):
    canvas = group_scene(animation=motion(track(PositionTrack, (0, 0), (10, 0)), stagger=delay))
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


@pytest.mark.parametrize("boundary", ["clip", "both", "invert0.4"])
def test_each_composed_crop_inherits_three_analytic_ancestor_frames(boundary, monkeypatch):
    from quickthumb import _parent_render as renderer

    canvas = group_scene(
        boundary=boundary,
        animation=motion(
            track(PositionTrack, (0, 8), (12, -3)),
            track(RotationTrack, -10, 25),
            track(ScaleXTrack, 0.8, 1.4),
            track(ScaleYTrack, 1, 0.7),
            stagger=0.4,
        ),
    )
    group = cast(GroupLayer, canvas.layers[-1])
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
                    local[0] + 10 + offset[0] - node.padding,
                    local[1] + 10 + offset[1] - node.padding,
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
def test_early_composed_targets_survive_last_target_collapse_but_not_ancestor_collapse(quality):
    canvas = group_scene(animation=motion(track(ScaleXTrack, 0, 1), stagger=0.4))
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


def test_static_composed_crops_are_cached_without_repainting(monkeypatch):
    animator = _SlideAnimator(group_scene(), {})
    before = [(image.tobytes(), offset) for image, offset in animator._units[-1].target_images]
    monkeypatch.setattr(ParentNode, "render_source", lambda *a, **k: pytest.fail("repaint"))
    frames = [animator.frame_at(t).tobytes() for t in (0.1, 0.6, 1.3, 2, 0.6)]
    assert frames[1] == frames[-1] and frames[2] == frames[3]
    assert before == [
        (image.tobytes(), offset) for image, offset in animator._units[-1].target_images
    ]


def test_composed_specs_keep_existing_cardinality_duration_and_overlap():
    canvas = group_scene(
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
def test_non_child_declarations_keep_the_existing_single_group_target(target):
    canvas = group_scene()
    cast(Any, canvas.layers[-1]).animation.stagger.target = target
    unit = _SlideAnimator(canvas, {})._units[-1]
    assert len(unit.target_timelines) == 1 and not unit.target_images


@pytest.mark.parametrize("order", ["document", "top_to_bottom", "left_to_right", "reverse"])
def test_declared_order_keeps_existing_top_to_bottom_band_clocks(order):
    canvas = group_scene()
    cast(Any, canvas.layers[-1]).animation.stagger = StaggerSpec(
        delay=0.4, target="children", order=order
    )
    animator = _SlideAnimator(canvas, {})
    unit = animator._units[-1]
    assert [timeline.events[0].start for timeline in unit.target_timelines] == [0, 0.4, 0.8]
    assert [offset[1] for _, offset in unit.target_images] == sorted(
        offset[1] for _, offset in unit.target_images
    )
    assert animator.frame_at(0.2).tobytes() == group_scene().render_frame(0.2).tobytes()


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
