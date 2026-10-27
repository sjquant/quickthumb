"""Shape masks follow the owner's canonical timeline before world transforms."""

import json

import jsonschema
import pytest
from quickthumb import (
    AnimationSpec,
    BackdropBlur,
    Canvas,
    ColorTrack,
    CubicBezierEasing,
    ExportPolicy,
    KeyframeSpec,
    LayerClip,
    LayerMask,
    MaskFeatherTrack,
    MaskPositionTrack,
    MaskSizeTrack,
    RotationTrack,
    ShapeLayer,
    TimingSpec,
    TrackMatte,
    ValidationError,
    canvas_json_schema,
)
from quickthumb.errors import RenderingError

from tests.test_parent_documents import embedded_png


def scene(*tracks, mask=None, timing=None, parent=False):
    canvas = Canvas(100, 60)
    if parent:
        canvas.null((10, 5), id="root")
    canvas.shape(
        "rectangle",
        (0, 0),
        80,
        40,
        color="#FF0000",
        mask=mask or LayerMask(position=(5, 0), width=20, height=40),
        animation=AnimationSpec.timeline(
            *tracks, timing=timing or TimingSpec(duration=1), easing="linear"
        ),
        parent="root" if parent else None,
    )
    return canvas


def test_mask_position_uses_owner_delay_hold_and_keyframe_easing():
    """Mask offsets honor the owner's delay, hold boundary and outgoing custom easing."""
    # Given: a held mask followed by a custom-eased move on a delayed owner clock
    track = MaskPositionTrack(
        keyframes=[
            KeyframeSpec(time=0, value=(0, 0), hold=True),
            KeyframeSpec(time=0.5, value=(20, 0), easing=CubicBezierEasing(points=(0, 0, 1, 1))),
            KeyframeSpec(time=1, value=(40, 0)),
        ]
    )
    canvas = scene(track, timing=TimingSpec(duration=1, delay=0.25))
    # When: seeking either side of the hold boundary and halfway through the eased segment
    before, boundary, middle = (canvas.render_frame(t) for t in (0.74, 0.75, 1))
    # Then: position is an offset from the authored five-pixel mask origin, not owner translation
    assert (
        before.getpixel((10, 10))
        == boundary.getpixel((30, 10))
        == middle.getpixel((40, 10))
        == (255, 0, 0, 255)
    )
    assert before.getpixel((30, 10)) == boundary.getpixel((10, 10)) == (0, 0, 0, 0)
    capture = canvas.sample(time=1).frames[0].to_image()
    assert capture.getpixel((40, 10)) == (255, 0, 0, 255)


@pytest.mark.parametrize("parent", [False, True])
def test_mask_geometry_precedes_owner_world_transforms_without_moving_pivot(parent):
    """Mask geometry reveals a fixed owner body before rotation and parent translation."""
    # Given: a mask revealing the owner's left half, with rotation about the full body center
    canvas = scene(
        MaskPositionTrack(
            keyframes=[KeyframeSpec(time=0, value=(0, 0)), KeyframeSpec(time=1, value=(20, 0))]
        ),
        MaskSizeTrack(
            keyframes=[KeyframeSpec(time=0, value=(20, 40)), KeyframeSpec(time=1, value=(40, 40))]
        ),
        RotationTrack(keyframes=[KeyframeSpec(time=0, value=180), KeyframeSpec(time=1, value=180)]),
        mask=LayerMask(position=(0, 0), width=20, height=40),
        parent=parent,
    )
    # When: sampling the authored and moving mask geometry
    start, middle = canvas.render_frame(0), canvas.render_frame(0.5)
    dx, dy = (10, 5) if parent else (0, 0)
    # Then: the fixed eighty-pixel body pivot rotates initial left paint onto its right side
    assert start.getpixel((70 + dx, 10 + dy)) == (255, 0, 0, 255)
    assert start.getpixel((10 + dx, 10 + dy)) == (0, 0, 0, 0)
    assert middle.getpixel((50 + dx, 10 + dy)) == (255, 0, 0, 255)
    capture = canvas.sample(time=0.5).frames[0].to_image()
    assert capture.getpixel((50 + dx, 10 + dy)) == (255, 0, 0, 255)


