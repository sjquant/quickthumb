"""Parent diagnostics consume static world pixels, not local-coordinate masks."""

import pytest
from PIL import Image, ImageChops
from quickthumb import (
    AnimationSpec,
    Background,
    BarChartSpec,
    Canvas,
    GroupLayer,
    KeyframeSpec,
    LayerClip,
    LinearGradient,
    OpacityTrack,
    PositionKeyframeSpec,
    PositionTrack,
    Shadow,
    ShapeLayer,
    TextLayer,
    TextPart,
    TimingSpec,
)
from quickthumb._measurements import BBox, measure_layers
from quickthumb._parent_diagnostics import ParentDiagnosticSources
from quickthumb._parent_render import affine_fragment
from quickthumb.errors import RenderingError

FONT = "assets/fonts/Roboto-Medium.ttf"
ITALIC = "assets/fonts/NotoSerif-Italic.ttf"


def motion(kind, first, last):
    return AnimationSpec.timeline(
        kind(keyframes=[KeyframeSpec(time=0, value=first), KeyframeSpec(time=1, value=last)]),
        timing=TimingSpec(duration=1),
        easing="linear",
    )


def setup(canvas):
    canvas._ctx.begin_render_pass()
    measured = measure_layers(canvas)
    source = ParentDiagnosticSources(canvas, measured)
    return source, source.decorate(measured)


def composite(canvas, sources, measured):
    image = canvas._create_canvas()
    for item in measured:
        if sources.handles(item):
            sources.composite(image, item)
        else:
            canvas._render_layer(image, item.raw_layer)
    return image


def rectangle_scene(rotation=0):
    return (
        Canvas(200, 140)
        .background(color="#FFFFFF")
        .null((80, 60), id="root", rotation=rotation)
        .shape("rectangle", (-70, -20), 30, 20, "#FF0000", parent="root", id="child")
    )


@pytest.mark.parametrize("rotation", [0, 33, 90, 180])
def test_world_composite_matches_authored_static_raster_without_sampling(rotation):
    canvas = rectangle_scene(rotation)
    canvas.layers[1].animation = motion(PositionTrack, (50, 0), (100, 0))
    sources, measured = setup(canvas)
    assert composite(canvas, sources, measured).tobytes() == canvas._render_to_image().tobytes()
    assert composite(canvas, sources, measured).tobytes() != canvas.render_frame(0).tobytes()


def test_local_offcanvas_content_is_kept_until_parenting_moves_it_onscreen():
    canvas = rectangle_scene()
    sources, measured = setup(canvas)
    child = measured[-1]
    assert child.bbox == BBox(10, 40, 30, 20)
    assert sources.alpha(child).getbbox() == (0, 0, 30, 20)
    assert not any(item.code == "off-canvas" for item in canvas.diagnose().findings)


def test_rotated_parent_rectangle_aabb_corners_are_not_opaque():
    canvas = (
        Canvas(160, 120)
        .shape("rectangle", (65, 80), 3, 3, "#00FF00", id="lower")
        .null((70, 50), rotation=45, id="root")
        .shape("rectangle", (0, 0), 40, 10, "#FF0000", parent="root", id="upper")
    )
    sources, measured = setup(canvas)
    alpha = sources.alpha(measured[-1])
    box = measured[-1].bbox
    assert box is not None
    assert alpha.crop((65 - box.x, 80 - box.y, 68 - box.x, 83 - box.y)).getbbox() is None
    assert not any(
        item.code in {"layer-hidden", "layer-overlap"} for item in canvas.diagnose().findings
    )


def test_resampled_almost_opaque_edge_does_not_hide_lower_layer():
    canvas = (
        Canvas(200, 140)
        .shape("rectangle", (78, 50), 1, 1, "#00FF00", id="lower")
        .null((80, 60), id="root", rotation=180)
        .shape("rectangle", (-20, -10), 40, 20, "#FF0000", parent="root", id="upper")
    )
    sources, measured = setup(canvas)
    upper = measured[-1]
    box = upper.bbox
    assert box is not None
    assert sources.alpha(upper).getpixel((78 - box.x, 50 - box.y)) == 254
    assert not any(
        item.code == "layer-hidden" and item.layer_id == "lower"
        for item in canvas.diagnose().findings
    )


