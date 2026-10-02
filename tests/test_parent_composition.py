"""Own source composition travels with parent geometry without clipping children."""

from typing import Any, cast

import pytest
from PIL import Image
from quickthumb import (
    Align,
    Background,
    BarChartSpec,
    Canvas,
    ClipProgressTrack,
    ColorTrack,
    LayerClip,
    LayerMask,
    NullLayer,
    OpacityTrack,
    PositionTrack,
    RotationTrack,
    ScaleXTrack,
    ScaleYTrack,
    Shadow,
)
from quickthumb._diagnostic_rules import worst_tile_contrast
from quickthumb._export_video import _SlideAnimator
from quickthumb._measurements import BBox, measure_layers
from quickthumb._parent_render import ParentRenderPlan, parent_geometry

from tests.test_parent_counters import FONT, motion, track
from tests.test_parent_diagnostics import composite, setup
from tests.test_parent_documents import embedded_png
from tests.test_parent_stagger import motion as stagger_motion


def linked(canvas):
    return Canvas(
        canvas.width,
        canvas.height,
        layers=[
            NullLayer(type="null", id="root"),
            *[cast(Any, layer).model_copy(update={"parent": "root"}) for layer in canvas.layers],
        ],
    )


def boundaries(kind="both"):
    clip = LayerClip(
        position=("50%", "50%"), width=115, height=75, align=Align.CENTER, border_radius=13
    )
    mask = LayerMask(
        shape="polygon",
        position=("52%", "53%"),
        width=110,
        height=85,
        align=Align.CENTER,
        points=[(0, 0.1), (0.9, 0), (1, 0.7), (0.3, 1)],
        opacity=0.6,
    )
    if kind == "clip":
        return {"clip": clip}
    if kind.startswith("invert"):
        mask.invert = True
        mask.opacity = float(kind.removeprefix("invert"))
    if kind == "empty":
        clip.position = (-500, -500)
    return {"clip": clip, "mask": mask}


@pytest.mark.parametrize("kind", ["shape", "text", "image", "svg", "chart", "qr"])
@pytest.mark.parametrize("boundary", ["clip", "both", "invert0", "invert0.4", "invert1", "empty"])
def test_identity_parent_retains_composed_rgba(tmp_path, kind, boundary):
    canvas = Canvas(320, 220)
    options: dict[str, Any] = dict(
        position=("50%", "50%"), align=Align.CENTER, **boundaries(boundary)
    )
    if kind == "shape":
        canvas.shape(
            "rectangle",
            width=145,
            height=105,
            color="#FA8833",
            rotation=29,
            effects=[Shadow(offset_x=-11, offset_y=9, blur_radius=3, color="#000000")],
            **options,
        )
    elif kind == "text":
        canvas.text(
            "MASK ME",
            font=FONT,
            size=32,
            rotation=27,
            effects=[Background(color="#116699", padding=12)],
            **options,
        )
    elif kind == "image":
        path = tmp_path / "source.png"
        Image.new("RGBA", (45, 35), "#3388CCAA").save(path)
        canvas.image(str(path), width=145, height=105, rotation=-23, **options)
    elif kind == "svg":
        path = tmp_path / "source.svg"
        path.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="145" height="105">'
            '<rect width="145" height="105" fill="#3388CC"/></svg>'
        )
        canvas.svg(str(path), rotation=17, **options)
    elif kind == "chart":
        canvas.chart(BarChartSpec(data=[1, 3, 2]), width=145, height=105, **options)
    else:
        canvas.qr_code("source boundary", size=130, **options)
    parented = linked(canvas)
    before = parented.to_json()
    assert parented._render_to_image().tobytes() == canvas._render_to_image().tobytes()
    for quality in ("standard", "high"):
        assert (
            _SlideAnimator(parented, {}, quality=quality).frame_at(0.5).tobytes()
            == _SlideAnimator(canvas, {}, quality=quality).frame_at(0.5).tobytes()
        )
    assert parented.to_json() == before