def test_feather_animation_has_soft_edges_without_crop_or_clip_seams():
    """Animated feather spreads beyond the mask edge while a separate clip remains sharp."""
    # Given: a finite mask beside a clip edge and feather increasing on the owner timeline
    canvas = scene(
        MaskFeatherTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=4)]),
        mask=LayerMask(position=(20, 0), width=20, height=40),
    )
    layer = canvas.layers[0]
    canvas.layers = [
        layer.model_copy(update={"clip": LayerClip(position=(0, 0), width=38, height=40)})
    ]
    # When: rendering sharp and fully feathered masks
    sharp, soft = canvas.render_frame(0), canvas.render_frame(1)
    # Then: feather reveals soft pixels outside the mask but never outside the clip
    assert sharp.getpixel((18, 20)) == (0, 0, 0, 0)
    assert 0 < soft.getpixel((18, 20))[3] < 128
    assert soft.getpixel((30, 20))[3] > 220
    assert soft.getpixel((37, 20))[3] > 100
    assert soft.getpixel((38, 20)) == (0, 0, 0, 0)


@pytest.mark.parametrize("kind", ["svg", "html", "pdf", "pptx"])
def test_animated_mask_documents_report_authored_static_fallback(kind, tmp_path):
    """Document output freezes authored mask geometry and strict policy refuses before writing."""
    if kind in {"pdf", "pptx"}:
        pytest.importorskip("reportlab" if kind == "pdf" else "pptx")
    # Given: a mask moving twenty pixels across a red source
    canvas = scene(
        MaskPositionTrack(
            keyframes=[KeyframeSpec(time=0, value=(0, 0)), KeyframeSpec(time=1, value=(20, 0))]
        )
    )
    if kind == "pptx":
        canvas.height = 100
    destination = tmp_path / f"mask.{kind}"
    # When: exporting normally then requesting strict native rendering
    result = canvas.export(destination)
    original = destination.read_bytes()
    with pytest.raises(RenderingError):
        canvas.export(destination, policy=ExportPolicy(unsupported_motion="error"))
    # Then: diagnostics identify the animated mask fallback and preserve the previous output
    assert result.capability_report[0].feature == "mask_animation"
    assert "authored-static" in result.fallback_diagnostics[0].reason
    assert destination.read_bytes() == original
    if kind in {"svg", "html"}:
        image = embedded_png(original.decode(), kind)
        assert image.getpixel((10, 10)) == (255, 0, 0, 255)
        assert image.getpixel((30, 10)) == (0, 0, 0, 0)


def test_mask_tracks_roundtrip_schema_and_are_visible_to_inspection():
    """Mask tracks and static feather serialize through schema and appear in motion inspection."""
    # Given: a mask with authored feather and all three canonical geometry tracks
    canvas = scene(
        MaskPositionTrack(
            keyframes=[KeyframeSpec(time=0, value=(0, 0)), KeyframeSpec(time=1, value=(10, 0))]
        ),
        MaskSizeTrack(
            keyframes=[KeyframeSpec(time=0, value=(20, 40)), KeyframeSpec(time=1, value=(30, 40))]
        ),
        MaskFeatherTrack(keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=1, value=2)]),
        mask=LayerMask(position=(5, 0), width=20, height=40, feather=1),
    )
    # When: validating JSON and rebuilding the actual scene
    jsonschema.validate(json.loads(canvas.to_json()), canvas_json_schema())
    restored = Canvas.from_json(canvas.to_json())
    # Then: sampled geometry roundtrips and capabilities expose the three implemented tracks
    assert restored.render_frame(0.5).tobytes() == canvas.render_frame(0.5).tobytes()
    features = {row.feature for row in restored.inspect_motion().capabilities}
    assert {"mask_position", "mask_size", "mask_feather"} <= features


@pytest.mark.parametrize(
    "track,value",
    [(MaskSizeTrack, (0, 10)), (MaskSizeTrack, (float("inf"), 10)), (MaskFeatherTrack, -1)],
)
def test_invalid_mask_geometry_keyframes_fail_at_admission(track, value):
    """Invalid mask size or feather values are rejected before any scene can be rendered."""
    # Given/When/Then: invalid public keyframe values cannot create an accepted geometry track
    with pytest.raises(ValidationError):
        track(keyframes=[KeyframeSpec(time=0, value=value)])


