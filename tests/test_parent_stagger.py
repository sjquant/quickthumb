"""Partial stagger targets keep independent clocks inside their ancestor frame."""

import math
from io import BytesIO
from typing import Any, cast

import pytest
from PIL import Image
from quickthumb import (
    AnimationSpec,
    BlurTrack,
    Canvas,
    ClipProgressTrack,
    ColorTrack,
    GifOptions,
    KeyframeSpec,
    OpacityTrack,
    PositionTrack,
    RotationTrack,
    ScaleXTrack,
    ScaleYTrack,
    Shadow,
    ShapeLayer,
    StaggerSpec,
    Stroke,
    TimingSpec,
)
from quickthumb._export_video import _SlideAnimator
from quickthumb._parent_render import ParentNode

FONT = "assets/fonts/NotoSerif-Italic.ttf"


def track(kind, first, last):
    return kind(keyframes=[KeyframeSpec(time=0, value=first), KeyframeSpec(time=1, value=last)])


def motion(*tracks, stagger=None, start=0):
    spec = AnimationSpec.timeline(
        *tracks, timing=TimingSpec(start=start, duration=1), easing="linear"
    )
    if stagger is not None:
        spec.stagger = StaggerSpec(delay=stagger, target="lines")
    return spec


def text_scene(**options):
    settings: dict[str, Any] = {
        "position": (15, 10),
        "font": FONT,
        "size": 24,
        "color": "#FFFFFF",
        "line_height": 2,
        "animation": AnimationSpec.rise(
            distance=14, duration=0.5, stagger=0.4, target="lines", easing="linear"
        ),
    }
    settings.update(options)
    content = settings.pop("content", "ONE\nTWO\nTHREE")
    return (
        Canvas(400, 340)
        .null((60, 35), id="root")
        .text(content, parent="root", id="leaf", **settings)
    )


def group_scene(*, direction="column", gap=20, animation=None, child_motion=False):
    animation = animation or AnimationSpec.rise(
        distance=20, duration=0.5, stagger=0.4, target="children", easing="linear"
    )
    if isinstance(animation, AnimationSpec) and animation.stagger:
        animation.stagger.target = "children"
    children = [
        ShapeLayer(
            type="shape",
            shape="rectangle",
            position=(0, 0),
            width=22,
            height=12,
            color="#FFFFFF",
            animation=motion(track(PositionTrack, (0, 0), (90, 80))) if child_motion else None,
        )
        for _ in range(3)
    ]
    return (
        Canvas(240, 180)
        .null((35, 25), id="root")
        .group(
            children,
            position=(10, 10),
            direction=direction,
            gap=gap,
            padding=4,
            parent="root",
            id="leaf",
            animation=animation,
        )
    )


def turn(point, position, rotation, sx, sy):
    x, y = point[0] * sx, point[1] * sy
    angle = math.radians(rotation)
    return (
        position[0] + x * math.cos(angle) - y * math.sin(angle),
        position[1] + x * math.sin(angle) + y * math.cos(angle),
    )


