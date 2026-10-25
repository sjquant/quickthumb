"""Color-track source rendering and public export contracts."""

import json
from pathlib import Path

import jsonschema
import pytest
from PIL import Image, ImageChops, ImageSequence
from quickthumb import (
    AnimationSpec,
    BackdropBlur,
    Canvas,
    ColorTrack,
    ExportPolicy,
    GifOptions,
    KeyframeSpec,
    LinearGradient,
    OpacityTrack,
    PositionTrack,
    RotationTrack,
    ScaleXTrack,
    Shadow,
    StaggerSpec,
    Stroke,
    TextPart,
    TimingSpec,
    canvas_json_schema,
)
from quickthumb import _export_video as video
from quickthumb._color_motion import _oklab, interpolate_color
from quickthumb._export_base import _with_motion_color
from quickthumb.errors import RenderingError
from quickthumb.models import ShapeLayer, TextLayer
from quickthumb.motion import capabilities_for, compile_timeline

FONT = "assets/fonts/Roboto-Medium.ttf"


def track(kind, *values):
    return kind(keyframes=[KeyframeSpec(time=i, value=value) for i, value in enumerate(values)])


def animation(*tracks, start=0):
    return AnimationSpec.timeline(
        *tracks, timing=TimingSpec(start=start, duration=1), easing="linear"
    )


def scene(kind="shape", **kwargs):
    canvas = Canvas(160, 120)
    if kind == "shape":
        return canvas.shape("rectangle", (35, 30), 70, 50, "#35AA6680", **kwargs)
    return canvas.text("Color", position=(20, 25), size=30, font=FONT, color="#35AA6680", **kwargs)


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        ("#000000", "#FFFFFF", "#636363"),
        ("#FF0000", "#0000FF", "#8C53A2"),
        ("#FF000000", "#0000FFFF", "#0000FF80"),
        ("#FF0000", "#0000FF00", "#FF000080"),
        ("#FF000000", "#0000FF00", "#00000000"),
        ("#000000", "#FFFFFFFF", "#636363FF"),
    ],
)
def test_perceptual_midpoints_and_premultiplied_alpha(left, right, expected):
    assert interpolate_color(left, right, 0.5) == expected
    motion = animation(track(ColorTrack, left, right))
    assert compile_timeline(motion).sample(0.5).color == expected
    assert compile_timeline(motion).sample(0).color == left
    assert compile_timeline(motion).sample(1).color == right


def test_color_interpolation_clamps_easing_and_keeps_authored_endpoints():
    assert interpolate_color("#ab01EF80", "#FFFFFF", 0) == "#ab01EF80"
    assert interpolate_color("#ab01EF80", "#FFFFFF", 1) == "#FFFFFF"
    for easing in ("ease_in_back", "ease_out_back", "ease_in_out_back"):
        motion = animation(track(ColorTrack, "#FF000001", "#00FF00FE"))
        motion.easing = easing
        for time in (0.1, 0.4, 0.7, 0.95):
            result = compile_timeline(motion).sample(time).color
            assert result is not None and len(result) == 9
            assert len(bytes.fromhex(result[1:])) == 4
    for value in range(300):
        _oklab(f"#{value:06X}")
    assert _oklab.cache_info().currsize <= 256


@pytest.mark.parametrize("kind", ["shape", "text"])
@pytest.mark.parametrize("start", [0, 0.5])
def test_sampled_source_matches_equivalent_static_fill_and_does_not_mutate(kind, start):
    motion = animation(track(ColorTrack, "#FF0000", "#0000FF80"), start=start)
    canvas = scene(kind, animation=motion)
    original = canvas.to_json()
    animator = video._SlideAnimator(canvas, {})
    for time in (0, start, start + 0.25, start + 0.5, start + 1, start + 2, start + 0.25):
        state = compile_timeline(motion).sample(time)
        reference = Canvas.from_json(original)
        layer = reference.layers[0]
        assert isinstance(layer, (ShapeLayer, TextLayer))
        reference._layers[0] = _with_motion_color(layer, state.color).model_copy(
            update={"animation": None}
        )
        expected = reference._render_to_image()
        assert canvas.render_frame(time).tobytes() == expected.tobytes()
        assert animator.frame_at(time).tobytes() == expected.tobytes()
    assert canvas.to_json() == original


