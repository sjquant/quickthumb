"""Owner-attached SVG path masks share coverage and the existing mask clock."""

import json

import jsonschema
import pytest
from quickthumb import (
    AnimationSpec,
    Canvas,
    ExportPolicy,
    KeyframeSpec,
    LayerMask,
    MaskFeatherTrack,
    MaskPositionTrack,
    MaskSizeTrack,
    PositionTrack,
    RotationTrack,
    TimingSpec,
    ValidationError,
    canvas_json_schema,
)
from quickthumb.errors import RenderingError

from tests.test_parent_documents import embedded_png

RING = "M0 20 C0 -7 40 -7 40 20 C40 47 0 47 0 20 Z M10 10 H30 V30 H10 Z"


def path_mask(**kwargs):
    return LayerMask(shape="path", d=RING, position=(10, 10), width=40, height=40, **kwargs)


def scene(mask=None, *tracks, parent=False):
    canvas = Canvas(120, 80)
    if parent:
        canvas.null((10, 5), id="parent")
    canvas.shape(
        "rectangle",
        (0, 0),
        80,
        60,
        color="#FF0000",
        id="owner",
        parent="parent" if parent else None,
        mask=mask or path_mask(),
        animation=AnimationSpec.timeline(*tracks, timing=TimingSpec(duration=1), easing="linear")
        if tracks
        else None,
    )
    return canvas


def test_path_mask_curves_holes_viewport_and_json_roundtrip():
    """Curved even-odd masks preserve holes, clip their viewport and survive public JSON."""
    # Given: a curved ring extending beyond its authored viewport
    canvas = scene()
    # When: rendering both the authored scene and its schema-checked JSON roundtrip
    payload = json.loads(canvas.to_json())
    jsonschema.validate(payload, canvas_json_schema())
    original = canvas._render_to_image()
    restored = Canvas.from_json(canvas.to_json())._render_to_image()
    # Then: curve paint remains, its hole and clipped outside stay transparent
    assert restored.tobytes() == original.tobytes()
    assert original.getpixel((15, 30)) == (255, 0, 0, 255)
    assert original.getpixel((30, 30))[3] == original.getpixel((30, 7))[3] == 0
    assert canvas.inspect_motion().slides[0].layers[0].static_state["mask"]["d"] == RING


@pytest.mark.parametrize("parent", [False, True])
def test_path_mask_tracks_scale_authored_basis_before_owner_transforms(parent):
    """Size and position tracks retain the authored path basis before stable owner rotation."""
    # Given: an initially left-side path mask and a rotating, optionally parented owner
    canvas = scene(
        LayerMask(shape="path", d="M0 0H20V40H0Z", position=(0, 0), width=20, height=40),
        MaskPositionTrack(
            keyframes=[KeyframeSpec(time=0, value=(0, 0)), KeyframeSpec(time=1, value=(20, 0))]
        ),
        MaskSizeTrack(
            keyframes=[KeyframeSpec(time=0, value=(20, 40)), KeyframeSpec(time=1, value=(40, 40))]
        ),
        RotationTrack(keyframes=[KeyframeSpec(time=0, value=180), KeyframeSpec(time=1, value=180)]),
        parent=parent,
    )
    # When: the mask grows and moves on the owner's clock
    start, final = canvas.render_frame(0), canvas.render_frame(1)
    dx, dy = (10, 5) if parent else (0, 0)
    # Then: resized coverage reaches beyond the original twenty-unit path, in world space
    assert start.getpixel((70 + dx, 30 + dy))[3] == 255
    assert final.getpixel((30 + dx, 30 + dy))[3] == 255
    assert final.getpixel((70 + dx, 30 + dy))[3] == 0
    assert canvas.sample(time=1).frames[0].to_image().getpixel(
        (30 + dx, 30 + dy)
    ) == final.getpixel((30 + dx, 30 + dy))


def test_path_mask_moves_with_owner_and_uses_explicit_viewbox():
    """An owner-attached path travels with owner translation without a scene source layer."""
    # Given: a shifted SVG coordinate system fitted to a twenty-pixel mask
    canvas = scene(
        LayerMask(
            shape="path",
            d="M100 100H120V120H100Z",
            view_box=(100, 100, 20, 20),
            position=(10, 10),
            width=20,
            height=20,
        ),
        PositionTrack(
            keyframes=[KeyframeSpec(time=0, value=(0, 0)), KeyframeSpec(time=1, value=(30, 0))]
        ),
    )
    # When: the owner translates
    start, final = canvas.render_frame(0), canvas.render_frame(1)
    # Then: local coverage follows it, with no hidden source IDs or coordinate synchronization
    assert start.getpixel((15, 15))[3] == final.getpixel((45, 15))[3] == 255
    assert final.getpixel((15, 15))[3] == 0