@pytest.mark.parametrize("time", [0.23, 0.61, 1.17, 1.8])
def test_each_target_composes_three_ancestors_with_analytic_shear(time, monkeypatch):
    from quickthumb import _parent_render as parent

    canvas = text_scene(
        anchor=(0.2, 0.8),
        animation=motion(
            track(PositionTrack, (0, 8), (12, -3)),
            track(RotationTrack, 0, 25),
            track(ScaleXTrack, 0.8, 1.4),
            track(ScaleYTrack, 1, 0.7),
            stagger=0.4,
        ),
    )
    root = cast(Any, canvas.layers[0])
    root.animation = motion(track(ScaleXTrack, 1, 1.8), track(RotationTrack, 0, 35))
    canvas.null(
        (14, 8),
        id="middle",
        parent="root",
        rotation=17,
        animation=motion(track(ScaleYTrack, 1, 0.6), track(RotationTrack, 0, -22)),
    )
    canvas.null((9, 6), id="inner", parent="middle", rotation=-13)
    cast(Any, canvas.layers[1]).parent = "inner"
    animator = _SlideAnimator(canvas, {})
    node = animator._units[1].parent_node
    assert len(node.unit.target_images) == 3
    calls = []
    original = parent.affine_fragment

    def capture(image, matrix, size, **kwargs):
        calls.append((image.size, matrix))
        return original(image, matrix, size, **kwargs)

    monkeypatch.setattr(parent, "affine_fragment", capture)
    animator.frame_at(time)
    visible = [index for index in range(3) if time >= index * 0.4]
    assert len(calls) == len(visible)
    ancestor_t = min(1, time)
    for index, (padded_size, matrix) in zip(visible, calls, strict=True):
        source, offset = node.unit.target_images[index]
        size = source.size
        assert padded_size == (size[0] + 4, size[1] + 4)
        t = min(1, time - 0.4 * index)
        anchor = (size[0] * 0.2, size[1] * 0.8)
        for point in ((0, 0), (size[0], 0), (0, size[1]), size):
            target = turn(
                (point[0] - anchor[0], point[1] - anchor[1]),
                (12 * t + anchor[0], 8 - 11 * t + anchor[1]),
                25 * t,
                0.8 + 0.6 * t,
                1 - 0.3 * t,
            )
            local = (
                target[0] + node.origin[0] + offset[0] - node.padding,
                target[1] + node.origin[1] + offset[1] - node.padding,
            )
            inner = turn(local, (9, 6), -13, 1, 1)
            # A null's authored rotation follows its sampled scale/rotation.
            middle_body = turn(inner, (0, 0), 17, 1, 1)
            middle = turn(middle_body, (14, 8), -22 * ancestor_t, 1, 1 - 0.4 * ancestor_t)
            expected = turn(middle, (60, 35), 35 * ancestor_t, 1 + 0.8 * ancestor_t, 1)
            actual = (
                matrix[0] * (point[0] + 2) + matrix[1] * (point[1] + 2) + matrix[2],
                matrix[3] * (point[0] + 2) + matrix[4] * (point[1] + 2) + matrix[5],
            )
            assert actual == pytest.approx(expected, abs=1e-10)
        assert abs(matrix[0] * matrix[1] + matrix[3] * matrix[4]) > 0.01


@pytest.mark.parametrize("quality", ["standard", "high"])
def test_waiting_or_collapsed_last_target_does_not_hide_earlier_targets(quality):
    canvas = group_scene(animation=motion(track(ScaleXTrack, 0, 1), stagger=0.4))
    animator = _SlideAnimator(canvas, {}, quality=quality)
    node = animator._units[-1].parent_node
    assert len(node.unit.target_images) == 3
    # Aggregate motion takes the final target, whose X axis is still zero.
    for instant in (0.2, 0.6, 0.8):
        assert animator.frame_at(instant).getbbox() is not None
    assert node.plan.sample(0.8)[id(node)][3]
    assert animator.frame_at(0).getbbox() is None


@pytest.mark.parametrize("axis", [-1, 0, 1])
@pytest.mark.parametrize("quality", ["standard", "high"])
def test_reflected_targets_and_exact_ancestor_collapse(axis, quality):
    canvas = group_scene(animation=motion(track(ScaleXTrack, -1, -1), stagger=0.4))
    cast(Any, canvas.layers[0]).animation = motion(track(ScaleYTrack, axis, axis))
    cast(Any, canvas.layers[0]).position = (80, 120)
    animator = _SlideAnimator(canvas, {}, quality=quality)
    image = animator.frame_at(0.6)
    if axis == 0:
        assert image.getbbox() is None
    else:
        assert image.getbbox() is not None
        assert image.getchannel("A").point(lambda n: 255 if n > 127 else 0).getbbox() == (
            (94, 62, 116, 106) if axis < 0 else (94, 134, 116, 178)
        )


