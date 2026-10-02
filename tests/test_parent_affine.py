"""Explicit parent-local geometry, independent drawing order and full shear."""

import math
from typing import Any, cast

import pytest
from PIL import Image
from quickthumb import (
    AnimationSpec,
    Canvas,
    GroupLayer,
    KeyframeSpec,
    NullLayer,
    OpacityTrack,
    RotationTrack,
    ScaleXTrack,
    ScaleYTrack,
    ShapeLayer,
    TimingSpec,
)
from quickthumb._export_video import _SlideAnimator
from quickthumb._parent_render import IDENTITY, affine_fragment, multiply


def track(cls, start, end=None):
    return cls(
        keyframes=[
            KeyframeSpec(time=0, value=start),
            KeyframeSpec(time=1, value=start if end is None else end),
        ]
    )


def animation(*tracks):
    return AnimationSpec.timeline(*tracks, timing=TimingSpec(duration=1), easing="linear")


def shape(position=(10, 20), parent="root", **kwargs):
    return ShapeLayer(
        type="shape",
        shape="rectangle",
        position=position,
        width=20,
        height=10,
        color="#FF0000",
        parent=parent,
        **kwargs,
    )


def test_parent_local_position_and_offcanvas_source_survive():
    for parent, child, expected in [
        ((100, 50), (10, 20), (110, 70, 130, 80)),
        ((120, 10), (-100, 5), (20, 15, 40, 25)),
    ]:
        canvas = Canvas(160, 120).null(parent, id="root")
        canvas.layers = [*canvas.layers, shape(child)]
        assert canvas.render_frame(0).getbbox() == expected
        assert _SlideAnimator(canvas, {}).frame_at(0).tobytes() == canvas.render_frame(0).tobytes()


def test_child_before_parent_keeps_authored_paint_order():
    child = shape((0, 0), parent="root")
    parent = shape((30, 20), parent=None, id="root").model_copy(update={"color": "#FFFFFF"})
    canvas = Canvas(100, 80, layers=[child, parent])
    assert canvas.render_frame(0).getpixel((35, 25)) == (255, 255, 255, 255)
    canvas.layers = [parent, child]
    assert canvas.render_frame(0).getpixel((35, 25)) == (255, 0, 0, 255)


def step(point, position, angle, sx, sy):
    x, y = point[0] * sx, point[1] * sy
    rad = math.radians(angle)
    return (
        position[0] + x * math.cos(rad) - y * math.sin(rad),
        position[1] + x * math.sin(rad) + y * math.cos(rad),
    )


@pytest.mark.parametrize("time", [0, 0.2, 0.5, 1, 1.5])
def test_three_levels_compose_full_affine_with_shear(time):
    canvas = Canvas(250, 200).null(
        (70, 50), id="a", animation=animation(track(ScaleXTrack, 1, 2), track(RotationTrack, 0, 30))
    )
    canvas.null(
        (10, 5),
        id="b",
        parent="a",
        animation=animation(track(ScaleYTrack, 1, 0.5), track(RotationTrack, 0, 40)),
    )
    canvas.null((15, 10), id="c", parent="b", rotation=20)
    canvas.layers = [*canvas.layers, shape((0, 0), "c")]
    animator = _SlideAnimator(canvas, {})
    leaf = animator._units[-1].parent_node
    world = leaf.plan.sample(time)[id(leaf)][1]
    t = min(time, 1)
    for point in [(0, 0), (20, 0), (0, 10), (20, 10)]:
        expected = step(
            step(step(point, (15, 10), 20, 1, 1), (10, 5), 40 * t, 1, 1 - 0.5 * t),
            (70, 50),
            30 * t,
            1 + t,
            1,
        )
        actual = (
            world[0] * point[0] + world[1] * point[1] + world[2],
            world[3] * point[0] + world[4] * point[1] + world[5],
        )
        assert actual == pytest.approx(expected, abs=1e-10)
    if t > 0:
        assert abs(world[0] * world[1] + world[3] * world[4]) > 0.01
    assert animator.frame_at(time).tobytes() == canvas.render_frame(time).tobytes()