@pytest.mark.parametrize("kind", ["shape", "text"])
def test_transparent_authored_fill_can_appear_and_disappear(kind):
    motion = animation(track(ColorTrack, "#FF000000", "#0000FFFF"))
    canvas = scene(kind, animation=motion)
    canvas._layers[0] = canvas.layers[0].model_copy(update={"color": "#00000000"})
    animator = video._SlideAnimator(canvas, {})
    assert animator._units[0].image is None
    assert animator.frame_at(0).getbbox() is None
    for time in (1, 0.5, 0, 1):
        assert animator.frame_at(time).tobytes() == canvas.render_frame(time).tobytes()
    assert animator.frame_at(1).getbbox()


@pytest.mark.parametrize("kind", ["shape", "text"])
@pytest.mark.parametrize("quality", ["standard", "high"])
def test_color_composes_with_geometry_alpha_effects_and_clip(kind, quality):
    motion = animation(
        track(ColorTrack, "#FF000080", "#0080FFFF"),
        track(PositionTrack, (0, 0), (4.3, 2.5)),
        track(RotationTrack, 0, 25),
        track(ScaleXTrack, 1, 0.8),
        track(OpacityTrack, 1, 0.5),
    )
    canvas = scene(
        kind,
        animation=motion,
        anchor=(0, 1),
        effects=[
            Stroke(width=2, color="#FFFFFF"),
            Shadow(color="#102030", offset_x=3, offset_y=2, blur_radius=1),
        ],
        clip={"position": (0, 0), "width": 130, "height": 110},
        opacity=0.75,
    )
    animator = video._SlideAnimator(canvas, {}, quality=quality)
    for time in (0, 0.25, 0.5, 1):
        actual = animator.frame_at(time)
        assert actual.getbbox()
        if quality == "standard":
            assert actual.tobytes() == canvas.render_frame(time).tobytes()
        else:
            assert (
                actual.tobytes()
                == animator._composite_frame(animator._units, time, render_scale=2).tobytes()
            )


def test_rich_text_color_replaces_each_part_and_gradient_but_preserves_effects():
    gradient = LinearGradient(angle=0, stops=[("#00FF00", 0), ("#FFFFFF", 1)])
    canvas = Canvas(240, 90).text(
        [TextPart(text="RED", color="#FF0000"), TextPart(text="BLUE", fill=gradient)],
        position=(10, 20),
        font=FONT,
        size=30,
        fill=gradient,
        effects=[Stroke(width=1, color="#FFFFFF")],
        animation=animation(track(ColorTrack, "#A04020", "#2040A0")),
    )
    original = canvas.to_json()
    reference = Canvas(240, 90).text(
        [TextPart(text="RED", color="#2040A0"), TextPart(text="BLUE", color="#2040A0")],
        position=(10, 20),
        font=FONT,
        size=30,
        color="#2040A0",
        effects=[Stroke(width=1, color="#FFFFFF")],
    )
    assert canvas.render_frame(1).tobytes() == reference._render_to_image().tobytes()
    assert (
        video._SlideAnimator(canvas, {}).frame_at(1).tobytes() == canvas.render_frame(1).tobytes()
    )
    assert canvas.to_json() == original


@pytest.mark.parametrize("anchor", [(0.5, 0.5), (0, 0)])
@pytest.mark.parametrize("nested", [False, True])
def test_parent_color_overrides_descendants_and_keeps_intrinsic_counter(anchor, nested):
    child = (
        Canvas(160, 120)
        .counter(
            0,
            100,
            1,
            position=(0, 0),
            font=FONT,
            size=30,
            animation=animation(
                track(ColorTrack, "#00FF00", "#FFFF00"), track(PositionTrack, (0, 0), (100, 0))
            ),
        )
        .layers[0]
    )
    if nested:
        child = Canvas(160, 120).group([child]).layers[0]
    parent = animation(track(ColorTrack, "#FF0000", "#0000FF"))
    canvas = Canvas(160, 120).group([child], position=(20, 20), anchor=anchor, animation=parent)
    animator = video._SlideAnimator(canvas, {})
    frames = [animator.frame_at(time) for time in (0, 0.5, 1)]
    assert len({frame.tobytes() for frame in frames}) == 3
    for time, frame in zip((0, 0.5, 1), frames, strict=True):
        assert frame.tobytes() == canvas.render_frame(time).tobytes()
    bounds = frames[-1].getbbox()
    assert bounds is not None and bounds[2] < 100
    assert any(
        isinstance(pixel, tuple) and pixel[:3] == (0, 0, 255) and pixel[3]
        for pixel in frames[-1].get_flattened_data()
    )


