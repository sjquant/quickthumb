"""Authored-static conservative parent bounds preserve local measurement metadata."""

import math

import pytest
from quickthumb import (
    AnimationSpec,
    Canvas,
    Deck,
    InspectionBBox,
    KeyframeSpec,
    LayerClip,
    NullLayer,
    PositionTrack,
    ShapeLayer,
    TextLayer,
    TimingSpec,
)
from quickthumb._measurements import BBox, LayerMeasurementEngine
from quickthumb._parent_inspection import transform_bbox
from quickthumb._parent_render import IDENTITY, ParentNode
from quickthumb.errors import RenderingError, ValidationError


def scene():
    return (
        Canvas(200, 130)
        .null((100, 50), id="root")
        .shape("rectangle", (10, 20), 20, 10, "#FF0000", parent="root", id="child")
    )


def test_world_position_is_parent_local_and_inspection_does_not_paint(monkeypatch):
    canvas = scene()
    before = canvas.to_json()
    monkeypatch.setattr(
        ParentNode, "render_source", lambda *_args, **_kwargs: pytest.fail("source paint")
    )
    monkeypatch.setattr(canvas, "_render_layer", lambda *_args: pytest.fail("layer paint"))
    report = canvas.inspect()
    assert report.layers[0].bbox is None and not report.layers[0].visible
    assert report.layers[1].bbox == InspectionBBox(x=110, y=70, width=20, height=10)
    assert canvas.to_json() == before


@pytest.mark.parametrize("angle", [0, 90, 180, 270, 360, -90])
def test_cardinal_parent_rotation_has_no_one_pixel_roundoff_inflation(angle):
    canvas = Canvas(200, 130).null((100, 50), id="root", rotation=angle)
    canvas.shape("rectangle", (0, 0), 20, 10, "#FF0000", parent="root")
    expected = {
        0: (100, 50, 20, 10),
        90: (90, 50, 10, 20),
        180: (80, 40, 20, 10),
        270: (100, 30, 10, 20),
    }[angle % 360]
    assert canvas.inspect().layers[1].bbox == InspectionBBox(
        x=expected[0], y=expected[1], width=expected[2], height=expected[3]
    )


def test_three_levels_compose_before_world_bbox_measurement():
    canvas = (
        Canvas(200, 130)
        .null((100, 50), id="root", rotation=90)
        .null((20, 10), id="arm", parent="root", rotation=90)
        .shape("rectangle", (5, 2), 10, 4, "#FF0000", parent="arm")
    )
    assert canvas.inspect().layers[-1].bbox == InspectionBBox(x=75, y=64, width=10, height=4)


def test_static_inspection_ignores_motion_samples_and_invisible_parent_opacity():
    animation = AnimationSpec.timeline(
        PositionTrack(
            keyframes=[KeyframeSpec(time=0, value=(100, 0)), KeyframeSpec(time=1, value=(200, 0))]
        ),
        timing=TimingSpec(duration=1),
    )
    canvas = (
        Canvas(400, 130)
        .shape("rectangle", (100, 50), 20, 10, "#FFFFFF", id="root", opacity=0, animation=animation)
        .shape("rectangle", (10, 20), 20, 10, "#FF0000", parent="root")
    )
    report = canvas.inspect()
    assert not report.layers[0].visible and report.layers[1].visible
    assert report.layers[1].bbox == InspectionBBox(x=110, y=70, width=20, height=10)
    assert canvas.render_frame(0).getbbox() == (210, 70, 230, 80)


