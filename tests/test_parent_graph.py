"""Explicit parent graph contract, independent of its subsequent render adapter."""

import json

import jsonschema
import pytest
from quickthumb import Canvas, ExportPolicy, NullLayer, ShapeLayer, canvas_json_schema
from quickthumb.errors import RenderingError, ValidationError
from quickthumb.models import CanvasModel, CanvasSpecModel, GroupLayer
from quickthumb.motion import capabilities_for


def node(id, parent=None):
    return NullLayer(type="null", id=id, parent=parent)


def scene():
    return (
        Canvas(140, 130)
        .null((5, 6), id="root")
        .shape("rectangle", (2, 3), 4, 5, "#FF0000", parent="root", id="child")
    )


def test_parent_null_schema_roundtrip_and_inspection():
    canvas = scene()
    spec = json.loads(canvas.to_json())
    jsonschema.validate(spec, canvas_json_schema())
    restored = Canvas.from_json(canvas.to_json())
    assert restored.to_json() == canvas.to_json()
    assert isinstance(restored.layers[0], NullLayer)
    assert "parent" not in spec["layers"][0]
    assert "anchor" not in spec["layers"][0]
    report = restored.inspect_motion()
    assert report.slides[0].layers[0].layer_type == "null"
    assert report.slides[0].layers[1].parent == "root"
    assert {item.feature for item in report.capabilities} == {"parent"}
    assert {item.target: item.support for item in report.capabilities} == {
        "raster": "full",
        "video": "full",
        "html": "unsupported",
        "pptx": "unsupported",
    }
    assert "parent" not in report.slides[0].layers[0].model_dump()
    assert restored.validate().ok


@pytest.mark.parametrize("parent", ["", " leading", "trailing ", "a/b", "1root", 3, True])
def test_parent_identifier_syntax_is_strict(parent):
    with pytest.raises(ValidationError):
        node("child", parent)


@pytest.mark.parametrize("cls", [Canvas, CanvasModel, CanvasSpecModel])
def test_complete_scenes_allow_forward_references_and_deep_chains(cls):
    layers = [node(f"n{index}", f"n{index + 1}") for index in range(1200)] + [node("n1200")]
    canvas = cls(width=40, height=30, layers=layers)
    assert len(canvas.layers) == 1201


@pytest.mark.parametrize("parents", [("a",), ("b", "a"), ("b", "c", "a")])
def test_cycles_report_parent_pointer_and_cycle(parents):
    with pytest.raises(ValidationError) as error:
        Canvas(40, 30, layers=[node(chr(97 + i), parent) for i, parent in enumerate(parents)])
    assert error.value.code == "parent_cycle"
    assert (error.value.details[0].path or "").endswith("/parent")
    assert " -> " in str(error.value)


@pytest.mark.parametrize("cls", [Canvas, CanvasModel, CanvasSpecModel])
def test_missing_parent_is_a_structured_validation_error(cls):
    with pytest.raises(ValidationError) as error:
        cls(width=40, height=30, layers=[node("child", "missing")])
    assert error.value.code == "missing_parent"
    assert error.value.details[0].path == "/layers/0/parent"
    assert error.value.details[0].layer_id == "child"


def test_nonanimatable_parent_rejected():
    canvas = Canvas(40, 30).background(color="#FFFFFF", id="background")
    with pytest.raises(ValidationError, match="must be an animatable layer"):
        canvas.null(id="child", parent="background")
    assert len(canvas.layers) == 1


def test_failed_append_and_replacement_roll_back():
    canvas = Canvas(40, 30).null(id="root")
    before = canvas.to_json()
    with pytest.raises(ValidationError, match="does not exist"):
        canvas.null(id="child", parent="missing")
    assert canvas.to_json() == before
    with pytest.raises(ValidationError, match="cycle"):
        canvas.layers = [node("cycle", "cycle")]
    assert canvas.to_json() == before
    with pytest.raises(ValidationError, match="duplicate layer id: root"):
        canvas.null(id="root")
    assert canvas.to_json() == before


@pytest.mark.parametrize("inside", [True, False])
def test_links_involving_group_descendants_are_explicitly_rejected(inside):
    child = ShapeLayer(
        type="shape",
        shape="rectangle",
        position=(0, 0),
        width=4,
        height=4,
        color="#FF0000",
        id="nested",
        parent="root" if inside else None,
    )
    group = GroupLayer(type="group", children=[child], id="group")
    with pytest.raises(ValidationError, match="auto-layout group descendant") as error:
        Canvas(40, 30, layers=[node("root"), group, node("other", None if inside else "nested")])
    assert error.value.details[0].path == (
        "/layers/1/children/0/parent" if inside else "/layers/2/parent"
    )