def test_unanimated_group_keeps_child_color_motion():
    child = (
        scene(animation=animation(track(ColorTrack, "#FF0000", "#0000FF")))
        .layers[0]
        .model_copy(update={"position": (0, 0)})
    )
    canvas = Canvas(160, 120).group([child], position=(20, 20))
    animator = video._SlideAnimator(canvas, {})
    for time in (0, 0.5, 1):
        assert animator.frame_at(time).tobytes() == canvas.render_frame(time).tobytes()


def test_color_backdrop_prefix_and_static_plate_order():
    canvas = scene(animation=animation(track(ColorTrack, "#FF0000", "#0000FF")))
    canvas.shape("rectangle", (50, 40), 40, 30, "#FFFFFF80", effects=[BackdropBlur(radius=2)])
    animator = video._SlideAnimator(canvas, {})
    for time in (0, 0.5, 1):
        assert animator.frame_at(time).tobytes() == canvas.render_frame(time).tobytes()


@pytest.mark.parametrize("transparent", [False, True])
def test_staggered_lines_use_independent_colors_and_stable_bounds(transparent):
    motion = animation(track(ColorTrack, "#FF000000" if transparent else "#FF0000", "#0000FF"))
    motion.stagger = StaggerSpec(delay=0.5, target="lines")
    canvas = Canvas(180, 180).text(
        "ONE\nTWO\nTHREE",
        position=(30, 20),
        font=FONT,
        size=25,
        color="#00000000" if transparent else "#FFFFFF",
        animation=motion,
    )
    animator = video._SlideAnimator(canvas, {})
    assert len(animator._units[0].target_images) == 3
    for time in (0, 0.25, 0.75, 1.25, 2):
        assert canvas.render_frame(time).tobytes() == animator.frame_at(time).tobytes()
    if not transparent:
        image = canvas.render_frame(0.75)
        colors = {
            pixel[:3]
            for pixel in image.get_flattened_data()
            if isinstance(pixel, tuple) and pixel[3] == 255
        }
        assert tuple(bytes.fromhex(interpolate_color("#FF0000", "#0000FF", 0.75)[1:])) in colors
        assert tuple(bytes.fromhex(interpolate_color("#FF0000", "#0000FF", 0.25)[1:])) in colors


def test_no_color_tracks_keep_prepared_images_and_source_identity(monkeypatch):
    canvas = scene(animation=animation(track(PositionTrack, (0, 0), (10, 0))))
    animator = video._SlideAnimator(canvas, {})
    source = animator._units[0].image
    assert source is not None
    original = source.tobytes()
    monkeypatch.setattr(canvas, "_render_layer", lambda *a, **kw: pytest.fail("source rerendered"))
    for time in (0, 0.5, 1, 0.5):
        assert animator.frame_at(time).getbbox()
    assert animator._units[0].image is source
    assert source.tobytes() == original
    assert _with_motion_color(canvas.layers[0], None) is canvas.layers[0]


def test_color_public_schema_roundtrip_inspection_and_format_fallbacks():
    canvas = scene(animation=animation(track(ColorTrack, "#FF0000", "#0000FF")))
    jsonschema.validate(json.loads(canvas.to_json()), canvas_json_schema())
    assert Canvas.from_json(canvas.to_json()).to_json() == canvas.to_json()
    inspected = canvas.inspect_motion().slides[0].layers[0]
    assert inspected.final_state["color"] == "#0000FF"
    assert inspected.events[0].tracks[0].type == "color"
    for target in ("raster", "video"):
        assert capabilities_for(target)["color"].support == "full"
        assert [(item.support, item.fallback) for item in canvas.validate_export(target)] == [
            ("full", None)
        ]
    for target in ("html", "pptx"):
        report = canvas.validate_export(target)
        assert [(item.support, item.fallback) for item in report] == [("fallback", "static")]
        with pytest.raises(RenderingError, match="unsupported"):
            canvas.validate_export(target, ExportPolicy(unsupported_motion="error"))
    html = canvas.to_html()
    assert "@keyframes" not in html
    assert "visibility:hidden" not in html