def test_mask_tracks_require_shape_masks_and_enforce_surface_budget():
    """Invalid mask bindings and oversized feather fail before rendering or allocation."""
    # Given: an owner mask track and incompatible mask bindings
    animation = AnimationSpec.timeline(MaskFeatherTrack(keyframes=[KeyframeSpec(time=0, value=1)]))
    # When/Then: absent or layer-reference masks cannot accept shape geometry tracks
    for mask in (None, TrackMatte(layer="source")):
        with pytest.raises(ValidationError, match="LayerMask"):
            Canvas(20, 20).shape(
                "rectangle", (0, 0), 20, 20, color="#FF0000", mask=mask, animation=animation
            )
    # Given: valid finite keyframes beyond the bounded temporary surface budget
    canvas = scene(MaskFeatherTrack(keyframes=[KeyframeSpec(time=0, value=1e308)]))
    # When/Then: rendering reports the allocation bound instead of overflowing or allocating
    with pytest.raises(RenderingError) as error:
        canvas.render_frame(0)
    assert error.value.code == "mask_surface_limit"


def test_mask_tracks_combine_with_color_on_an_initially_transparent_body():
    """Color and mask tracks share a stable body even when the authored fill is transparent."""
    # Given: a transparent body whose color becomes green while its mask moves
    canvas = scene(
        MaskPositionTrack(
            keyframes=[KeyframeSpec(time=0, value=(0, 0)), KeyframeSpec(time=1, value=(20, 0))]
        ),
        ColorTrack(
            keyframes=[KeyframeSpec(time=0, value="#00FF00"), KeyframeSpec(time=1, value="#00FF00")]
        ),
    )
    layer = canvas.layers[0]
    canvas.layers = [layer.model_copy(update={"color": "#FF000000"})]
    # When: rendering through direct raster and the complete scheduled sampler
    direct = canvas.render_frame(0.5)
    captured = canvas.sample(time=0.5).frames[0].to_image()
    # Then: both tracks contribute actual pixels instead of losing an empty prepared source
    assert direct.getpixel((30, 10)) == captured.getpixel((30, 10)) == (0, 255, 0, 255)


@pytest.mark.parametrize("width,visible", [(0.1, False), (0.24, False), (0.25, True)])
def test_positive_subpixel_mask_sizes_rasterize_without_an_api_minimum(width, visible):
    """Positive widths below one supersample accept their track and safely rasterize as empty."""
    # Given: a valid positive size track, including widths below the four-times raster grid
    canvas = scene(MaskSizeTrack(keyframes=[KeyframeSpec(time=0, value=(width, 10))]))
    # When: rendering through the direct and complete scheduled raster paths
    direct = canvas.render_frame(0)
    captured = canvas.sample(time=0).frames[0].to_image()
    # Then: sub-grid geometry stays empty while a one-supersample-wide mask retains coverage
    assert (direct.getchannel("A").getextrema()[1] > 0) == visible
    assert (captured.getpixel((5, 5))[:3] != (0, 0, 0)) == visible


@pytest.mark.parametrize("format", ["png", "gif", "html"])
def test_animated_mask_backdrop_blur_is_refused_before_overwrite(format, tmp_path):
    """Animated owner masks refuse backdrop blur instead of applying backdrop alpha twice."""
    # Given: the intended static combination preserves the blue backdrop under translucent red
    still = (
        Canvas(40, 20)
        .background(color="#0000FF")
        .shape(
            "rectangle",
            (0, 0),
            40,
            20,
            color="#FF000080",
            effects=[BackdropBlur(radius=3)],
            mask=LayerMask(position=(10, 0), width=20, height=20),
        )
    )
    assert still.render_frame().getpixel((15, 5)) == (128, 0, 127, 255)
    canvas = (
        Canvas(40, 20)
        .background(color="#0000FF")
        .shape(
            "rectangle",
            (0, 0),
            40,
            20,
            color="#FF000080",
            mask=LayerMask(position=(0, 0), width=20, height=20),
            animation=AnimationSpec.timeline(
                MaskPositionTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value=(0, 0)),
                        KeyframeSpec(time=1, value=(20, 0)),
                    ]
                ),
                timing=TimingSpec(duration=1),
            ),
        )
    )
    # Mutating the public effect list also requires preflight validation, beyond model admission.
    layer = canvas.layers[-1]
    assert isinstance(layer, ShapeLayer)
    layer.effects.append(BackdropBlur(radius=3))
    destination = tmp_path / f"existing.{format}"
    destination.write_bytes(b"preserve existing output")
    # When: requesting actual output from the unsupported animated combination
    with pytest.raises(ValidationError) as error:
        canvas.export(destination)
    # Then: a precise refusal preserves the destination before any backend writes
    assert error.value.code == "unsupported_mask_backdrop"
    assert destination.read_bytes() == b"preserve existing output"
