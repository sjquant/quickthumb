"""Track mattes use sampled, scene-local layer surfaces without painting their sources."""

import json

import pytest
from PIL import Image
from quickthumb import (
    AnimationSpec,
    Canvas,
    ExportPolicy,
    KeyframeSpec,
    PositionTrack,
    ShapeLayer,
    TimingSpec,
    TrackMatte,
    ValidationError,
    canvas_json_schema,
)
from quickthumb.errors import RenderingError

from tests.test_parent_documents import embedded_png


@pytest.mark.parametrize(
    "mode,invert,alpha",
    [("alpha", False, 128), ("alpha", True, 127), ("luma", False, 63), ("luma", True, 192)],
)
def test_matte_channels_include_source_alpha_and_inversion(mode, invert, alpha):
    """A translucent source contributes alpha-weighted luma with full-canvas inversion."""
    # Given: a translucent source covering half a red target
    canvas = Canvas(40, 20).shape("rectangle", (0, 0), 20, 20, color="#80808080", id="source")
    canvas.shape(
        "rectangle",
        (0, 0),
        40,
        20,
        color="#FF0000",
        mask=TrackMatte(layer="source", mode=mode, invert=invert),
    )
    # When: sampling the actual canonical raster
    image = canvas.render_frame(0)
    # Then: the source is hidden and the target preserves straight red RGB and expected alpha
    assert image.getpixel((5, 5)) == (255, 0, 0, alpha)
    assert image.getpixel((30, 5)) == ((255, 0, 0, 255) if invert else (0, 0, 0, 0))


def test_matte_sources_are_reusable_forward_references_and_support_chains():
    """Multiple targets share one hidden source, including a source masked by another source."""
    # Given: two half-width sources, with the second masking both red and blue targets
    canvas = Canvas(40, 20)
    canvas.shape("rectangle", (0, 0), 20, 20, color="#FFFFFF", id="first")
    canvas.shape(
        "rectangle", (0, 0), 40, 20, color="#FFFFFF", id="second", mask=TrackMatte(layer="first")
    )
    canvas.shape(
        "rectangle", (0, 0), 40, 10, color="#FF0000", id="red", mask=TrackMatte(layer="second")
    )
    canvas.shape(
        "rectangle", (0, 10), 40, 10, color="#0000FF", id="blue", mask=TrackMatte(layer="second")
    )
    canvas.layers = list(reversed(canvas.layers))
    # When: round-tripping the full scene through the public JSON schema
    import jsonschema

    jsonschema.validate(json.loads(canvas.to_json()), canvas_json_schema())
    restored = Canvas.from_json(canvas.to_json())
    image = restored.render_frame()
    # Then: reference order has no effect, sources stay hidden, and both targets receive the chain
    assert image.getpixel((5, 5)) == (255, 0, 0, 255)
    assert image.getpixel((5, 15)) == (0, 0, 255, 255)
    assert image.getpixel((30, 5)) == image.getpixel((30, 15)) == (0, 0, 0, 0)


def test_matte_and_target_motion_share_parent_world_coordinates():
    """A parented moving matte masks the sampled target after both world transforms."""
    # Given: a controller moving a ten-pixel matte across a fixed red target
    canvas = Canvas(60, 20).null(
        id="controller",
        animation=AnimationSpec(
            timing=TimingSpec(duration=1),
            easing="linear",
            tracks=[
                PositionTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value=(0, 0)),
                        KeyframeSpec(time=1, value=(20, 0)),
                    ]
                )
            ],
        ),
    )
    canvas.shape("rectangle", (0, 0), 10, 20, color="#FFFFFF", id="source", parent="controller")
    canvas.shape("rectangle", (0, 0), 60, 20, color="#FF0000", mask=TrackMatte(layer="source"))
    # When: sampling intermediate and settled canonical frames
    middle, end = canvas.render_frame(0.5), canvas.render_frame(1)
    # Then: matte pixels follow the inherited world translation at the same clock
    assert middle.getpixel((15, 5)) == end.getpixel((25, 5)) == (255, 0, 0, 255)
    assert middle.getpixel((5, 5)) == end.getpixel((15, 5)) == (0, 0, 0, 0)