@pytest.mark.parametrize("opacity", [0, 0.5, 1])
def test_parent_opacity_does_not_inherit_or_erase_pivot(opacity):
    parent = shape(
        (100, 50),
        parent=None,
        id="root",
        opacity=opacity,
        anchor=(0, 0),
        animation=animation(track(RotationTrack, 90), track(OpacityTrack, 0)),
    )
    canvas = Canvas(160, 120, layers=[parent, shape((10, 0))])
    assert canvas.render_frame(0.5).getbbox() == (90, 60, 100, 80)
    assert canvas.render_frame(0.5).getpixel((95, 65)) == (255, 0, 0, 255)


@pytest.mark.parametrize("scale", [-1, 0, 1, 2])
@pytest.mark.parametrize("quality", ["standard", "high"])
def test_inherited_reflection_and_zero_collapse(scale, quality):
    canvas = Canvas(100, 80).null(
        (40, 30), id="root", animation=animation(track(ScaleXTrack, scale))
    )
    canvas.layers = [*canvas.layers, shape((0, 0))]
    image = _SlideAnimator(canvas, {}, quality=quality).frame_at(0.5)
    if scale == 0:
        assert image.getbbox() is None
    else:
        assert image.getbbox() is not None
        opaque = image.getchannel("A").point(lambda n: 255 if n > 127 else 0)
        assert opaque.getbbox() == (
            (20 if scale < 0 else 40),
            30,
            (40 if scale < 0 else 40 + 20 * scale),
            40,
        )


def test_rotated_visible_parent_inherits_static_geometry_once():
    parent = shape((50, 40), parent=None, id="root", rotation=90)
    child = shape((0, 0)).model_copy(update={"width": 4, "height": 2, "color": "#00FF00"})
    canvas = Canvas(120, 100, layers=[parent, child])
    image = canvas.render_frame(0)
    assert image.getbbox() == (50, 40, 60, 60)
    assert image.getpixel((59, 42)) == (0, 255, 0, 255)
    assert image.getpixel((55, 52)) == (255, 0, 0, 255)


def test_group_padding_is_not_an_extra_child_transform():
    canvas = Canvas(150, 100).group(
        [{"type": "shape", "shape": "rectangle", "width": 20, "height": 10, "color": "#FFFFFF"}],
        position=(50, 40),
        padding=10,
        id="root",
    )
    canvas.layers = [*canvas.layers, shape((0, 0))]
    image = canvas.render_frame(0)
    assert image.getpixel((50, 40)) == (255, 0, 0, 255)


def test_parent_axes_are_applied_in_one_affine_resample(monkeypatch):
    source = Image.new("RGBA", (8, 6), "red")
    calls = []
    original = Image.Image.transform
    monkeypatch.setattr(
        Image.Image,
        "transform",
        lambda self, *args, **kwargs: (
            calls.append(args) if self is source else None,
            original(self, *args, **kwargs),
        )[1],
    )
    result = affine_fragment(source, (1, 0.5, 10, 0.25, 1, 8), (100, 100))
    assert result and len(calls) == 1
    assert source.getpixel((0, 0)) == (255, 0, 0, 255)
    assert multiply(IDENTITY, IDENTITY) == IDENTITY


def test_very_deep_null_chain_is_iterative():
    nodes = [
        NullLayer(type="null", id=f"n{index}", parent=f"n{index + 1}", position=(0, 0))
        for index in range(1100)
    ]
    canvas = Canvas(
        40, 30, layers=[shape((0, 0), "n0"), *nodes, NullLayer(type="null", id="n1100")]
    )
    assert canvas.render_frame(0).getbbox() == (0, 0, 20, 10)