@pytest.mark.parametrize("invert", [False, True])
@pytest.mark.parametrize("opacity", [0, 0.4, 1])
def test_opacity_weighted_mask_inverts_once(invert, opacity):
    canvas = Canvas(100, 80).shape(
        "rectangle",
        (10, 10),
        70,
        50,
        "#FF0000",
        mask=LayerMask(position=(30, 20), width=30, height=20, invert=invert, opacity=opacity),
    )
    image = linked(canvas)._render_to_image()
    assert image.getpixel((40, 30))[3] == (
        255 - round(255 * opacity) if invert else round(255 * opacity)
    )
    assert image.getpixel((15, 15))[3] == (255 if invert else 0)


@pytest.mark.parametrize("empty", [False, True])
@pytest.mark.parametrize("opacity", [0, 1])
def test_composed_drawable_parent_keeps_unmasked_frame_and_unclipped_child(empty, opacity):
    canvas = (
        Canvas(240, 180)
        .shape(
            "rectangle",
            (90, 60),
            100,
            50,
            "#FF0000",
            align=Align.CENTER,
            rotation=31,
            opacity=opacity,
            id="owner",
            clip=LayerClip(position=(500, 500) if empty else (70, 50), width=12, height=10),
        )
        .shape("rectangle", (80, 20), 12, 9, "#00FF00", parent="owner")
    )
    owner = cast(Any, canvas.layers[0])
    bare = owner.model_copy(update={"clip": None})
    geometry, original = parent_geometry(canvas, owner), parent_geometry(canvas, bare)
    assert (geometry.origin, geometry.body_size, geometry.body_to_baked) == (
        original.origin,
        original.body_size,
        original.body_to_baked,
    )
    reference = Canvas(240, 180, layers=[bare.model_copy(update={"opacity": 0}), canvas.layers[1]])
    actual, expected = canvas._render_to_image(), reference._render_to_image()
    assert actual.getchannel("G").getextrema()[1] == 255
    for x in range(actual.width):
        for y in range(actual.height):
            if expected.getchannel("G").getpixel((x, y)) == 255:
                assert actual.getpixel((x, y)) == expected.getpixel((x, y))
    node = ParentRenderPlan(canvas).nodes[id(owner)]
    if empty:
        assert node.pivot_box == (0, 0, *geometry.body_size)
    assert node.image is None if empty or not opacity else node.image is not None


@pytest.mark.parametrize("style", ["plain", "odometer", "flip"])
def test_dynamic_counter_owner_mask_is_once_and_source_offset_is_current(style):
    canvas = Canvas(500, 320).counter(
        -999,
        1111,
        1,
        position=(250, 160),
        align=Align.CENTER,
        font=FONT,
        size=42,
        prefix="$",
        suffix=" kg",
        style=style,
        rotation=23,
        easing="linear",
        effects=[
            Background(color="#145582", padding=8),
            Shadow(offset_x=-8, offset_y=6, blur_radius=2, color="#000000"),
        ],
        clip=LayerClip(
            position=(230, 165), width=160, height=100, align=Align.CENTER, border_radius=12
        ),
        mask=LayerMask(shape="ellipse", position=(170, 115), width=170, height=100, opacity=0.4),
    )
    parented = linked(canvas)
    animator = _SlideAnimator(parented, {})
    node = animator._units[-1].parent_node
    geometry = node.origin, node.body_to_baked, node.pivot_box, node.source_size
    offsets = set()
    for time in (0.1, 0.817, 0.333, 1, 0, 0.817):
        assert animator.frame_at(time).tobytes() == canvas.render_frame(time).tobytes()
        assert geometry == (node.origin, node.body_to_baked, node.pivot_box, node.source_size)
        _, offset = node.render_sample(time, None)
        offsets.add(offset)
    assert len(offsets) > 1