@pytest.mark.parametrize("kind", [OpacityTrack, PositionTrack])
def test_ancestor_geometry_motion_but_not_opacity_affects_hidden_rule(kind):
    first, last = ((0, 0), (10, 0)) if kind is PositionTrack else (0, 1)
    canvas = (
        Canvas(160, 120)
        .shape("rectangle", (55, 45), 5, 5, "#00FF00", id="lower")
        .shape(
            "rectangle",
            (40, 30),
            10,
            10,
            "#FFFFFF",
            opacity=0,
            id="root",
            animation=motion(kind, first, last),
        )
        .shape("rectangle", (0, 0), 40, 40, "#FF0000", parent="root", id="upper")
    )
    sources, measured = setup(canvas)
    assert sources.alpha(measured[-1]).getextrema()[1] == 255
    hidden = [item for item in canvas.diagnose().findings if item.code == "layer-hidden"]
    assert bool(hidden) is (kind is OpacityTrack)


def test_text_contrast_uses_world_backdrop_and_own_background():
    canvas = (
        Canvas(300, 180)
        .background(color="#000000")
        .shape("rectangle", (170, 40), 120, 80, "#FFFFFF")
        .null((180, 50), id="root")
        .text(
            "WORLD", position=(0, 0), size=22, font=FONT, color="#000000", parent="root", id="text"
        )
    )
    assert not any(item.code == "low-contrast" for item in canvas.diagnose().findings)
    layer = canvas.layers[1]
    assert isinstance(layer, ShapeLayer)
    layer.color = "#000000"
    assert any(item.code == "low-contrast" for item in canvas.diagnose().findings)
    text = canvas.layers[-1]
    assert isinstance(text, TextLayer)
    text.effects = [Background(color="#FFFFFF", padding=5)]
    assert not any(item.code == "low-contrast" for item in canvas.diagnose().findings)


def test_nested_group_prefix_uses_original_slots_and_atomic_warp():
    canvas = (
        Canvas(400, 240)
        .background(color="#000000")
        .null((150, 80), id="root", rotation=19)
        .group(
            [
                {
                    "type": "shape",
                    "shape": "rectangle",
                    "width": 140,
                    "height": 60,
                    "color": "#FFFFFF",
                },
                {
                    "type": "group",
                    "children": [
                        {
                            "type": "text",
                            "content": "BLACK",
                            "size": 28,
                            "font": FONT,
                            "color": "#000000",
                        }
                    ],
                },
            ],
            position=(-30, -20),
            direction="row",
            gap=10,
            parent="root",
            id="group",
        )
    )
    # The prefix must keep the original nested group slots.
    sources, measured = setup(canvas)
    root = sources.occurrences["group"].root
    replay = Image.new("RGBA", root.node.source_size)
    for operation in root.operations:
        sources._paint_operation(replay, operation)
    assert root.node.image is not None
    assert replay.tobytes() == root.node.image.tobytes()
    assert composite(canvas, sources, measured).tobytes() == canvas._render_to_image().tobytes()
    text = measured[-1].children[1].children[0]
    base = canvas._create_canvas()
    canvas._render_layer(base, canvas.layers[0])
    backdrop, _ = sources.text_images(base, text)
    expected = base.copy()
    prefix = Image.new("RGBA", root.node.source_size)
    sources._paint_operation(prefix, root.operations[0])
    fragment = affine_fragment(prefix, root.matrix, base.size)
    assert fragment is not None
    expected.alpha_composite(*fragment)
    assert backdrop.tobytes() == expected.tobytes()


@pytest.mark.parametrize("rich", [False, True])
@pytest.mark.parametrize("angle", [30, 90, 180])
@pytest.mark.parametrize("opacity", [1, 0.6])
def test_rotated_text_probe_uses_original_effect_stage_without_italic_clipping(
    rich, angle, opacity
):
    content = (
        [
            TextPart(
                text="jfQgy\njQ",
                font=ITALIC,
                size=170,
                effects=[Shadow(color="#000000", offset_x=50, offset_y=20, blur_radius=4)],
            )
        ]
        if rich
        else "jfQgy\njQ"
    )
    layer = TextLayer(
        type="text",
        content=content,
        font=ITALIC,
        size=170,
        position=(0, 0),
        rotation=angle,
        opacity=opacity,
        color="#000000",
        effects=[Shadow(color="#000000", offset_x=50, offset_y=20, blur_radius=4)],
    )
    canvas = Canvas(1000, 800).null((100, 100), rotation=17, id="root")
    canvas.layers = [*canvas.layers, layer.model_copy(update={"parent": "root"})]
    sources, measured = setup(canvas)
    occurrence = sources.occurrences[measured[-1].layer_id]
    source = occurrence.text
    assert source is not None
    parts = source.content
    if isinstance(parts, list):
        parts = [part.model_copy(update={"effects": []}) for part in parts]
    variant = source.model_copy(update={"content": parts, "effects": [], "auto_scale": False})
    actual = Image.new("RGBA", occurrence.root.node.source_size)
    canvas._text.render_text_layer(actual, variant, staging_reference=source)
    # Independent fixed-stage construction, retaining the original effect padding.
    w, h = canvas._text.measure_text_size(source)
    padding = (
        canvas._text._calculate_rich_text_effects_padding(source)
        if rich
        else canvas._text._calculate_text_effects_padding(
            canvas._text._get_stroke_effects(source.effects),
            canvas._text._get_shadow_effects(source.effects),
            canvas._text._get_glow_effects(source.effects),
        )
    )
    stage = Image.new("RGBA", (w + 2 * padding, h + 2 * padding))
    paint = variant.model_copy(
        update={
            "position": (padding, padding),
            "align": None,
            "rotation": 0,
            "opacity": 1,
            "auto_scale": False,
        }
    )
    canvas._text.render_text_layer(stage, paint)
    expected = Image.new("RGBA", actual.size)
    canvas._text._rotate_and_composite_text(expected, stage, source)
    canvas._effects.apply_opacity(expected, opacity)
    assert actual.tobytes() == expected.tobytes()
    old = Image.new("RGBA", actual.size)
    canvas._text.render_text_layer(old, variant)
    assert ImageChops.difference(old.getchannel("A"), actual.getchannel("A")).getbbox() is not None