def test_unsupported_color_layer_declares_fallback():
    canvas = Canvas(100, 100).image(
        "tests/fixtures/sample_image.jpg",
        (0, 0),
        50,
        50,
        animation=animation(track(ColorTrack, "#FF0000", "#0000FF")),
    )
    for target in ("video", "raster"):
        assert canvas.validate_export(target)[0].fallback == "static"
        with pytest.raises(RenderingError, match="unsupported"):
            canvas.validate_export(target, ExportPolicy(unsupported_motion="error"))


@pytest.mark.parametrize("quality", ["standard", "high"])
def test_color_gif_worker_bytes_and_timing(quality, tmp_path):
    canvas = scene(animation=animation(track(ColorTrack, "#FF000000", "#0000FFFF")))
    outputs = [tmp_path / f"{workers}.gif" for workers in (1, 2)]
    for workers, output in zip((1, 2), outputs, strict=True):
        canvas.render(str(output), animation=GifOptions(fps=4, quality=quality, workers=workers))
    assert outputs[0].read_bytes() == outputs[1].read_bytes()


def test_color_motion_visual_snapshot():
    strip = Image.new("RGBA", (160 * 3, 120 * 2))
    for row, kind in enumerate(("shape", "text")):
        canvas = scene(kind, animation=animation(track(ColorTrack, "#FF0000", "#0000FF")))
        for column, time in enumerate((0, 0.5, 1)):
            strip.paste(canvas.render_frame(time), (160 * column, 120 * row))
    expected = Image.open(Path(__file__).parent / "snapshots" / "color_motion.png").convert("RGBA")
    assert (strip.size, strip.tobytes()) == (expected.size, expected.tobytes())


def test_color_prefix_encodes_intermediate_frames(tmp_path):
    canvas = scene(animation=animation(track(ColorTrack, "#FF0000", "#0000FF")))
    canvas.shape("rectangle", (70, 40), 40, 30, "#FFFFFF80", effects=[BackdropBlur(radius=2)])
    animator = video._SlideAnimator(canvas, {})
    assert animator.segments(0, 1) == [(0, 1, True)]
    output = tmp_path / "prefix.gif"
    canvas.render(str(output), animation=GifOptions(fps=4))
    with Image.open(output) as image:
        colors = []
        durations = []
        for frame in ImageSequence.Iterator(image):
            colors.append(frame.convert("RGB").getpixel((45, 45)))
            durations.append(frame.info["duration"])
    assert len(set(colors)) >= 5
    assert durations[:4] == [250] * 4


def test_retained_color_counter_keeps_its_longer_source_timing():
    child = Canvas(160, 120).counter(0, 100, 2, position=(0, 0), font=FONT, size=30).layers[0]
    canvas = Canvas(160, 120).group(
        [child],
        position=(20, 20),
        clip={"position": (0, 0), "width": 150, "height": 110},
        animation=animation(track(ColorTrack, "#FF0000", "#0000FF")),
    )
    animator = video._SlideAnimator(canvas, {})
    assert animator.duration == 2
    assert all(active for _, _, active in animator.segments(0, 2))
    assert animator.frame_at(1).tobytes() != animator.frame_at(2).tobytes()


def test_retained_group_color_measurements_are_bounded_even_on_error(monkeypatch):
    child = scene().layers[0].model_copy(update={"position": (0, 0)})
    canvas = Canvas(160, 120).group(
        [child],
        position=(20, 20),
        anchor=(0, 0),
        animation=animation(track(ColorTrack, "#FF0000", "#0000FF")),
    )
    animator = video._SlideAnimator(canvas, {})
    measurements = canvas._ctx.measure_cache
    original = dict(measurements)
    for index in range(101):
        animator.frame_at(index / 100)
        assert canvas._ctx.measure_cache is measurements
        assert measurements == original

    def fail(*args, **kwargs):
        raise RuntimeError("paint failed")

    monkeypatch.setattr(canvas, "_render_layer", fail)
    with pytest.raises(RuntimeError, match="paint failed"):
        animator.frame_at(0.5)
    assert canvas._ctx.measure_cache is measurements
    assert measurements == original