def test_offcanvas_boundary_survives_ancestor_placement_and_shear():
    from quickthumb._parent_render import affine_fragment, multiply, translate

    canvas = (
        Canvas(320, 220)
        .null(
            (205, 115),
            id="root",
            animation=motion(track(RotationTrack, 0, 32), track(ScaleXTrack, 1, 1.7)),
        )
        .null(
            (10, 5),
            id="inner",
            parent="root",
            rotation=-17,
            animation=motion(track(ScaleYTrack, 1, 0.55)),
        )
        .shape(
            "rectangle",
            (-90, -45),
            120,
            80,
            "#CC7722",
            parent="inner",
            rotation=23,
            clip=LayerClip(position=(-70, -35), width=75, height=50, border_radius=12),
            mask=LayerMask(shape="ellipse", position=(-85, -30), width=90, height=70, opacity=0.6),
            animation=motion(track(RotationTrack, 0, -24)),
        )
    )
    animator = _SlideAnimator(canvas, {})
    node = animator._units[-1].parent_node
    assert node.image is not None and node.image.getbbox()
    for time in (0.1, 0.8, 1, 0.1):
        expected = Image.new("RGBA", (320, 220))
        paint = animator._sample_parents(time)[id(node)][0]
        fragment = affine_fragment(
            node.image, multiply(paint, translate(-node.padding, -node.padding)), expected.size
        )
        assert fragment is not None
        expected.alpha_composite(*fragment)
        assert animator.frame_at(time).tobytes() == expected.tobytes()


@pytest.mark.parametrize("quality", ["standard", "high"])
def test_composed_static_stagger_splits_and_recolors_composed_source(quality):
    canvas = Canvas(350, 300).text(
        "ONE\nTWO\nTHREE",
        position=(100, 50),
        size=26,
        font=FONT,
        line_height=2,
        clip=LayerClip(position=(100, 45), width=65, height=180, border_radius=8),
        mask=LayerMask(position=(100, 45), width=65, height=180, opacity=0.5),
        animation=stagger_motion(
            track(ColorTrack, "#E33A20", "#286FCC"),
            track(PositionTrack, (0, 12), (0, 0)),
            stagger=0.25,
        ),
    )
    parented = linked(canvas)
    animator = _SlideAnimator(parented, {}, quality=quality)
    assert len(animator._units[-1].target_images) == 3
    for time in (0, 0.25, 0.5, 1, 1.5, 0.25):
        assert (
            animator.frame_at(time).tobytes()
            == _SlideAnimator(canvas, {}, quality=quality).frame_at(time).tobytes()
        )


@pytest.mark.parametrize("opacity", [0, 0.4, 1])
def test_owner_pivot_and_reveal_use_composed_settled_reference(opacity):
    canvas = Canvas(260, 180).shape(
        "rectangle",
        (80, 50),
        100,
        60,
        "#EE5533",
        opacity=opacity,
        clip=LayerClip(position=(110, 60), width=35, height=25),
        animation=motion(
            track(RotationTrack, 0, 0),
            track(ClipProgressTrack, 0.2, 1),
            track(OpacityTrack, 0.4, 1),
        ),
    )
    parented = linked(canvas)
    animator = _SlideAnimator(parented, {})
    node = animator._units[-1].parent_node
    assert node.pivot_box == (30, 10, 35, 25)
    for time in (0.8, 0.2, 1, 0.8):
        assert animator.frame_at(time).tobytes() == canvas.render_frame(time).tobytes()