def test_path_mask_feather_opacity_inversion_and_clipping():
    """Feathering is applied after viewport clipping and before mask inversion."""
    # Given: a path larger than its viewport with partial mask opacity
    mask = LayerMask(
        shape="path",
        d="M-100 -100H100V100H-100Z",
        position=(20, 20),
        width=20,
        height=20,
        opacity=0.5,
    )
    canvas = scene(
        mask,
        MaskFeatherTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=2)]),
    )
    # When: comparing a sharp edge, a feathered edge and inverted sampled geometry
    sharp, soft = canvas.render_frame(0), canvas.render_frame(1)
    inverted = scene(mask.model_copy(update={"feather": 2, "invert": True}))._render_to_image()
    rectangle = scene(
        LayerMask(position=(20, 20), width=20, height=20, opacity=0.5, feather=2)
    )._render_to_image()
    # Then: outside path geometry cannot leak into the viewport's blur, and alpha is complementary
    assert sharp.getpixel((30, 30))[3] == 128
    assert 0 < soft.getpixel((18, 30))[3] < 128
    assert soft.getpixel((30, 30))[3] + inverted.getpixel((30, 30))[3] == 255
    assert soft.tobytes() == rectangle.tobytes()
    # Given/When: the same oversized path's viewport crosses the canvas's negative origin
    clipped_path = scene(mask.model_copy(update={"position": (-5, -5), "feather": 2}))
    clipped_rectangle = scene(
        LayerMask(position=(-5, -5), width=20, height=20, opacity=0.5, feather=2)
    )
    # Then: the shared half-open viewport gives identical cropped feather coverage
    assert (
        clipped_path._render_to_image().tobytes() == clipped_rectangle._render_to_image().tobytes()
    )


@pytest.mark.parametrize("kind", ["html", "svg", "pptx", "pdf"])
def test_path_mask_documents_declare_fallback_and_reject_before_write(kind, tmp_path):
    """Document adapters expose path-mask rasterization and refuse strict native output prewrite."""
    # Given: an owner-attached path mask and a fresh destination
    canvas = scene()
    if kind == "pptx":
        canvas.height = 100
    destination = tmp_path / ("masked." + kind)
    # When: querying and then requesting strict document export
    report = canvas.validate_export(kind)
    assert any(d.feature == "path_mask" and d.fallback == "rasterize" for d in report)
    with pytest.raises(RenderingError, match="Path-shaped LayerMask"):
        canvas.export(destination, policy=ExportPolicy(unsupported_motion="error"))
    # Then: no output is written; supported embedded images retain actual path-mask pixels
    assert not destination.exists()
    if kind in {"html", "svg", "pptx"}:
        output = getattr(canvas, "to_" + kind)()
        assert (
            embedded_png(output, kind).tobytes()
            == canvas._render_to_image().crop((10, 10, 50, 50)).tobytes()
        )


@pytest.mark.parametrize(
    "updates",
    [
        {"d": None},
        {"d": "M0 0 K1 2"},
        {"view_box": (0, 0, 0, 20)},
        {"view_box": (float("inf"), 0, 20, 20)},
        {"points": [(0, 0), (1, 0), (1, 1)]},
        {"d": "M-1e308 0L1e308 0L0 1Z"},
    ],
)
def test_path_mask_rejects_invalid_or_unbounded_geometry(updates):
    """Invalid SVG geometry and incompatible polygon fields fail during public model admission."""
    # Given: path-mask arguments modified to violate a concrete geometry contract
    args = {"shape": "path", "d": RING, "position": (0, 0), "width": 40, "height": 40}
    args.update(updates)
    # When/Then: admission fails before any export or image allocation
    with pytest.raises((ValueError, RenderingError, ValidationError)):
        LayerMask.model_validate(args)


def test_nonpath_masks_reject_path_fields():
    """Primitive mask shapes cannot accept ignored SVG path controls."""
    # Given/When/Then: a path field on a rectangle has no interpretation
    with pytest.raises(ValidationError, match="only valid for path"):
        LayerMask(position=(0, 0), width=10, height=10, d="M0 0Z")


@pytest.mark.parametrize("width", [0.1, 0.24, 0.25])
def test_path_mask_accepts_subpixel_sampled_viewports(width):
    """Positive fractional size tracks remain valid even below a supersampling pixel."""
    # Given: a one-unit path resized below one device pixel
    canvas = scene(
        LayerMask(shape="path", d="M0 0H1V10H0Z", position=(10, 10), width=1, height=10),
        MaskSizeTrack(
            keyframes=[
                KeyframeSpec(time=0, value=(width, 10)),
                KeyframeSpec(time=1, value=(width, 10)),
            ]
        ),
    )
    # When: rendering canonical and prepared samples
    direct = canvas.render_frame(0.5)
    sampled = canvas.sample(time=0.5).frames[0].to_image()
    # Then: both paths complete with bounded geometry and no unrelated paint
    assert direct.getpixel((30, 30))[3] == 0
    assert sampled.size == direct.size