def test_unanimated_group_keeps_separable_child_line_color_stagger():
    motion = animation(track(ColorTrack, "#FF0000", "#0000FF"))
    motion.stagger = StaggerSpec(delay=0.5, target="lines")
    child = (
        Canvas(180, 180)
        .text(
            "ONE\nTWO\nTHREE",
            position=(0, 0),
            font=FONT,
            size=25,
            animation=motion,
        )
        .layers[0]
    )
    canvas = Canvas(180, 180).group([child], position=(30, 20))
    animator = video._SlideAnimator(canvas, {})
    assert len(animator._units[0].target_images) == 3
    for time in (0, 0.25, 0.75, 1.25, 2):
        assert canvas.render_frame(time).tobytes() == animator.frame_at(time).tobytes()


@pytest.mark.parametrize("clip", [None, {"position": (25, 15), "width": 55, "height": 45}])
@pytest.mark.parametrize("moving", [False, True])
def test_colored_backdrop_shape_matches_static_sample_with_effects(clip, moving):
    def background():
        return (
            Canvas(100, 80)
            .background(color="#FF0000")
            .shape("rectangle", (50, 0), 50, 80, "#00FF00")
        )

    effects = [
        BackdropBlur(radius=5),
        Stroke(width=2, color="#FFFFFF"),
        Shadow(offset_x=3, offset_y=3, color="#606060", blur_radius=2),
    ]
    tracks = [track(ColorTrack, "#FFFFFF80", "#0000FF80")]
    if moving:
        tracks.append(track(PositionTrack, (0, 0), (5, 3)))
    canvas = background().shape(
        "rectangle",
        (20, 20),
        60,
        40,
        "#FFFFFF80",
        effects=effects,
        clip=clip,
        animation=animation(*tracks),
    )
    reference = background().shape(
        "rectangle",
        (25, 23) if moving else (20, 20),
        60,
        40,
        "#0000FF80",
        effects=effects,
        clip=clip,
    )
    if not moving:
        assert canvas.render_frame(1).tobytes() == reference._render_to_image().tobytes()
    elif clip is None:
        # Motion flattens exterior effects into one source; compositing order
        # can round a channel by one, but must not lose or widen the body blur.
        difference = ImageChops.difference(canvas.render_frame(1), reference._render_to_image())
        assert max(difference.tobytes()) <= 1
    animator = video._SlideAnimator(canvas, {})
    for time in (0, 0.5, 1):
        assert canvas.render_frame(time).tobytes() == animator.frame_at(time).tobytes()


def test_stagger_reuses_settled_color_without_discarded_source_renders(monkeypatch):
    motion = animation(track(ColorTrack, "#FF0000", "#0000FF"))
    motion.stagger = StaggerSpec(delay=0.5, target="lines")
    canvas = Canvas(180, 180).text(
        "ONE\nTWO\nTHREE", position=(30, 20), font=FONT, size=25, animation=motion
    )
    animator = video._SlideAnimator(canvas, {})
    draw = canvas._render_layer
    calls = []

    def count(image, layer, time=None):
        calls.append(layer.color)
        return draw(image, layer, time)

    monkeypatch.setattr(canvas, "_render_layer", count)
    animator.frame_at(2)
    assert calls == ["#0000FF"]
    calls.clear()
    canvas.render_frame(2)
    assert calls == ["#FFFFFF", "#0000FF"]
    motion.timing = TimingSpec(start=1, duration=1)
    calls.clear()
    canvas.render_frame(0)
    assert calls == ["#FFFFFF"]


def test_color_reduced_motion_and_pptx_keep_authored_fill():
    from io import BytesIO
    from zipfile import ZipFile

    canvas = scene(animation=animation(track(ColorTrack, "#FF0000", "#0000FF")))
    expected = scene()._render_to_image().tobytes()
    animator = video._SlideAnimator(canvas, {}, reduced_motion=True)
    assert animator.frame_at(1).tobytes() == expected
    assert canvas._render_to_image().tobytes() == expected
    with ZipFile(BytesIO(canvas.to_pptx())) as archive:
        slide = archive.read("ppt/slides/slide1.xml").decode()
    assert "35AA66" in slide and "animClr" not in slide