@pytest.mark.parametrize("background", [None, "#000000"])
@pytest.mark.parametrize("opacity", [0.4, 1])
def test_composed_text_contrast_samples_actual_pixels_without_double_attenuation(
    background, opacity
):
    canvas = Canvas(300, 180)
    if background:
        canvas.background(color=background)
    canvas.null((30, 15), id="root").text(
        "MMMM",
        position=(25, 25),
        font="assets/fonts/Roboto-Medium.ttf",
        size=55,
        color="#000000",
        effects=[Background(color="#FFFFFF", padding=10)],
        opacity=opacity,
        parent="root",
        id="text",
        mask=LayerMask(position=(20, 20), width=240, height=100, opacity=0.5),
    )
    sources, measured = setup(canvas)
    running = canvas._create_canvas()
    if background:
        canvas._render_layer(running, canvas.layers[0])
    backing, foreground = sources.text_images(running, measured[-1])
    visible = Image.new("RGBA", running.size, "white")
    visible.alpha_composite(canvas._render_to_image())
    alpha = foreground.getchannel("A")
    highest = alpha.getextrema()[1]
    glyphs = (
        Canvas(300, 180)
        .text(
            "MMMM",
            position=(55, 40),
            font="assets/fonts/Roboto-Medium.ttf",
            size=55,
            color="#FFFFFF",
        )
        ._render_to_image()
        .getchannel("A")
    )
    points = [
        (x, y)
        for y in range(180)
        for x in range(300)
        if alpha.getpixel((x, y)) == highest and glyphs.getpixel((x, y)) == 255
    ]
    assert len(points) > 20
    for point in points:
        assert (
            cast(tuple[int, int, int, int], foreground.getpixel(point))[:3]
            == cast(tuple[int, int, int, int], visible.getpixel(point))[:3]
        )
    # Use a core-only sampling probe to isolate treatment opacity from edge AA.
    marker = Image.new("L", foreground.size)
    for point in points:
        if (
            cast(tuple[int, int, int, int], visible.getpixel(point))[:3]
            == cast(tuple[int, int, int, int], visible.getpixel(points[0]))[:3]
        ):
            marker.putpixel(point, highest)
    foreground.putalpha(marker)
    result = worst_tile_contrast(backing, foreground, BBox(0, 0, 300, 180), tile_size=300)
    assert result is not None
    assert result.foreground == pytest.approx(
        cast(tuple[int, int, int, int], visible.getpixel(points[0]))[:3]
    )
    assert composite(canvas, sources, measured).tobytes() == canvas._render_to_image().tobytes()
    assert canvas._render_to_image(debug=True).size == (300, 180)
    canvas.diagnose()


def test_inspection_maps_composed_bounds_without_painting_or_moving_child(monkeypatch):
    canvas = (
        Canvas(240, 180)
        .null((40, 20), id="root", rotation=90)
        .shape(
            "rectangle",
            (20, 10),
            100,
            60,
            "#EE5533",
            parent="root",
            id="owner",
            clip=LayerClip(position=(35, 25), width=30, height=20),
        )
        .shape("rectangle", (80, 30), 10, 10, "#00FF00", parent="owner")
    )
    monkeypatch.setattr(canvas, "_render_layer", lambda *_: pytest.fail("inspection painted"))
    measured = measure_layers(canvas)
    assert measured[1].bbox == BBox(-5, 55, 20, 30)
    assert measured[2].bbox == BBox(-10, 120, 10, 10)


@pytest.mark.parametrize("kind", ["html", "svg", "pptx"])
def test_composed_document_static_fallback_embeds_shared_pixels(kind):
    canvas = (
        Canvas(220, 180)
        .null((40, 25), id="root", rotation=25)
        .counter(
            11,
            88,
            1,
            position=(20, 15),
            font=FONT,
            size=40,
            parent="root",
            clip=LayerClip(position=(20, 20), width=55, height=40, border_radius=6),
            mask=LayerMask(shape="ellipse", position=(15, 10), width=70, height=60, opacity=0.6),
        )
    )
    actual = embedded_png(getattr(canvas, "to_" + kind)(), kind)
    assert actual.tobytes() == canvas._render_to_image().tobytes()