@pytest.mark.parametrize("align", [None, "center", "bottom-right"])
@pytest.mark.parametrize("rich", [False, True])
@pytest.mark.parametrize("rotation", [0, 31, 90])
def test_linked_text_preserves_full_italic_ink_and_static_rotation(align, rich, rotation):
    from quickthumb import TextPart

    content = (
        [TextPart(text="jfQgy", size=70), TextPart(text="\njQ", size=42)] if rich else "jfQgy\njQ"
    )
    base = Canvas(500, 400).text(
        content,
        font="assets/fonts/NotoSerif-Italic.ttf",
        size=70,
        color="#FFFFFF",
        position=(230, 180),
        align=align,
        rotation=rotation,
    )
    linked = Canvas(
        500,
        400,
        layers=[
            NullLayer(type="null", id="root"),
            cast(Any, base.layers[0]).model_copy(update={"parent": "root"}),
        ],
    )
    assert linked.render_frame(0).tobytes() == base.render_frame(0).tobytes()


def test_parented_image_keeps_source_viewport_zoom_and_child_outer_geometry(tmp_path):
    from quickthumb import ScaleTrack

    source = Image.new("RGB", (60, 20), "green")
    source.paste("red", (0, 0, 20, 20))
    source.paste("blue", (40, 0, 60, 20))
    path = tmp_path / "strip.png"
    source.save(path)
    base = Canvas(100, 80).image(
        str(path), (20, 20), width=60, height=20, animation=animation(track(ScaleTrack, 1, 2))
    )
    linked = Canvas(
        100,
        80,
        layers=[
            NullLayer(type="null", id="root"),
            cast(Any, base.layers[0]).model_copy(update={"parent": "root", "id": "image"}),
        ],
    )
    animator = _SlideAnimator(linked, {})
    assert animator._units[1].component_duration == 1
    for instant in (0, 0.5, 1):
        assert linked.render_frame(instant).tobytes() == base.render_frame(instant).tobytes()
    assert linked.render_frame(0).tobytes() != linked.render_frame(1).tobytes()
    linked.layers = [
        *linked.layers,
        shape((0, 0), "image").model_copy(update={"width": 2, "height": 2, "color": "#FFFFFF"}),
    ]
    assert (
        linked.render_frame(0).getpixel((20, 20))
        == linked.render_frame(1).getpixel((20, 20))
        == (255, 255, 255, 255)
    )


@pytest.mark.parametrize("effect", ["wipe", "box", "circle", "fade"])
def test_legacy_reveal_uses_visible_fragment_not_source_padding(effect):
    from quickthumb import Box, Circle, Fade, Wipe

    animation = {
        "wipe": Wipe(direction="right", duration=1, easing="linear"),
        "box": Box(duration=1, easing="linear"),
        "circle": Circle(duration=1, easing="linear"),
        "fade": Fade(duration=1, easing="linear"),
    }[effect]
    base = Canvas(100, 80, layers=[shape((20, 20), None, animation=animation)])
    linked = Canvas(
        100,
        80,
        layers=[
            NullLayer(type="null", id="root"),
            cast(Any, base.layers[0]).model_copy(update={"parent": "root"}),
        ],
    )
    expected, actual = _SlideAnimator(base, {}), _SlideAnimator(linked, {})
    for instant in (0, 0.1, 0.25, 0.5, 0.75, 1):
        assert expected.frame_at(instant).tobytes() == actual.frame_at(instant).tobytes()


def test_prepared_parent_sources_are_released_without_waiting_for_cycle_collection():
    import weakref

    animator = _SlideAnimator(
        Canvas(100, 80, layers=[NullLayer(type="null", id="root"), shape()]), {}
    )
    plan = weakref.ref(animator._units[0].parent_plan)
    del animator
    assert plan() is None