@pytest.mark.parametrize("kind", ["missing", "self", "cycle", "nested"])
def test_matte_reference_graph_rejects_invalid_scenes_atomically(kind):
    """Invalid matte references and cycles fail before replacing a valid scene's layer list."""
    # Given: a valid scene and a proposed invalid dependency graph
    canvas = Canvas(20, 20).shape("rectangle", (0, 0), 20, 20, color="#FF0000", id="first")
    first = canvas.layers[0]
    assert isinstance(first, ShapeLayer)
    if kind == "missing":
        layers = [first.model_copy(update={"mask": TrackMatte(layer="missing")})]
    elif kind == "self":
        layers = [first.model_copy(update={"mask": TrackMatte(layer="first")})]
    elif kind == "cycle":
        second = ShapeLayer(
            type="shape",
            shape="rectangle",
            position=(0, 0),
            width=20,
            height=20,
            color="#FFFFFF",
            id="second",
            mask=TrackMatte(layer="first"),
        )
        layers = [first.model_copy(update={"mask": TrackMatte(layer="second")}), second]
    else:
        with pytest.raises(ValidationError):
            canvas.group(
                [first.model_copy(update={"id": "child", "mask": TrackMatte(layer="first")})]
            )
        assert canvas.layers == [first]
        return
    # When: assigning the proposed graph
    with pytest.raises(ValidationError):
        canvas.layers = layers
    # Then: failure preserves the actual original layer and its unmasked pixels
    assert canvas.layers == [first]
    assert canvas.render_frame().getpixel((5, 5)) == (255, 0, 0, 255)


@pytest.mark.parametrize("format", ["svg", "html", "pdf", "pptx"])
def test_document_matte_fallback_is_real_and_strict_prewrite_is_atomic(format, tmp_path):
    """Document exports freeze the correctly masked scene and disclose that route before writing."""
    if format in {"pdf", "pptx"}:
        pytest.importorskip("reportlab" if format == "pdf" else "pptx")
    # Given: a hidden matte source and its red target
    canvas = Canvas(100, 100).shape("rectangle", (0, 0), 50, 100, color="#FFFFFF", id="source")
    canvas.shape(
        "rectangle", (0, 0), 100, 100, color="#FF0000", id="target", mask=TrackMatte(layer="source")
    )
    destination = tmp_path / f"scene.{format}"
    # When: writing the actual document then asking for strict native output
    result = canvas.export(destination)
    original = destination.read_bytes()
    with pytest.raises(RenderingError):
        canvas.export(destination, policy=ExportPolicy(unsupported_motion="error"))
    # Then: every frozen layer is reported and strict refusal preserves the existing file
    assert result.fallback_diagnostics and all(
        "authored-static" in item.reason for item in result.fallback_diagnostics
    )
    assert {item.layer_id for item in result.capability_report} == {"source", "target"}
    assert destination.read_bytes() == original
    if format in {"svg", "html"}:
        image = embedded_png(original.decode(), format)
        assert image.getpixel((10, 10)) == (255, 0, 0, 255)
        assert image.getpixel((80, 10)) == (0, 0, 0, 0)


def test_mattes_reach_static_png_and_canonical_timeline_capture(tmp_path):
    """Static PNG and timeline captures consume the same hidden-source matte composition."""
    # Given: a translucent target masked by a moving white source
    canvas = Canvas(40, 20).shape(
        "rectangle",
        (0, 0),
        10,
        20,
        color="#FFFFFF",
        id="source",
        animation=AnimationSpec(
            timing=TimingSpec(duration=1),
            easing="linear",
            tracks=[
                PositionTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value=(0, 0)),
                        KeyframeSpec(time=1, value=(20, 0)),
                    ]
                )
            ],
        ),
    )
    canvas.shape("rectangle", (0, 0), 40, 20, color="#FF0000", mask=TrackMatte(layer="source"))
    # When: exporting a still and capturing the same scene's scheduled timeline
    destination = tmp_path / "matte.png"
    canvas.export(destination)
    still = Image.open(destination).convert("RGBA")
    middle = canvas.sample(time=0.5).frames[0].to_image()
    # Then: the still uses authored geometry and the timeline observes the moved matte on black
    assert still.getpixel((5, 5)) == (255, 0, 0, 255)
    assert still.getpixel((15, 5)) == (0, 0, 0, 0)
    assert middle.getpixel((15, 5)) == (255, 0, 0, 255)
    assert middle.getpixel((5, 5)) == (0, 0, 0, 255)
    assert any(row.feature == "track_matte" for row in canvas.inspect_motion().capabilities)


def test_deep_matte_chain_resolves_without_recursive_rendering():
    """A chain longer than Python's recursion limit resolves to the final target's RGBA pixels."""
    # Given: a complete scene of one-pixel mattes with forward references
    layers = [
        ShapeLayer(
            type="shape",
            shape="rectangle",
            position=(0, 0),
            width=2,
            height=2,
            color="#FFFFFF",
            id=f"source{index}",
            mask=TrackMatte(layer=f"source{index + 1}") if index < 1049 else None,
        )
        for index in range(1050)
    ]
    layers[0] = layers[0].model_copy(update={"color": "#FF0000"})
    canvas = Canvas(2, 2, layers=layers)
    # When: rendering the canonical dependency graph
    image = canvas.render_frame()
    # Then: all hidden dependencies contribute to the visible red target without recursion failure
    assert image.getpixel((0, 0)) == (255, 0, 0, 255)