@pytest.mark.parametrize("boundary", ["identity", "rounded", "polygon"])
def test_composed_contrast_does_not_count_antialias_fringe_as_faint_text(boundary):
    canvas = (
        Canvas(500, 200)
        .background(color="#FFFFFF")
        .null(id="root")
        .text(
            "WORLD HELLO",
            position=(30, 40),
            size=64,
            font="assets/fonts/Roboto-Medium.ttf",
            color="#000000",
            parent="root",
        )
    )
    layer = cast(Any, canvas.layers[-1])
    if boundary == "identity":
        layer.clip = LayerClip(position=(0, 0), width=500, height=200)
    elif boundary == "rounded":
        layer.clip = LayerClip(position=(45, 45), width=300, height=75, border_radius=25)
    else:
        layer.mask = LayerMask(
            shape="polygon",
            position=(45, 45),
            width=300,
            height=75,
            points=[(0, 0.2), (1, 0), (0.9, 1), (0, 0.8)],
        )
    assert not any(item.code == "low-contrast" for item in canvas.diagnose().findings)


def test_parent_composition_visual_snapshot():
    from pathlib import Path

    from examples.parent_composition import build_scene

    actual = build_scene().render_frame(0.7)
    expected = Image.open(Path(__file__).parent / "snapshots/parent_composition.png").convert(
        "RGBA"
    )
    assert actual.size == expected.size and actual.tobytes() == expected.tobytes()


def test_html_samples_affine_css_around_composed_static_source():
    from quickthumb._export_html import HtmlExporter

    from tests.test_parent_html import bake, css_row, source_image

    canvas = (
        Canvas(200, 140)
        .null(
            (70, 50),
            id="root",
            animation=motion(track(RotationTrack, 0, 35), track(ScaleXTrack, 1, 1.4)),
        )
        .shape(
            "rectangle",
            (10, 5),
            70,
            40,
            "#FF8800",
            parent="root",
            clip=LayerClip(position=(15, 10), width=45, height=25, border_radius=8),
            mask=LayerMask(shape="ellipse", position=(10, 5), width=60, height=35, opacity=0.4),
        )
    )
    baked = bake(canvas)
    node = baked.sources[id(canvas.layers[-1])]
    stage = HtmlExporter(canvas).render_stage()
    assert stage.timeline
    assert embedded_png(stage.body, "html").tobytes() == source_image(node).tobytes()
    assert stage.timeline[0]["initial"] == css_row(node.rows[0])
    assert stage.timeline[0]["final"] == css_row(node.rows[-1])
    assert (
        next(item for item in canvas.validate_export("video") if item.feature == "parent").support
        == "full"
    )


@pytest.mark.parametrize("quality", ["standard", "high"])
def test_composed_counter_serial_spawn_gif_bytes_match(tmp_path, quality):
    from quickthumb import GifOptions

    canvas = (
        Canvas(180, 120)
        .null((80, 45), id="root", rotation=17)
        .counter(
            99,
            105,
            0.6,
            style="odometer",
            position=(0, 0),
            align="center",
            size=25,
            font=FONT,
            parent="root",
            clip=LayerClip(position=(-40, -20), width=80, height=50, border_radius=8),
            mask=LayerMask(shape="ellipse", position=(-40, -25), width=80, height=55, opacity=0.6),
        )
    )
    serial, parallel = tmp_path / "serial.gif", tmp_path / "parallel.gif"
    for workers, path in ((1, serial), (2, parallel)):
        canvas.render(str(path), animation=GifOptions(fps=5, quality=quality, workers=workers))
    assert serial.read_bytes() == parallel.read_bytes()


@pytest.mark.parametrize("inverted", [False, True])
def test_partial_mask_contrast_keeps_real_treatment_inside_and_outside(inverted):
    canvas = (
        Canvas(400, 160)
        .background(color="#FFFFFF")
        .null((20, 0), id="root")
        .text(
            "MMMMMMMM",
            position=(20, 35),
            size=45,
            font="assets/fonts/Roboto-Medium.ttf",
            color="#000000",
            parent="root",
            id="text",
            mask=LayerMask(
                position=(20, 20),
                width=120,
                height=100,
                opacity=0.1 if not inverted else 0.9,
                invert=inverted,
            ),
        )
    )
    sources, measured = setup(canvas)
    running = canvas._create_canvas()
    canvas._render_layer(running, canvas.layers[0])
    backing, foreground = sources.text_images(running, measured[-1])
    inside = worst_tile_contrast(backing, foreground, BBox(50, 40, 90, 55), tile_size=90)
    assert inside is not None and inside.contrast < 1.5
    outside = worst_tile_contrast(backing, foreground, BBox(165, 40, 140, 55), tile_size=140)
    if inverted:
        assert outside is not None and outside.contrast > 15
    else:
        assert outside is None
    assert any(item.code == "low-contrast" for item in canvas.diagnose().findings)