@pytest.mark.parametrize("kind", ["text", "image", "svg", "chart", "qr_code", "group"])
def test_identity_parent_preserves_diverse_static_source_pixels(tmp_path, kind):
    from quickthumb import BarChartSpec

    canvas = Canvas(200, 150)
    if kind == "text":
        canvas.text("Quickthumb", position=(40, 35), font="assets/fonts/Roboto-Medium.ttf", size=20)
    elif kind == "image":
        path = tmp_path / "image.png"
        image = Image.new("RGBA", (30, 20), (20, 70, 120, 180))
        image.paste((200, 0, 80, 255), (10, 5, 20, 15))
        image.save(path)
        canvas.image(str(path), (40, 35), width=30, height=20)
    elif kind == "svg":
        path = tmp_path / "image.svg"
        path.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="30" height="20">'
            '<rect width="30" height="20" fill="red"/></svg>'
        )
        canvas.svg(str(path), (40, 35))
    elif kind == "chart":
        canvas.chart(BarChartSpec(data=[1, 3, 2]), (40, 35), 60, 40)
    elif kind == "qr_code":
        canvas.qr_code("test", (40, 35), size=64)
    else:
        canvas.group(
            [
                {
                    "type": "shape",
                    "shape": "rectangle",
                    "width": 20,
                    "height": 10,
                    "color": "#FFFFFF",
                },
                {
                    "type": "text",
                    "content": "label",
                    "font": "assets/fonts/Roboto-Medium.ttf",
                    "size": 14,
                },
            ],
            position=(40, 35),
            padding=8,
            gap=5,
        )
    linked = Canvas(
        200,
        150,
        layers=[
            NullLayer(type="null", id="root"),
            cast(Any, canvas.layers[0]).model_copy(update={"parent": "root"}),
        ],
    )
    assert linked.render_frame(0).tobytes() == canvas.render_frame(0).tobytes()


@pytest.mark.parametrize("quality", ["standard", "high"])
def test_public_gif_spawn_worker_bytes_match_serial(tmp_path, quality):
    from quickthumb import GifOptions

    canvas = (
        Canvas(80, 60)
        .background(color="#101820")
        .null(
            (30, 20),
            id="root",
            animation=animation(track(RotationTrack, 0, 30), track(ScaleXTrack, 1, 1.5)),
        )
    )
    canvas.layers = [*canvas.layers, shape((0, 0))]
    single, parallel = tmp_path / "one.gif", tmp_path / "two.gif"
    canvas.render(str(single), animation=GifOptions(fps=4, quality=quality))
    canvas.render(str(parallel), animation=GifOptions(fps=4, quality=quality, workers=2))
    assert single.read_bytes() == parallel.read_bytes()


def test_parent_morph_falls_back_to_fade_and_strict_policy_reports_it():
    from quickthumb import Deck, ExportPolicy, Morph
    from quickthumb.errors import RenderingError

    first = Canvas(100, 80).background(color="#000000").null((20, 20), id="root")
    first.layers = [*first.layers, shape((0, 0))]
    second = Canvas(100, 80).background(color="#0000FF").null((50, 40), id="root")
    second.layers = [*second.layers, shape((0, 0))]
    deck = Deck(100, 80).slide(first).slide(second, transition=Morph(duration=1))
    diagnostics = deck.validate_export("raster")
    assert next(item for item in diagnostics if item.feature == "parent_morph").fallback == "fade"
    with pytest.raises(RenderingError, match="fade fallback"):
        deck.validate_export("raster", ExportPolicy(unsupported_motion="error"))
    frames = deck.sample(time=[0, 3, 3.5, 4]).frames
    assert len(frames) == 4


@pytest.mark.parametrize("target", ["raster", "video"])
def test_raster_parent_capability_matches_supported_or_rejected_combinations(target):
    from quickthumb import ExportPolicy, LayerClip
    from quickthumb.errors import RenderingError

    canvas = Canvas(100, 80, layers=[NullLayer(type="null", id="root"), shape()])
    assert (
        next(item for item in canvas.validate_export(target) if item.feature == "parent").support
        == "full"
    )
    assert canvas.validate_export(target, ExportPolicy(unsupported_motion="error"))
    layers = canvas.layers
    layers[1] = GroupLayer(
        type="group",
        parent="root",
        children=[
            shape(position=(0, 0), parent=None).model_copy(
                update={
                    "clip": LayerClip(position=(0, 0), width=10, height=10),
                    "animation": AnimationSpec.fade(duration=1),
                }
            )
        ],
    )
    canvas.layers = layers
    assert (
        next(item for item in canvas.validate_export(target) if item.feature == "parent").support
        == "unsupported"
    )
    with pytest.raises(RenderingError, match="descendant boundaries cannot animate descendants"):
        canvas.validate_export(target, ExportPolicy(unsupported_motion="error"))