def test_aligned_rotated_video_uses_renderers_expanded_body(tmp_path, monkeypatch):
    source = tmp_path / "clip.mp4"
    source.write_bytes(b"geometry needs no decoder")
    canvas = (
        Canvas(200, 130)
        .null((30, 20), id="root", rotation=90)
        .video(str(source), (50, 40), 20, 10, rotation=90, align="center", parent="root", id="clip")
        .shape("rectangle", (0, 0), 4, 4, "#FF0000", parent="clip")
    )
    monkeypatch.setattr(
        ParentNode, "render_source", lambda *_args, **_kwargs: pytest.fail("video decode")
    )
    report = canvas.inspect()
    # Video expanded body10x20, centred at(50,40), hence local(45,30,10,20).
    assert report.layers[1].bbox == InspectionBBox(x=-20, y=65, width=20, height=10)
    # The explicit child uses the video's full frame, including its own rotation.
    assert report.layers[2].bbox == InspectionBBox(x=-4, y=71, width=4, height=4)


def test_rich_text_retains_authored_auto_scale_metadata():
    canvas = (
        Canvas(400, 300)
        .null((10, 20), id="root", rotation=33)
        .text(
            [
                {"text": "ALPHA ", "size": 80, "color": "#000000"},
                {"text": "BETA", "size": 40, "color": "#111111"},
            ],
            position=(10, 10),
            max_width=180,
            auto_scale=True,
            parent="root",
        )
    )
    original = canvas.layers[1]
    assert isinstance(original, TextLayer)
    plain = Canvas(400, 300, layers=[original.model_copy(update={"parent": None})])
    text = canvas.inspect().layers[1].text
    assert text is not None
    assert text == plain.inspect().layers[0].text
    assert text.auto_scaled
    assert canvas.layers[1] is original


def test_nested_group_descendants_and_explicit_child_use_distinct_frames():
    canvas = (
        Canvas(200, 130)
        .null((100, 50), id="root", rotation=90)
        .group(
            [
                {
                    "type": "group",
                    "children": [
                        {
                            "type": "shape",
                            "shape": "rectangle",
                            "width": 10,
                            "height": 4,
                            "color": "#FF0000",
                        }
                    ],
                    "padding": 2,
                }
            ],
            position=(20, 10),
            padding=3,
            id="group",
            parent="root",
        )
        .shape("rectangle", (1, 2), 4, 6, "#0000FF", parent="group", id="explicit")
    )
    local = LayerMeasurementEngine(canvas._ctx, canvas._groups, canvas._text).measure_layers(
        canvas.layers
    )
    report = canvas.inspect()
    ancestor = (0, -1, 100, 1, 0, 50)
    child = local[1].children[0].children[0]
    world_child = transform_bbox(child.bbox, ancestor)
    assert world_child is not None
    assert report.layers[1].children[0].children[0].bbox == InspectionBBox(
        **dict(
            zip(
                ("x", "y", "width", "height"),
                world_child.as_tuple(),
                strict=True,
            )
        )
    )
    assert report.layers[2].bbox == InspectionBBox(x=82, y=71, width=6, height=4)


def test_offcanvas_bounds_are_not_clipped_to_viewport():
    canvas = (
        Canvas(40, 30)
        .null((-100, 20), id="root")
        .shape("rectangle", (10, 20), 20, 10, "#FF0000", parent="root")
    )
    assert canvas.inspect().layers[1].bbox == InspectionBBox(x=-90, y=40, width=20, height=10)


@pytest.mark.parametrize("bbox", [BBox(3, 4, 0, 10), BBox(3, 4, 10, 0), BBox(3, 4, 0, 0)])
def test_empty_boxes_stay_empty_under_rotation(bbox):
    rotated = transform_bbox(bbox, (0.5, -0.8, 3, 0.8, 0.5, 4))
    assert rotated is not None and rotated.is_empty
    assert transform_bbox(bbox, IDENTITY) is bbox
    assert transform_bbox(None, (0.5, -0.8, 3, 0.8, 0.5, 4)) is None


def test_conservative_body_bounds_are_not_claimed_alpha_tight():
    canvas = (
        Canvas(200, 130)
        .null((100, 50), id="root", rotation=45)
        .shape("rectangle", (0, 0), 20, 10, "#FF0000", rotation=45, parent="root")
    )
    local = LayerMeasurementEngine(canvas._ctx, canvas._groups, canvas._text).measure_layers(
        canvas.layers
    )[1]
    world = transform_bbox(
        local.bbox, (math.sqrt(0.5), -math.sqrt(0.5), 100, math.sqrt(0.5), math.sqrt(0.5), 50)
    )
    assert world is not None
    assert canvas.inspect().layers[1].bbox == InspectionBBox(
        x=world.x, y=world.y, width=world.width, height=world.height
    )