@pytest.mark.parametrize(
    "options",
    [
        {"align": "center", "rotation": 7},
        {"align": "bottom-right", "rotation": -7, "anchor": (0, 1)},
        {
            "effects": [
                Stroke(width=1, color="#FF0000"),
                Shadow(offset_x=2, offset_y=2, blur_radius=1, color="#00FF00"),
            ]
        },
        {"content": "ONE TWO THREE FOUR FIVE SIX", "max_width": 100},
    ],
)
def test_local_italic_effects_rotation_alignment_and_wrap_survive_offcanvas(options):
    reference = text_scene(**options)
    translated = text_scene(**options)
    cast(Any, translated.layers[0]).position = (360, 235)
    cast(Any, translated.layers[1]).position = (-285, -190)
    actual = _SlideAnimator(translated, {})
    expected = _SlideAnimator(reference, {})
    assert actual._units[-1].target_images
    for instant in (0.1, 0.5, 0.9, 1.8, 0.5):
        assert actual.frame_at(instant).tobytes() == expected.frame_at(instant).tobytes()
    assert translated._render_to_image().tobytes() == reference._render_to_image().tobytes()


def test_target_color_opacity_reveal_and_blur_are_independent_of_parent_appearance(monkeypatch):
    animation = motion(
        track(ColorTrack, "#FF0000", "#0000FF"),
        track(OpacityTrack, 0.3, 1),
        track(ClipProgressTrack, 0.3, 1),
        track(BlurTrack, 0, 2),
        stagger=0.4,
    )
    canvas = group_scene(animation=animation)
    leaf = cast(Any, canvas.layers[-1])
    for child in leaf.children:
        child.color = "#00000000"
        child.effects = [Stroke(width=1, color="#00FF00")]
    # A transparent parent carries visual animation which must never affect the leaf.
    canvas.layers[0] = ShapeLayer(
        type="shape",
        shape="rectangle",
        width=5,
        height=5,
        id="root",
        position=(35, 25),
        opacity=0,
        color="#FFFF00",
        animation=motion(
            track(OpacityTrack, 0, 0),
            track(BlurTrack, 4, 8),
            track(ClipProgressTrack, 0, 0),
            track(ColorTrack, "#00FF00", "#FFFF00"),
        ),
    )
    animator = _SlideAnimator(canvas, {})
    unit = animator._units[-1]
    assert len(unit.target_images) == 3
    bounds = [(image.size, pos) for image, pos in unit.target_images]
    cache = canvas._ctx.measure_cache
    original = dict(cache)
    frames = [animator.frame_at(t).tobytes() for t in (0.2, 0.6, 1, 1.8, 0.6)]
    assert frames[1] == frames[-1] and len(set(frames)) == 4
    assert [(image.size, pos) for image, pos in unit.target_images] == bounds
    assert canvas._ctx.measure_cache is cache and cache == original
    # Reconstruct each target as a separately animated whole group containing
    # just that shape, using the established parent compositor as the oracle.
    at = 1.0
    expected = Image.new("RGBA", (canvas.width, canvas.height))
    for index in range(3):
        single = Canvas(canvas.width, canvas.height).null((35, 25), id="root")
        spec = animation.model_copy(deep=True, update={"stagger": None})
        spec.timing = TimingSpec(start=0.4 * index, duration=1)
        single.shape(
            "rectangle",
            (14, 14 + 32 * index),
            22,
            12,
            "#00000000",
            parent="root",
            effects=[Stroke(width=1, color="#00FF00")],
            animation=spec,
        )
        expected.alpha_composite(single.render_frame(at))
    assert animator.frame_at(at).tobytes() == expected.tobytes()

    def fail(*args, **kwargs):
        raise RuntimeError("paint")

    monkeypatch.setattr(canvas._groups, "render_group_layer", fail)
    with pytest.raises(RuntimeError, match="paint"):
        animator.frame_at(0.6)
    assert canvas._ctx.measure_cache is cache and cache == original
    assert canvas._ctx.motion_time is None