def test_top_level_groups_can_be_parented_and_referenced():
    canvas = (
        Canvas(40, 30)
        .null(id="root")
        .group(
            [{"type": "shape", "shape": "rectangle", "width": 4, "height": 4, "color": "#FF0000"}],
            id="group",
            parent="root",
        )
        .null(id="leaf", parent="group")
    )
    assert canvas.validate().ok


@pytest.mark.parametrize("target", ["html", "pptx"])
def test_document_formats_declare_unsupported_without_claiming_a_fallback(target):
    diagnostics = scene().validate_export(target)
    diagnostic = next(item for item in diagnostics if item.feature == "parent")
    assert diagnostic.support == "unsupported" and diagnostic.fallback is None
    assert capabilities_for(target)["parent"].support == "unsupported"
    assert capabilities_for(target)["parent"].fallback is None
    with pytest.raises(RenderingError, match="parent transforms"):
        scene().validate_export(target, ExportPolicy(unsupported_motion="error"))


@pytest.mark.parametrize("method", ["to_html", "to_svg", "to_pptx", "to_pdf"])
def test_model_only_exports_fail_instead_of_silently_ignoring_links(method):
    with pytest.raises(RenderingError) as error:
        getattr(scene(), method)()
    assert error.value.code == "unsupported_parent_rendering"


def test_model_mutation_is_revalidated_before_drawing():
    canvas = scene()
    canvas.layers[0].parent = "child"
    assert not canvas.validate().ok
    with pytest.raises(ValidationError, match="cycle"):
        canvas.render_frame(0)
    with pytest.raises(ValidationError, match="cycle"):
        canvas.validate_export("html")


def test_unlinked_null_is_nonrendering_and_existing_json_unchanged():
    base = Canvas(40, 30).shape("rectangle", (2, 3), 4, 5, "#FF0000")
    explicit = Canvas(40, 30).shape("rectangle", (2, 3), 4, 5, "#FF0000", parent=None)
    assert base.to_json() == explicit.to_json()
    assert "parent" not in base.to_json()
    assert Canvas(40, 30).null().render_frame(0).getbbox() is None
    assert (
        explicit.null((100, -200), rotation=45).render_frame(0).tobytes()
        == base.render_frame(0).tobytes()
    )


def test_null_not_allowed_in_auto_layout_and_unknown_fields_rejected():
    with pytest.raises(ValidationError):
        GroupLayer.model_validate({"type": "group", "children": [{"type": "null"}]})
    with pytest.raises(ValidationError):
        NullLayer.model_validate({"type": "null", "opacity": 0.5})


@pytest.mark.parametrize("rotation", [float("inf"), float("nan")])
def test_null_rotation_is_finite(rotation):
    with pytest.raises(ValidationError):
        NullLayer(type="null", rotation=rotation)


@pytest.mark.parametrize("method", ["inspect", "diagnose"])
def test_layout_observations_do_not_silently_ignore_parent_links(method):
    with pytest.raises(RenderingError) as error:
        getattr(scene(), method)()
    assert error.value.code == "unsupported_parent_rendering"


def test_null_layout_inspection_reports_nonrendering_node():
    layer = Canvas(40, 30).null(id="controller").inspect().layers[0]
    assert layer.type == "null" and not layer.visible and layer.bbox is None


def test_null_does_not_capture_targets_from_a_shared_animation():
    from quickthumb import AnimationSpec
    from quickthumb._export_video import _SlideAnimator

    animation = AnimationSpec.rise(
        from_="bottom", distance=20, duration=0.5, stagger=0.4, target="lines"
    )
    expected = Canvas(200, 150).text(
        "ONE\nTWO\nTHREE",
        font="assets/fonts/Pretendard-ExtraBold.woff2",
        size=20,
        color="#FFFFFF",
        position=(20, 20),
        line_height=1.3,
        animation=animation,
    )
    actual = Canvas(
        200, 150, layers=[NullLayer(type="null", animation=animation), *expected.layers]
    )
    baseline, with_null = _SlideAnimator(expected, {}), _SlideAnimator(actual, {})
    assert baseline.duration == with_null.duration == 1.3
    for instant in (0, 0.2, 0.5, 1, 1.3):
        assert baseline.frame_at(instant).tobytes() == with_null.frame_at(instant).tobytes()