def test_parent_repairs_do_not_assign_world_coordinates_to_local_fields():
    canvas = (
        Canvas(120, 80)
        .null((-80, 10), id="root", rotation=30)
        .shape("rectangle", (0, 0), 30, 20, "#FF0000", parent="root", id="child")
    )
    finding = next(item for item in canvas.diagnose().findings if item.code == "off-canvas")
    assert "parent-local" in finding.suggestion
    assert "x=" not in finding.suggestion and "y=" not in finding.suggestion
    assert finding.measured["coordinate_space"] == "world"
    assert finding.measured["position_space"] == "parent_local"


def test_oversized_parent_child_repair_preserves_resize_first_guidance():
    canvas = (
        Canvas(100, 80)
        .null((0, 0), id="root")
        .shape("rectangle", (0, 0), 200, 30, "#FF0000", parent="root")
    )
    finding = next(item for item in canvas.diagnose().findings if item.code == "off-canvas")
    assert finding.suggestion.startswith("resize")
    assert "parent-local" in finding.suggestion


def test_inherited_rotation_disables_near_alignment():
    canvas = (
        Canvas(200, 130)
        .null((50, 50), id="root", rotation=30)
        .shape("rectangle", (0, 0), 20, 20, "#FF0000", parent="root")
        .shape("rectangle", (2, 0), 20, 20, "#0000FF", parent="root")
    )
    assert not any(item.code == "near-alignment" for item in canvas.diagnose().findings)


def test_unsupported_combination_stays_guarded_and_failure_cleans_context(monkeypatch):
    canvas = rectangle_scene()
    layers = canvas.layers
    layers[-1] = GroupLayer(
        type="group",
        parent="root",
        children=[canvas.layers[-1].model_copy(update={"parent": None, "position": (0, 0)})],
        clip=LayerClip(position=(0, 0), width=4, height=4),
    )
    canvas.layers = layers
    closed = []
    monkeypatch.setattr(canvas._ctx, "close_video_decoders", lambda: closed.append(True))
    with pytest.raises(RenderingError) as error:
        canvas.diagnose()
    assert error.value.code == "unsupported_parent_rendering"
    assert canvas._diagnostics._parent_sources is None and closed


def test_repeated_diagnosis_after_mutation_keeps_source_spec_and_updates_bounds():
    canvas = rectangle_scene()
    original = canvas.to_json()
    first = canvas.diagnose().model_dump_json()
    assert canvas.to_json() == original
    assert canvas.diagnose().model_dump_json() == first
    canvas.layers[1].position = (-100, 60)
    assert any(item.code == "off-canvas" for item in canvas.diagnose().findings)
    assert canvas._diagnostics._parent_sources is None


@pytest.mark.parametrize("rich", [False, True])
@pytest.mark.parametrize("rotation", [0, 31])
@pytest.mark.parametrize("spacing", [0, 3])
def test_wrapped_text_background_probe_preserves_ink_backing(rich, rotation, spacing):
    background = Background(color="#FFFFFF", padding=40)
    gradient = LinearGradient(angle=0, stops=[("#000000", 0), ("#101010", 1)])
    content = (
        [{"text": "READ THIS\nLINE TWO", "fill": gradient, "effects": [background]}]
        if rich
        else "READ THIS\nLINE TWO"
    )
    canvas = (
        Canvas(400, 300)
        .background(color="#000000")
        .null((130, 100), id="root", rotation=13)
        .text(
            content,
            position=(0, 0),
            font=FONT,
            size=24,
            fill=gradient,
            letter_spacing=spacing,
            max_width=170,
            rotation=rotation,
            effects=[] if rich else [background],
            parent="root",
        )
    )
    assert not any(item.code == "low-contrast" for item in canvas.diagnose().findings)