def test_static_targets_are_reused_without_mutating_pixels(monkeypatch):
    canvas = text_scene()
    animator = _SlideAnimator(canvas, {})
    unit = animator._units[-1]
    original = [image.tobytes() for image, _ in unit.target_images]
    monkeypatch.setattr(ParentNode, "render_source", lambda *a, **k: pytest.fail("repaint"))
    for instant in (0.1, 0.6, 1.2, 0.6):
        animator.frame_at(instant)
    assert [image.tobytes() for image, _ in unit.target_images] == original


@pytest.mark.parametrize(
    "direction,gap,separated", [("column", 20, True), ("row", 20, False), ("column", 0, False)]
)
def test_group_bands_keep_existing_fallback_and_override_child_motion(direction, gap, separated):
    canvas = group_scene(direction=direction, gap=gap, child_motion=True)
    fixed = group_scene(direction=direction, gap=gap)
    animator = _SlideAnimator(canvas, {})
    assert bool(animator._units[-1].target_images) == separated
    assert len(animator._units[-1].target_timelines) == 3
    for instant in (0.1, 0.7, 1.3, 0.7):
        assert animator.frame_at(instant).tobytes() == fixed.render_frame(instant).tobytes()


@pytest.mark.parametrize(
    "content,target",
    [
        ("ONE", "lines"),
        ("ONE TWO", "words"),
        ("ONE", "characters"),
        ("ONE\n\nTHREE", "lines"),
        ("", "lines"),
    ],
)
def test_semantic_targets_preserve_whole_source_approximation(content, target):
    canvas = text_scene(
        content=content,
        animation=AnimationSpec.rise(
            distance=14, duration=0.5, stagger=0.4, target=target, easing="linear"
        ),
    )
    animator = _SlideAnimator(canvas, {})
    assert not animator._units[-1].target_images
    assert animator.frame_at(0.3).tobytes() == canvas.render_frame(0.3).tobytes()


def test_delayed_target_clocks_continue_after_parent_and_are_encoded_in_gif():
    canvas = group_scene()
    cast(Any, canvas.layers[0]).animation = AnimationSpec.rise(distance=0, duration=0.1)
    animator = _SlideAnimator(canvas, {})
    assert animator.duration == pytest.approx(1.3)
    segments = animator.segments(0.1, 1.7)
    assert segments[0][0] == 0.1 and segments[-2][1] == 1.3
    assert all(active for _, _, active in segments[:-1])
    assert segments[-1] == (1.3, 1.7, False)
    frames = [animator.frame_at(t).tobytes() for t in (0, 0.4, 0.7, 1.3, 2, 0.7)]
    assert frames[2] == frames[-1] and frames[3] == frames[4]
    with Image.open(BytesIO(canvas.to_gif(fps=10, hold=0.2))) as gif:
        instant, later, durations = 0, [], []
        for index in range(getattr(gif, "n_frames", 1)):
            gif.seek(index)
            duration = gif.info["duration"] / 1000
            durations.append(duration)
            if 0.8 <= instant < 1.3:
                later.append(gif.convert("RGBA").tobytes())
            instant += duration
    assert len(set(later)) >= 4
    assert sum(durations) == pytest.approx(1.5)


@pytest.mark.parametrize("quality", ["standard", "high"])
def test_spawn_and_serial_gif_bytes_match(tmp_path, quality):
    canvas = group_scene(
        animation=motion(
            track(ColorTrack, "#FF0000", "#0000FF"), track(RotationTrack, -12, 12), stagger=0.4
        )
    )
    paths = [tmp_path / "serial.gif", tmp_path / "spawn.gif"]
    for workers, path in zip((1, 2), paths, strict=True):
        canvas.render(str(path), animation=GifOptions(fps=5, quality=quality, workers=workers))
    assert paths[0].read_bytes() == paths[1].read_bytes()