@pytest.mark.parametrize(
    "method,args,kwargs",
    [
        ("text", ("hi",), {}),
        ("shape", ("rectangle", (0, 0), 4, 5, "#FF0000"), {}),
        ("image", ("image.png", (0, 0)), {}),
        ("svg", ("shape.svg", (0, 0)), {}),
        ("video", ("clip.mp4", (0, 0), 4, 4), {}),
        (
            "chart",
            (),
            {"spec": {"type": "bar", "data": [1, 2]}, "position": (0, 0), "width": 8, "height": 8},
        ),
        ("qr_code", ("payload",), {}),
        ("group", ([{"type": "text", "content": "hi"}],), {}),
        ("null", (), {}),
    ],
)
def test_all_animatable_builders_preserve_parent_keyword(method, args, kwargs):
    canvas = Canvas(40, 30).null(id="controller")
    getattr(canvas, method)(*args, **kwargs, parent="controller")
    assert getattr(canvas.layers[-1], "parent", None) == "controller"
    spec = json.loads(canvas.to_json())
    jsonschema.validate(spec, canvas_json_schema())
    assert Canvas.from_json(canvas.to_json()).to_json() == canvas.to_json()


def test_validation_reports_deferred_layout_as_warning_on_canvas_and_deck():
    from quickthumb import Deck

    report = scene().validate()
    assert report.ok and report.warnings[0].code == "unsupported_parent_rendering"
    deck = Deck(140, 130).slide(Canvas(140, 130)).slide(scene())
    report = deck.validate()
    assert report.ok and report.warnings[0].path == "/slides/1"
    child = deck.slides[1].layers[1]
    assert isinstance(child, ShapeLayer)
    child.parent = "missing"
    with pytest.raises(ValidationError) as error:
        deck.validate_export("html")
    assert error.value.details[0].path == "/slides/1/layers/1/parent"


def test_null_preparation_never_allocates_a_source_canvas(monkeypatch):
    from quickthumb._export_video import _SlideAnimator

    canvas = Canvas(40, 30).null(id="controller")
    monkeypatch.setattr(canvas, "_render_layer", lambda *args: pytest.fail("null source render"))
    animator = _SlideAnimator(canvas, {})
    assert animator.frame_at(0).getbbox() is None


@pytest.mark.parametrize("extension", ["svg", "html", "pdf", "pptx"])
@pytest.mark.parametrize("method", ["render", "export"])
def test_model_only_rejection_preserves_existing_destination(tmp_path, extension, method):
    destination = tmp_path / f"existing.{extension}"
    destination.write_bytes(b"EXISTING DOCUMENT")
    with pytest.raises(RenderingError, match="Parent-linked rendering"):
        getattr(scene(), method)(str(destination))
    assert destination.read_bytes() == b"EXISTING DOCUMENT"


def test_deck_rejection_precedes_first_slide_sequence_write(tmp_path):
    from quickthumb import Deck

    deck = Deck(140, 130).slide(Canvas(140, 130)).slide(scene())
    destination = tmp_path / "slides.svg"
    first = tmp_path / "slides_01.svg"
    first.write_bytes(b"EXISTING SLIDE")
    with pytest.raises(RenderingError, match="Parent-linked rendering"):
        deck.render(str(destination))
    assert first.read_bytes() == b"EXISTING SLIDE"
    assert not (tmp_path / "slides_02.svg").exists()


def test_direct_pdf_rejection_preserves_existing_destination(tmp_path):
    from quickthumb._export_pdf import PdfExporter

    destination = tmp_path / "existing.pdf"
    destination.write_bytes(b"EXISTING PDF")
    with pytest.raises(RenderingError, match="Parent-linked rendering"):
        PdfExporter().save_canvases([Canvas(140, 130), scene()], destination)
    assert destination.read_bytes() == b"EXISTING PDF"


@pytest.mark.parametrize("first", [True, False])
def test_null_motion_does_not_transform_backdrop_prefix(first):
    from quickthumb import AnimationSpec, BackdropBlur, KeyframeSpec, PositionTrack, TimingSpec
    from quickthumb._export_video import _SlideAnimator

    controller = NullLayer(
        type="null",
        animation=AnimationSpec.timeline(
            PositionTrack(
                keyframes=[KeyframeSpec(time=0, value=(0, 0)), KeyframeSpec(time=1, value=(20, 0))]
            ),
            timing=TimingSpec(duration=1),
            easing="linear",
        ),
    )
    canvas = Canvas(140, 130).shape(
        "rectangle", (10, 10), 20, 20, "#FFFFFF", effects=[BackdropBlur(radius=1)]
    )
    baseline = canvas.render_frame(0).tobytes()
    canvas.layers = [controller, *canvas.layers] if first else [*canvas.layers, controller]
    animator = _SlideAnimator(canvas, {})
    assert animator.duration == 1
    assert all(len(unit.layers) == 1 for unit in animator._units)
    for instant in (0, 0.5, 1):
        assert (
            animator.frame_at(instant).tobytes()
            == baseline
            == canvas.render_frame(instant).tobytes()
        )