def test_shape_color_overrides_gradient_and_example_runs():
    from examples.color_tracks import build_scene

    gradient = LinearGradient(angle=0, stops=[("#00FF00", 0), ("#FFFFFF", 1)])
    canvas = scene(fill=gradient, animation=animation(track(ColorTrack, "#FF0000", "#0000FF")))
    reference = scene()
    reference._layers[0] = reference.layers[0].model_copy(update={"color": "#0000FF"})
    assert canvas.render_frame(1).tobytes() == reference._render_to_image().tobytes()
    example = build_scene()
    restored = Canvas.from_json(example.to_json())
    assert restored.to_json() == example.to_json()
    assert len({example.render_frame(time).tobytes() for time in (0, 1, 2)}) == 3


@pytest.mark.parametrize("anchor", [(0.5, 0.5), (0, 0)])
@pytest.mark.parametrize("nested", [False, True])
def test_color_group_backdrop_reads_prior_layers(anchor, nested):
    def build(motion, color):
        child = (
            Canvas(100, 80)
            .shape("rectangle", (0, 0), 60, 40, color, effects=[BackdropBlur(radius=5)])
            .layers[0]
        )
        if nested:
            child = Canvas(100, 80).group([child]).layers[0]
        return (
            Canvas(100, 80)
            .background(color="#FF0000")
            .shape("rectangle", (50, 0), 50, 80, "#00FF00")
            .group([child], position=(20, 20), anchor=anchor, animation=motion)
        )

    motion = animation(track(ColorTrack, "#FFFFFF80", "#0000FF80"))
    canvas = build(motion, "#FFFFFF80")
    animator = video._SlideAnimator(canvas, {})
    for time in (0, 0.5, 1):
        expected = build(None, compile_timeline(motion).sample(time).color)._render_to_image()
        assert canvas.render_frame(time).tobytes() == expected.tobytes()
        assert animator.frame_at(time).tobytes() == expected.tobytes()


def test_group_color_plus_motion_with_backdrop_reports_and_rejects_unsupported_boundary():
    child = (
        Canvas(100, 80)
        .shape("rectangle", (0, 0), 60, 40, "#FFFFFF80", effects=[BackdropBlur(radius=5)])
        .layers[0]
    )
    canvas = (
        Canvas(100, 80)
        .background(color="#FF0000")
        .group(
            [child],
            position=(20, 20),
            animation=animation(
                track(ColorTrack, "#FFFFFF80", "#0000FF80"), track(PositionTrack, (0, 0), (5, 0))
            ),
        )
    )
    diagnostic = next(item for item in canvas.validate_export("video") if item.feature == "color")
    assert diagnostic.support == "unsupported" and diagnostic.fallback is None
    with pytest.raises(RenderingError, match="backdrop-dependent descendants"):
        canvas.render_frame(0.5)
    with pytest.raises(RenderingError, match="backdrop-dependent descendants"):
        video._SlideAnimator(canvas, {}).frame_at(0.5)


def test_parent_color_validation_ignores_overridden_child_backdrop_motion():
    child = (
        Canvas(100, 80)
        .shape("rectangle", (0, 0), 60, 40, "#FFFFFF80", effects=[BackdropBlur(radius=5)])
        .layers[0]
    )
    inner = (
        Canvas(100, 80)
        .group(
            [child],
            animation=animation(
                track(ColorTrack, "#FF000080", "#00FF0080"), track(PositionTrack, (0, 0), (5, 0))
            ),
        )
        .layers[0]
    )
    canvas = (
        Canvas(100, 80)
        .background(color="#FF0000")
        .group(
            [inner],
            position=(20, 20),
            anchor=(0, 0),
            animation=animation(track(ColorTrack, "#FFFFFF80", "#0000FF80")),
        )
    )
    diagnostics = canvas.validate_export("video", ExportPolicy(unsupported_motion="error"))
    colors = [item for item in diagnostics if item.feature == "color"]
    assert len(colors) == 1 and colors[0].support == "full"
    animator = video._SlideAnimator(canvas, {})
    assert canvas.render_frame(1).tobytes() == animator.frame_at(1).tobytes()