@pytest.mark.parametrize("quality", ["standard", "high"])
def test_fractional_target_edges_match_identity_parent(quality):
    from quickthumb import NullLayer

    base = Canvas(600, 520).text(
        "ONE\nTWO\nTHREE",
        position=(260, 220),
        font="assets/fonts/Roboto-Medium.ttf",
        size=40,
        line_height=2.5,
        animation=AnimationSpec.rise(
            distance=30, duration=1, stagger=0.4, target="lines", easing="linear"
        ),
    )
    linked = Canvas(
        600,
        520,
        layers=[
            NullLayer(type="null", id="root"),
            cast(Any, base.layers[0]).model_copy(update={"parent": "root"}),
        ],
    )
    actual, expected = (
        _SlideAnimator(linked, {}, quality=quality),
        _SlideAnimator(base, {}, quality=quality),
    )
    for instant in (0.15, 0.31, 0.47, 0.65, 0.95, 1.15, 1.65, 1.8, 0.15):
        assert actual.frame_at(instant).tobytes() == expected.frame_at(instant).tobytes()


def test_composed_text_keeps_overlap_and_delayed_target_endpoints():
    canvas = text_scene(
        animation=[
            AnimationSpec.rise(
                distance=20, duration=0.5, stagger=0.4, target="lines", easing="linear"
            ),
            AnimationSpec.fade(duration=0.2, easing="linear"),
        ]
    )
    animator = _SlideAnimator(canvas, {})
    unit = animator._units[-1]
    assert len(unit.target_images) == 3
    assert [[event.start for event in timeline.events] for timeline in unit.target_timelines] == [
        [0, 0.5],
        [0.4, 0.5],
        [0.8, 0.5],
    ]
    assert animator.duration == pytest.approx(1.3)
    frames = [animator.frame_at(t).tobytes() for t in (0.2, 0.5, 0.6, 1.3, 2, 0.6)]
    assert frames[2] == frames[-1] and frames[3] == frames[4]
    assert len(set(frames)) == 4


def test_composed_group_keeps_existing_whole_block_cardinality_limitation():
    canvas = group_scene(
        animation=[
            AnimationSpec.rise(
                distance=20, duration=0.5, stagger=0.4, target="children", easing="linear"
            ),
            AnimationSpec.fade(duration=0.2, easing="linear"),
        ]
    )
    cast(Any, canvas.layers[0]).position = (0, 0)
    original = Canvas(
        240, 180, layers=[cast(Any, canvas.layers[-1]).model_copy(update={"parent": None})]
    )
    actual, expected = _SlideAnimator(canvas, {}), _SlideAnimator(original, {})
    assert not actual._units[-1].target_images and not expected._units[-1].target_images
    assert len(actual._units[-1].target_timelines) == len(expected._units[-1].target_timelines) == 1
    assert actual.duration == expected.duration == pytest.approx(0.7)
    for instant in (0.1, 0.3, 0.5, 0.8, 2):
        assert actual.frame_at(instant).tobytes() == expected.frame_at(instant).tobytes()


def test_color_reference_keeps_fully_transparent_local_text_geometry():
    spec = motion(track(ColorTrack, "#FF0000", "#0000FF"), stagger=0.4)
    canvas = text_scene(color="#00000000", animation=spec)
    animator = _SlideAnimator(canvas, {})
    unit = animator._units[-1]
    assert unit.image is None and len(unit.target_images) == 3
    assert animator.frame_at(0.2).getbbox() is not None
    reference = text_scene(animation=spec)
    for instant in (0.2, 0.6, 1, 1.8):
        assert animator.frame_at(instant).tobytes() == reference.render_frame(instant).tobytes()


def test_separated_active_windows_keep_intervening_holds():
    canvas = text_scene(
        animation=AnimationSpec.rise(duration=0.2, stagger=0.7, target="lines", easing="linear")
    )
    animator = _SlideAnimator(canvas, {})
    segments = animator.segments(0, 2)
    assert [(round(start, 6), round(end, 6), active) for start, end, active in segments] == [
        (0, 0.2, True),
        (0.2, 0.7, False),
        (0.7, 0.9, True),
        (0.9, 1.4, False),
        (1.4, 1.6, True),
        (1.6, 2, False),
    ]
    assert animator.frame_at(0.3).tobytes() == animator.frame_at(0.6).tobytes()
    assert animator.frame_at(1).tobytes() == animator.frame_at(1.3).tobytes()