def test_unsupported_observation_keeps_validation_warning_not_model_error():
    canvas = scene()
    canvas.layers[1].clip = LayerClip(position=(0, 0), width=2, height=2)
    with pytest.raises(RenderingError) as error:
        canvas.inspect()
    assert error.value.code == "unsupported_parent_rendering"
    report = canvas.validate()
    assert report.ok and report.warnings[0].code == "unsupported_parent_rendering"
    deck_report = Deck(200, 130).slide(Canvas(200, 130)).slide(canvas).validate()
    assert deck_report.ok and deck_report.warnings[0].path == "/slides/1"


def test_diagnostics_remain_guarded_before_any_local_paint(monkeypatch):
    canvas = scene()
    monkeypatch.setattr(canvas, "_render_layer", lambda *_args: pytest.fail("local paint"))
    with pytest.raises(RenderingError) as error:
        canvas.diagnose()
    assert error.value.code == "unsupported_parent_rendering"


def test_debug_overlay_uses_static_world_bounds_but_sampled_debug_stays_guarded():
    canvas = scene()
    image = canvas._render_to_image(debug=True)
    assert image.getpixel((110, 70)) == (255, 45, 85, 255)
    with pytest.raises(RenderingError):
        canvas._render_to_image(debug=True, time=0)


def test_graph_mutations_revalidate_before_world_measurement():
    canvas = scene()
    canvas.layers[0].parent = "child"
    with pytest.raises(ValidationError, match="cycle"):
        canvas.inspect()


def test_reused_anonymous_layer_occurrences_keep_their_inspection_identity():
    shared = ShapeLayer(
        type="shape",
        shape="rectangle",
        position=(10, 20),
        width=20,
        height=10,
        color="#FF0000",
        parent="root",
    )
    canvas = Canvas(200, 130, layers=[NullLayer(type="null", id="root"), shared, shared])
    report = canvas.inspect()
    assert [item.id for item in report.layers] == ["root", "layer:1", "layer:2"]
    assert [item.index for item in report.layers] == [0, 1, 2]
    assert report.layers[1].bbox == report.layers[2].bbox


def test_unlinked_inspection_is_the_existing_measurement_path(monkeypatch):
    from quickthumb import _parent_inspection

    canvas = (
        Canvas(200, 130)
        .text("Hello", position=(20, 20), size=18)
        .shape("rectangle", (20, 80), 30, 10, "#FF0000")
    )
    expected = canvas.inspect().model_dump_json()
    monkeypatch.setattr(
        _parent_inspection, "measure_parent_layers", lambda *_: pytest.fail("parent path")
    )
    assert canvas.inspect().model_dump_json() == expected


def test_deep_null_chain_inspection_is_iterative():
    layers = [NullLayer(type="null", id="root", position=(1, 1))]
    layers += [
        NullLayer(
            type="null", id=f"n{i}", parent="root" if i == 0 else f"n{i - 1}", position=(1, 1)
        )
        for i in range(1200)
    ]
    layers += [
        ShapeLayer(
            type="shape",
            shape="rectangle",
            position=(0, 0),
            width=2,
            height=3,
            color="#FF0000",
            parent="n1199",
        )
    ]
    canvas = Canvas(40, 30, layers=layers)
    assert canvas.inspect().layers[-1].bbox == InspectionBBox(x=1201, y=1201, width=2, height=3)


def test_nonfinite_world_bounds_are_rejected():
    with pytest.raises(RenderingError, match="finite coordinates"):
        transform_bbox(BBox(2, 3, 4, 5), (1e308, 0, 0, 0, 1, 0))