def test_nested_group_animated_descendant_composition_rejects_before_deck_output(tmp_path):
    from quickthumb import AnimationSpec, Deck, ExportPolicy, GroupLayer, ShapeLayer
    from quickthumb.errors import RenderingError

    leaf = ShapeLayer(
        type="shape",
        shape="rectangle",
        position=(0, 0),
        width=30,
        height=20,
        color="#FFFFFF",
        mask=LayerMask(position=(0, 0), width=20, height=15),
        animation=AnimationSpec.fade(duration=1),
    )
    inner = GroupLayer(type="group", children=[leaf])
    canvas = Canvas(100, 80).null(id="root").group([inner], parent="root")
    for target in ("raster", "video", "html", "pptx"):
        with pytest.raises(RenderingError, match="descendants"):
            canvas.validate_export(target, ExportPolicy(unsupported_motion="error"))
    destination = tmp_path / "slides.png"
    first = tmp_path / "slides_01.png"
    first.write_bytes(b"existing")
    with pytest.raises(RenderingError, match="descendants"):
        Deck(100, 80).slide(Canvas(100, 80)).slide(canvas).render(str(destination))
    assert first.read_bytes() == b"existing"


@pytest.mark.parametrize(
    "font,size",
    [
        ("assets/fonts/Roboto-Medium.ttf", 8),
        ("assets/fonts/Roboto-Medium.ttf", 10),
        (FONT, 8),
        (FONT, 16),
    ],
)
@pytest.mark.parametrize("rotation", [7, 23, 45])
@pytest.mark.parametrize("color", ["#000000", "#707070", "#888888", "#DDDDDD"])
def test_identity_clip_keeps_thin_transformed_text_contrast(font, size, rotation, color):
    canvas = (
        Canvas(400, 200)
        .background(color="#FFFFFF")
        .null((180, 80), id="root", rotation=rotation)
        .text(
            "thin mini lill ill",
            position=(0, 0),
            font=font,
            size=size,
            color=color,
            parent="root",
            id="text",
        )
    )
    before = [item for item in canvas.diagnose().findings if item.code == "low-contrast"]
    cast(Any, canvas.layers[-1]).clip = LayerClip(position=(-100, -100), width=600, height=400)
    after = [item for item in canvas.diagnose().findings if item.code == "low-contrast"]
    assert bool(after) == bool(before)
    if color == "#000000":
        assert not after


def test_zero_opacity_inverted_mask_does_not_remove_thin_text_evidence():
    canvas = (
        Canvas(200, 100)
        .background(color="#FFFFFF")
        .null(id="root")
        .text(
            "I",
            position=(40, 30),
            font="assets/fonts/Roboto-Medium.ttf",
            size=20,
            color="#DDDDDD",
            parent="root",
            clip=LayerClip(position=(0, 0), width=200, height=100),
        )
    )
    before_pixels = canvas._render_to_image().tobytes()
    before = [item for item in canvas.diagnose().findings if item.code == "low-contrast"]
    cast(Any, canvas.layers[-1]).mask = LayerMask(
        position=(40, 20), width=3, height=50, invert=True, opacity=0
    )
    after = [item for item in canvas.diagnose().findings if item.code == "low-contrast"]
    assert canvas._render_to_image().tobytes() == before_pixels
    assert before and after and before[0].measured["contrast"] == after[0].measured["contrast"]