def test_group_override_suppresses_descendant_viewport_and_visualization_motion(tmp_path):
    from quickthumb import GroupLayer, ImageLayer, QRCodeLayer

    path = tmp_path / "colors.png"
    image = Image.new("RGB", (30, 18), "red")
    image.paste("blue", (15, 0, 30, 18))
    image.save(path)
    canvas = group_scene()
    group = cast(GroupLayer, canvas.layers[-1])
    group.children[1:] = [
        ImageLayer(
            type="image",
            path=str(path),
            position=(0, 0),
            width=30,
            height=18,
            animation=AnimationSpec.ken_burns(duration=1),
        ),
        QRCodeLayer(
            type="qr_code",
            data="static rows",
            size=32,
            animation=AnimationSpec.qr_reveal(duration=1),
        ),
    ]
    fixed = Canvas.from_json(canvas.to_json())
    for child in cast(GroupLayer, fixed.layers[-1]).children:
        cast(Any, child).animation = None
    actual = _SlideAnimator(canvas, {})
    assert len(actual._units[-1].target_images) == 3
    for instant in (0.1, 0.5, 0.9, 1.3):
        assert actual.frame_at(instant).tobytes() == fixed.render_frame(instant).tobytes()


def test_parent_stagger_visual_snapshot():
    from pathlib import Path

    from examples.parent_stagger import build_scene

    actual = build_scene().render_frame(0.95)
    expected = Image.open(Path(__file__).parent / "snapshots/parent_stagger.png").convert("RGBA")
    assert (actual.size, actual.tobytes()) == (expected.size, expected.tobytes())


def test_reflected_italic_targets_use_left_associated_ancestor_frame():
    from quickthumb import GroupLayer, NullLayer, TextLayer
    from quickthumb._export_base import split_into_bands
    from quickthumb._parent_render import affine_fragment

    def matrix(x=0, y=0, angle=0, sx=1, anchor=(0, 0), size=(0, 0)):
        r = math.radians(angle)
        a, b, d, e = math.cos(r) * sx, -math.sin(r), math.sin(r) * sx, math.cos(r)
        px, py = anchor[0] * size[0], anchor[1] * size[1]
        return a, b, x + px - a * px - b * py, d, e, y + py - d * px - e * py

    def product(left, right):
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

    children = [
        TextLayer(type="text", content=text, size=37, color="#CC55559F", font=FONT)
        for text in ("One", "jfy", "Three")
    ]
    reference = GroupLayer(type="group", children=children, gap=27, position=(10, 10))
    bands = split_into_bands(Canvas(600, 500, layers=[reference])._render_to_image(), 3)
    assert bands is not None
    spec = motion(track(ScaleXTrack, -1, -1), stagger=0.4)
    spec.stagger = StaggerSpec(delay=0.4, target="children")
    group = reference.model_copy(
        update={"position": (71, 41), "parent": "root", "anchor": (0.1, 0.9), "animation": spec}
    )
    canvas = Canvas(
        600,
        500,
        layers=[NullLayer(type="null", id="root", position=(330, 270), rotation=180), group],
    )
    origin = product(matrix(330, 270, 180), matrix(71, 41))
    expected = Image.new("RGBA", (600, 500))
    for source, (x, y) in bands:
        transform = product(origin, matrix(x - 10, y - 10))
        transform = product(transform, matrix(sx=-1, anchor=(0.1, 0.9), size=source.size))
        transform = product(transform, matrix(-2, -2))
        padded = Image.new("RGBA", (source.width + 4, source.height + 4))
        padded.paste(source, (2, 2))
        result = affine_fragment(padded, transform, expected.size)
        assert result is not None
        expected.alpha_composite(*result)
    assert canvas.render_frame(1.1).tobytes() == expected.tobytes()