def test_three_rotated_visible_ancestors_preserve_static_composite_and_alpha():
    canvas = Canvas(300, 250).background(color="#FFFFFF")
    canvas.shape("rectangle", (170, 120), 40, 50, "#123456", rotation=180, id="root")
    canvas.shape("rectangle", (-50, 30), 20, 30, "#FF0000", rotation=33, parent="root", id="arm")
    canvas.shape("ellipse", (15, 10), 24, 18, "#00FF00", rotation=19, parent="arm", id="tip")
    canvas.text("END", position=(0, 0), font=FONT, size=15, parent="tip")
    sources, measured = setup(canvas)
    assert composite(canvas, sources, measured).tobytes() == canvas._render_to_image().tobytes()
    for item in measured[1:]:
        source = canvas._create_canvas()
        sources.composite(source, item)
        box = item.bbox
        assert box is not None
        expected = source.getchannel("A").crop((box.x, box.y, box.right, box.bottom))
        assert sources.alpha(item).tobytes() == expected.tobytes()


def test_parented_chart_uses_painted_alpha_instead_of_bbox():
    canvas = Canvas(200, 140).null((70, 30), rotation=20, id="root")
    canvas.chart(BarChartSpec(data=[1, 3, 2]), (0, 0), 80, 50, parent="root")
    sources, measured = setup(canvas)
    alpha = sources.alpha(measured[-1])
    assert alpha.getextrema() == (0, 255)
    assert len(set(alpha.tobytes())) > 2
    canvas.diagnose()


def test_group_animation_suppresses_child_motion_diagnostics():
    track = PositionTrack(
        keyframes=[
            PositionKeyframeSpec(time=0, value=(0, 0), in_tangent=(2, 2)),
            KeyframeSpec(time=1, value=(20, 0)),
        ]
    )
    canvas = Canvas(200, 140).null((60, 40), id="root")
    canvas.group(
        [
            {
                "type": "text",
                "content": "X",
                "font": FONT,
                "animation": AnimationSpec.timeline(track),
            }
        ],
        position=(0, 0),
        parent="root",
        animation=motion(OpacityTrack, 0, 1),
    )
    assert not any(item.code == "motion-path-unused-handle" for item in canvas.diagnose().findings)


def test_group_repairs_target_its_layout_and_private_metadata_stays_internal():
    canvas = Canvas(200, 140).null((20, 20), id="root")
    canvas.group(
        [{"type": "text", "content": "edge", "font": FONT, "size": 25}],
        position=(-18, 0),
        parent="root",
        id="group",
    )
    findings = canvas.diagnose().findings
    child = next(item for item in findings if item.measured.get("position_space") == "group_layout")
    assert "containing group 'group'" in child.suggestion
    assert "parent_world" not in canvas.inspect().model_dump_json()


def test_render_failure_releases_parent_sources_and_video_decoders(monkeypatch):
    canvas = rectangle_scene()
    closed = []
    monkeypatch.setattr(canvas._ctx, "close_video_decoders", lambda: closed.append(True))
    monkeypatch.setattr(
        ParentDiagnosticSources,
        "composite",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("paint")),
    )
    with pytest.raises(RuntimeError, match="paint"):
        canvas.diagnose()
    assert canvas._diagnostics._parent_sources is None and closed


def test_parented_video_diagnostics_keep_caption_coordinates_and_close_decoder(tmp_path):
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
    caption = VideoCaption(
        text="Fixed caption", position=(10, 8), font=FONT, size=12, start=0, end=0.5
    )
    plain = Canvas(180, 140).video(str(path), (50, 40), 48, 36, rotation=31, captions=[caption])
    linked = (
        Canvas(180, 140)
        .null((30, 10), id="root")
        .video(str(path), (20, 30), 48, 36, rotation=31, captions=[caption], parent="root")
    )
    report = linked.diagnose()
    baseline = plain.diagnose()
    observed = [
        (item.code, item.measured) for item in report.findings if item.code.startswith("caption-")
    ]
    assert observed == [
        (item.code, item.measured) for item in baseline.findings if item.code.startswith("caption-")
    ]
    assert observed
    assert not linked._ctx.video_decoder_cache