def test_unsupported_parent_combination_does_not_overwrite_earlier_deck_outputs(tmp_path):
    from quickthumb import Deck, LayerClip
    from quickthumb.errors import RenderingError

    canvas = Canvas(
        100,
        80,
        layers=[
            NullLayer(type="null", id="root"),
            GroupLayer(
                type="group",
                parent="root",
                children=[
                    shape(position=(0, 0), parent=None).model_copy(
                        update={
                            "clip": LayerClip(position=(0, 0), width=10, height=10),
                            "animation": AnimationSpec.fade(duration=1),
                        }
                    )
                ],
            ),
        ],
    )
    deck = Deck(100, 80).slide(Canvas(100, 80)).slide(canvas)
    destination = tmp_path / "slides.png"
    first = tmp_path / "slides_01.png"
    first.write_bytes(b"EXISTING")
    with pytest.raises(RenderingError, match="descendant boundaries cannot animate descendants"):
        deck.render(str(destination))
    assert first.read_bytes() == b"EXISTING"


@pytest.mark.parametrize("color,opacity", [("#FFFFFF", 0), ("#FFFFFF00", 1)])
def test_transparent_fill_and_zero_opacity_keep_same_polygon_parent_geometry(color, opacity):
    parent = ShapeLayer(
        type="shape",
        shape="polygon",
        position=(100, 100),
        width=100,
        height=80,
        points=[(0.1, 0.1), (0.4, 0.1), (0.1, 0.4)],
        color=color,
        opacity=opacity,
        id="root",
        anchor=(0, 0),
        animation=animation(track(RotationTrack, 90)),
    )
    child = shape((0, 0)).model_copy(update={"width": 4, "height": 4})
    canvas = Canvas(240, 200, layers=[parent, child])
    assert canvas.render_frame(0.5).getbbox() == (108, 98, 112, 102)


@pytest.mark.parametrize("kind", ["chart", "qr"])
def test_parented_component_reveal_is_not_clipped_twice(kind):
    from quickthumb import BarChartSpec

    canvas = Canvas(160, 100)
    if kind == "chart":
        canvas.chart(
            BarChartSpec(data=[1, 2, 3]),
            (20, 20),
            120,
            60,
            animation=AnimationSpec.bar_grow(duration=1),
        )
    else:
        canvas.qr_code(
            "parent geometry", (20, 20), size=64, animation=AnimationSpec.qr_reveal(duration=1)
        )
    linked = Canvas(
        160,
        100,
        layers=[
            NullLayer(type="null", id="root"),
            cast(Any, canvas.layers[0]).model_copy(update={"parent": "root"}),
        ],
    )
    for instant in (0, 0.25, 0.5, 1):
        assert linked.render_frame(instant).tobytes() == canvas.render_frame(instant).tobytes()


def test_singular_ancestor_stays_collapsed_after_rotated_descendants():
    canvas = Canvas(150, 100).null(
        (50, 40), id="root", animation=animation(track(ScaleXTrack, 0), track(RotationTrack, 33))
    )
    canvas.null((15, 10), id="branch", parent="root", rotation=41)
    canvas.layers = [*canvas.layers, shape((0, 0), "branch", rotation=19)]
    assert canvas.render_frame(0.5).getbbox() is None


def test_parent_visual_properties_do_not_inherit_to_explicit_child():
    from quickthumb import BlurTrack, ColorTrack

    parent = shape(
        (40, 30),
        None,
        id="root",
        opacity=0,
        animation=animation(track(BlurTrack, 8), track(ColorTrack, "#0000FF")),
    )
    canvas = Canvas(100, 80, layers=[parent, shape((0, 0)).model_copy(update={"color": "#00FF00"})])
    image = canvas.render_frame(0.5)
    assert image.getbbox() == (40, 30, 60, 40)
    assert image.getpixel((40, 30)) == (0, 255, 0, 255)