def test_repeated_anonymous_target_occurrences_composite_independently():
    """Repeated references to one anonymous layer paint the same alpha as separate layer copies."""
    # Given: a translucent source and two authored occurrences of the same masked target
    source = ShapeLayer(
        type="shape",
        shape="rectangle",
        position=(0, 0),
        width=4,
        height=4,
        color="#FFFFFF80",
        id="source",
    )
    target = ShapeLayer(
        type="shape",
        shape="rectangle",
        position=(0, 0),
        width=4,
        height=4,
        color="#FF000080",
        mask=TrackMatte(layer="source"),
    )
    repeated = Canvas(4, 4, layers=[source, target, target])
    copied = Canvas(4, 4, layers=[source, target, target.model_copy()])
    # When: sampling the actual two-occurrence scenes
    actual, expected = repeated.render_frame(), copied.render_frame()
    # Then: source masking applies once to each occurrence before ordered alpha compositing
    assert actual.getpixel((1, 1)) == expected.getpixel((1, 1)) == (255, 0, 0, 112)


def test_consumed_matte_chain_surfaces_are_released(monkeypatch):
    """A forty-step matte chain releases full-canvas surfaces after their final consumer."""
    import weakref

    from quickthumb._export_video import _SlideAnimator

    # Given: a real forty-step chain and an observer of actual compositor surface lifetimes
    layers = [
        ShapeLayer(
            type="shape",
            shape="rectangle",
            position=(0, 0),
            width=16,
            height=16,
            color="#FF0000" if index == 0 else "#FFFFFF",
            id=f"source{index}",
            mask=TrackMatte(layer=f"source{index + 1}") if index < 39 else None,
        )
        for index in range(40)
    ]
    canvas = Canvas(16, 16, layers=layers)
    original = _SlideAnimator._composite_frame
    surfaces, peak = [], 0

    def observe(self, *args, **kwargs):
        nonlocal peak
        image = original(self, *args, **kwargs)
        surfaces.append(weakref.ref(image))
        peak = max(peak, sum(reference() is not None for reference in surfaces))
        return image

    monkeypatch.setattr(_SlideAnimator, "_composite_frame", observe)
    # When: rendering through the real canonical pipeline
    image = canvas.render_frame()
    # Then: dependency depth does not retain the already-consumed full-canvas chain
    assert image.getpixel((5, 5)) == (255, 0, 0, 255)
    assert len(surfaces) == 40 and peak <= 3


def test_static_group_matte_keeps_layout_and_unrelated_child_motion():
    """A laid-out static group masks a target without freezing another group's child animation."""
    from quickthumb import GroupLayer

    # Given: a white group source, a red target and an unrelated moving blue group child
    source = ShapeLayer(
        type="shape", shape="rectangle", position=(0, 0), width=10, height=10, color="#FFFFFF"
    )
    child = ShapeLayer(
        type="shape",
        shape="rectangle",
        position=(0, 0),
        width=10,
        height=10,
        color="#0000FF",
        animation=AnimationSpec(
            timing=TimingSpec(duration=1),
            easing="linear",
            tracks=[
                PositionTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value=(0, 0)),
                        KeyframeSpec(time=1, value=(20, 0)),
                    ]
                )
            ],
        ),
    )
    canvas = Canvas(60, 20).group([source], position=(0, 0), id="source")
    canvas.shape("rectangle", (0, 0), 60, 20, color="#FF0000", mask=TrackMatte(layer="source"))
    canvas.group([child], position=(0, 10))
    # When: sampling the full scene's intermediate frame
    image = canvas.render_frame(0.5)
    # Then: the static source's layout masks red while unrelated child motion remains live
    assert image.getpixel((5, 5)) == (255, 0, 0, 255)
    assert image.getpixel((15, 15)) == (0, 0, 255, 255)
    assert image.getpixel((5, 15)) == (0, 0, 0, 0)
    # Given: a moving child inside a proposed matte source
    moving_source = GroupLayer(type="group", children=[child], position=(0, 0), id="source")
    # When/Then: unsupported source-group content is refused before replacing the scene
    with pytest.raises(ValidationError, match="static descendants"):
        canvas.layers = [moving_source, canvas.layers[1]]