def test_parent_affine_visual_snapshot():
    from pathlib import Path

    from examples.parent_transforms import build_scene

    canvas = build_scene()
    strip = Image.new("RGBA", (1440, 300))
    for index, instant in enumerate((0, 0.5, 1)):
        strip.paste(canvas.render_frame(instant), (index * 480, 0))
    expected = Image.open(Path(__file__).parent / "snapshots/parent_affine.png").convert("RGBA")
    assert strip.size == expected.size and strip.tobytes() == expected.tobytes()


@pytest.mark.parametrize("composition", [False, True])
def test_parented_real_video_reverse_seeks_static_rotation_and_captions(tmp_path, composition):
    import shutil
    import subprocess

    from quickthumb.models import VideoCaption

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg renders the real video source")
    path = tmp_path / "source.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=32x24:rate=4:duration=1",
            "-c:v",
            "libx264",
            "-threads",
            "1",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        check=True,
        timeout=20,
    )
    captions = [
        VideoCaption(
            text="Fixed overlay",
            position=(110, 95),
            font="assets/fonts/Roboto-Medium.ttf",
            size=12,
            start=0,
            end=1,
        )
    ]
    base = Canvas(180, 140).video(str(path), (50, 40), 48, 36, rotation=31, captions=captions)
    linked = (
        Canvas(180, 140)
        .null((30, 10), id="root")
        .video(str(path), (20, 30), 48, 36, rotation=31, captions=captions, parent="root")
    )
    if composition:
        from quickthumb import LayerClip, LayerMask

        for layer, offset in ((base.layers[0], (30, 10)), (linked.layers[1], (0, 0))):
            cast(Any, layer).clip = LayerClip(
                position=(25 + offset[0], 35 + offset[1]), width=35, height=30, border_radius=6
            )
            cast(Any, layer).mask = LayerMask(
                shape="ellipse",
                position=(20 + offset[0], 30 + offset[1]),
                width=45,
                height=40,
                opacity=0.6,
            )
    animator = _SlideAnimator(linked, {})
    try:
        for instant in (0.75, 0.25, 0, 1, 1.25):
            assert animator.frame_at(instant).tobytes() == base.render_frame(instant).tobytes()
    finally:
        linked._ctx.close_video_decoders()
    assert not linked._ctx.video_decoder_cache


def test_unlinked_runs_keep_grouping_and_parent_sources_are_reused(monkeypatch):
    canvas = Canvas(160, 120).background(color="#000000")
    canvas.shape("rectangle", (0, 0), 5, 5, "#FFFFFF").shape("rectangle", (8, 0), 5, 5, "#FFFFFF")
    canvas.null((60, 40), id="root", animation=animation(track(RotationTrack, 0, 25)))
    canvas.layers = [*canvas.layers, shape((0, 0))]
    canvas.shape("rectangle", (100, 100), 5, 5, "#FFFFFF").shape(
        "rectangle", (110, 100), 5, 5, "#FFFFFF"
    )
    animator = _SlideAnimator(canvas, {})
    assert [len(unit.layers) for unit in animator._units] == [3, 1, 1, 2]
    assert [unit.parent_node is not None for unit in animator._units] == [False, True, True, False]
    plan = animator._units[1].parent_plan
    original = plan.sample
    calls = []
    monkeypatch.setattr(plan, "sample", lambda time: (calls.append(time), original(time))[1])
    monkeypatch.setattr(
        canvas, "_render_layer", lambda *args: pytest.fail("static source repainted")
    )
    for instant in (0, 0.25, 0.75, 1):
        animator.frame_at(instant)
    assert calls == [0, 0.25, 0.75, 1]


@pytest.mark.parametrize("kind", ["stagger", "independent_group", "mask", "backdrop"])
def test_unsupported_local_source_boundaries_are_explicit(kind):
    from quickthumb import BackdropBlur, LayerMask
    from quickthumb.errors import RenderingError

    canvas = Canvas(160, 120).null(id="root")
    if kind == "stagger":
        canvas.layers = [
            *canvas.layers,
            shape(animation=AnimationSpec.rise(stagger=0.1, target="characters")),
        ]
    elif kind == "independent_group":
        canvas.group(
            [shape((0, 0), None, animation=animation(track(RotationTrack, 0, 30)))], parent="root"
        )
    elif kind == "mask":
        canvas.layers = [
            *canvas.layers,
            GroupLayer(
                type="group",
                parent="root",
                children=[
                    shape(position=(0, 0), parent=None).model_copy(
                        update={
                            "mask": LayerMask(
                                shape="ellipse", position=(0, 0), width=20, height=20
                            ),
                            "animation": AnimationSpec.fade(duration=1),
                        }
                    )
                ],
            ),
        ]
    else:
        canvas.layers = [*canvas.layers, shape()]
        canvas.shape("rectangle", (0, 0), 80, 60, "#FFFFFF", effects=[BackdropBlur(radius=2)])
    diagnostic = next(item for item in canvas.validate_export("raster") if item.feature == "parent")
    assert diagnostic.support == "unsupported"
    with pytest.raises(RenderingError) as error:
        canvas.render_frame(0.5)
    assert error.value.code == "unsupported_parent_combination"


@pytest.mark.parametrize("method", ["render", "to_gif", "to_animated_mp4", "to_webm"])
def test_parent_morph_strict_policy_precedes_convenience_encoding(tmp_path, method):
    from quickthumb import Deck, ExportPolicy, Morph
    from quickthumb.errors import RenderingError

    first = Canvas(100, 80, layers=[NullLayer(type="null", id="root"), shape()])
    deck = Deck(100, 80).slide(first).slide(Canvas(100, 80), transition=Morph(duration=1))
    destination = tmp_path / "existing.gif"
    destination.write_bytes(b"EXISTING")
    args = (str(destination),) if method == "render" else ()
    with pytest.raises(RenderingError, match="fade fallback"):
        getattr(deck, method)(*args, policy=ExportPolicy(unsupported_motion="error"))
    assert destination.read_bytes() == b"EXISTING"


@pytest.mark.parametrize(
    "case",
    ["shape_shadow", "shape_glow", "shape_stroke", "text_shadow", "text_glow", "text_background"],
)
def test_local_source_includes_exterior_effects(case):
    from quickthumb import Background, Glow, Shadow, Stroke

    effect = {
        "shadow": Shadow(offset_x=-25, offset_y=18, color="#A050E080", blur_radius=7),
        "glow": Glow(radius=9, color="#00AAFF"),
        "stroke": Stroke(width=7, color="#FFFF00"),
        "background": Background(color="#123456", padding=(18, 25)),
    }[case.split("_")[1]]
    canvas = Canvas(240, 180)
    if case.startswith("text"):
        canvas.text(
            "jfQgy",
            position=(80, 65),
            font="assets/fonts/NotoSerif-Italic.ttf",
            size=36,
            color="#FFFFFF",
            effects=[cast(Any, effect)],
        )
    else:
        canvas.shape("ellipse", (80, 65), 40, 30, "#F0309080", effects=[cast(Any, effect)])
    linked = Canvas(
        240,
        180,
        layers=[
            NullLayer(type="null", id="root"),
            cast(Any, canvas.layers[0]).model_copy(update={"parent": "root"}),
        ],
    )
    assert (
        linked.render_frame(0).convert("RGBa").tobytes()
        == canvas.render_frame(0).convert("RGBa").tobytes()
    )


def test_affine_error_and_empty_bounds_are_explicit():
    from quickthumb.errors import RenderingError

    source = Image.new("RGBA", (8, 6), "red")
    assert affine_fragment(source, (0, 0, 0, 0, 1, 0), (100, 80)) is None
    assert affine_fragment(source, (1, 0, 1000, 0, 1, 0), (100, 80)) is None
    with pytest.raises(RenderingError, match="determinant"):
        affine_fragment(source, (1e200, 0, 0, 0, 1e200, 0), (100, 80))
    with pytest.raises(RenderingError, match="bounds"):
        affine_fragment(source, (1e308, 0, 0, 0, 1, 0), (100, 80))
    with pytest.raises(RenderingError, match="matrix"):
        multiply((1e308, 0, 0, 0, 1, 0), (1e308, 0, 0, 0, 1, 0))
