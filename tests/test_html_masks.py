"""Bounded native HTML masks share canonical geometry, identity and export admission."""

import pytest
from quickthumb import (
    AnimationSpec,
    Canvas,
    ExportPolicy,
    KeyframeSpec,
    LayerMask,
    MaskPositionTrack,
    MaskSizeTrack,
    PositionTrack,
    ShapeLayer,
    Stroke,
    TimingSpec,
    TrackMatte,
)
from quickthumb.errors import RenderingError

from tests.test_export_html import timelines


def scene(shape="rectangle"):
    points = [(0, 0), (1, 0.25), (0.75, 1), (0.1, 0.8)] if shape == "polygon" else None
    return Canvas(160, 100).shape(
        "rectangle",
        (20, 20),
        120,
        60,
        color="#42CEB7",
        id="owner",
        motion_key="shared.owner",
        mask=LayerMask(shape=shape, position=(30, 30), width=40, height=40, points=points),
        animation=AnimationSpec.timeline(
            MaskPositionTrack(
                keyframes=[
                    KeyframeSpec(time=0, value=(0, 0)),
                    KeyframeSpec(time=0.25, value=(20, 0)),
                    KeyframeSpec(time=1, value=(40, 0)),
                ]
            ),
            MaskSizeTrack(
                keyframes=[
                    KeyframeSpec(time=0, value=(40, 40)),
                    KeyframeSpec(time=0.5, value=(60, 40)),
                    KeyframeSpec(time=1, value=(80, 40)),
                ]
            ),
            timing=TimingSpec(duration=1),
            easing="linear",
        ),
    )


@pytest.mark.parametrize(
    "shape,clip",
    [
        ("rectangle", "inset("),
        ("ellipse", "ellipse("),
        ("pill", " round calc("),
        ("polygon", "polygon("),
    ],
)
def test_html_masks_are_native_and_preserve_independent_track_knots(shape, clip, tmp_path):
    """Hard masks retain native CSS geometry, owner identity and independent track intervals."""
    # Given: one mask with different position and size keyframe times
    canvas = scene(shape)
    destination = tmp_path / "native.html"
    # When: requesting strict native HTML through the public export receipt
    result = canvas.export(destination, policy=ExportPolicy(unsupported_motion="error"))
    text = destination.read_text()
    timeline = timelines(text)[0]
    # Then: real vector CSS, source identity and the existing timeline retain independent knots
    assert "data:image/png" not in text and clip in text
    assert 'data-qt-source-id="owner"' in text and 'data-qt-motion-key="shared.owner"' in text
    assert len(timeline) == 1 and timeline[0]["a"] == "transform"
    assert "25%{--qt-mask-x:20;--qt-mask-y:0}" in text
    assert "50%{--qt-mask-width:60;--qt-mask-height:40}" in text
    assert timeline[0]["initial"]["--qt-mask-width"] == "40"
    assert timeline[0]["final"]["--qt-mask-width"] == "80"
    assert not result.fallback_diagnostics
    assert all(row.support == "native" for row in result.capability_report)
    inspection = canvas.inspect_motion(target="html")
    assert all(row.support == "native" for row in inspection.diagnostics)
    restored = Canvas.from_json(canvas.to_json())
    assert restored.to_html() == canvas.to_html()


@pytest.mark.parametrize(
    "source,reason",
    [
        ("feather", "hard opaque"),
        ("invert", "inversion"),
        ("opacity", "opaque"),
        ("effects", "effects"),
        ("parent", "parent links"),
        ("hold", "holds"),
        ("tiny", "sub-pixel"),
        ("authored_range", "geometry range"),
        ("effective_range", "geometry range"),
        ("composed_range", "geometry range"),
        ("authored_precision", "CSS coordinate precision"),
        ("composed_precision", "CSS coordinate precision"),
    ],
)
def test_unsupported_html_masks_freeze_truthfully_before_strict_refusal(source, reason, tmp_path):
    """Unsupported masks disclose their static fallback and fail strict export before writing."""
    # Given: a valid canonical mask outside the bounded native HTML contract
    canvas = scene()
    layer = canvas.layers[0]
    assert isinstance(layer, ShapeLayer) and isinstance(layer.mask, LayerMask)
    if source == "feather":
        layer.mask.feather = 2
    elif source == "invert":
        layer.mask.invert = True
    elif source == "opacity":
        layer.mask.opacity = 0.5
    elif source == "effects":
        layer.effects.append(Stroke(width=2, color="#0000FF"))
    elif source == "parent":
        canvas.null(id="root")
        layer.parent = "root"
    elif source == "hold":
        layer.animation.tracks[0].keyframes[0].hold = True
    elif source == "authored_range":
        layer.mask.position = (2**28 + 1, 30)
    elif source == "effective_range":
        layer.animation = AnimationSpec.timeline(
            MaskSizeTrack(
                keyframes=[
                    KeyframeSpec(time=0, value=(40, 40)),
                    KeyframeSpec(time=1, value=(1e308, 40)),
                ]
            ),
            timing=TimingSpec(duration=1),
        )
        with pytest.raises(RenderingError) as error:
            canvas.render_frame(0.5)
        assert error.value.code == "mask_geometry_range"
    elif source in {"composed_range", "composed_precision"}:
        origin, delta = (2**28 - 80, 80) if source == "composed_range" else (1_100_000, 1_100_000)
        layer.mask.position = (origin, 30)
        layer.animation = AnimationSpec.timeline(
            MaskPositionTrack(
                keyframes=[
                    KeyframeSpec(time=0, value=(0, 0)),
                    KeyframeSpec(time=1, value=(delta, 0)),
                ]
            ),
            timing=TimingSpec(duration=1),
        )
    elif source == "authored_precision":
        layer.mask.position = (2_200_000, 30)
    else:
        layer.animation = AnimationSpec.timeline(
            MaskSizeTrack(keyframes=[KeyframeSpec(time=0, value=(0.1, 40))])
        )
    destination = tmp_path / "fallback.html"
    # When: writing the real fallback then asking for strict native HTML
    result = canvas.export(destination)
    original = destination.read_bytes()
    with pytest.raises(RenderingError):
        canvas.export(destination, policy=ExportPolicy(unsupported_motion="error"))
    # Then: diagnostics match actual static content and preserve the existing destination
    assert "data:image/png" in original.decode()
    assert reason in result.fallback_diagnostics[0].reason
    assert "authored-static" in result.fallback_diagnostics[0].reason
    assert not timelines(original.decode())[0]
    assert destination.read_bytes() == original


def test_static_and_animated_html_masks_keep_owner_specific_defaults():
    """Static and moving masks retain their own widths with shared CSS property registration."""
    # Given: one animated mask and a differently sized static mask in the same scene
    canvas = scene()
    canvas.shape(
        "ellipse",
        (0, 0),
        20,
        20,
        color="#FF0000",
        id="static",
        mask=LayerMask(position=(0, 0), width=8, height=12),
    )
    # When: generating the actual HTML stage
    text = canvas.to_html()
    # Then: registration occurs once and static geometry supplies its own nonzero inline defaults
    assert text.count("@property --qt-mask-width{") == 1
    assert "--qt-mask-width:8;--qt-mask-height:12" in text
    assert len(timelines(text)[0]) == 1 and "data:image/png" not in text


def test_path_layer_mattes_already_cover_curves_holes_motion_and_source_reuse():
    """A curved path with a hole moves as a reusable, hidden mask source."""
    # Given: an existing PathLayer ring reused as the alpha source of two colored targets
    canvas = Canvas(120, 60).path(
        "M10 30A20 20 0 1 1 50 30A20 20 0 1 1 10 30ZM20 30A10 10 0 1 1 40 30A10 10 0 1 1 20 30Z",
        (0, 0),
        120,
        60,
        "#FFFFFF",
        id="reveal",
        animation=AnimationSpec.timeline(
            PositionTrack(
                keyframes=[KeyframeSpec(time=0, value=(0, 0)), KeyframeSpec(time=1, value=(40, 0))]
            ),
            timing=TimingSpec(duration=1),
            easing="linear",
        ),
    )
    canvas.shape("rectangle", (0, 0), 120, 30, color="#FF0000", mask=TrackMatte(layer="reveal"))
    canvas.shape("rectangle", (0, 30), 120, 30, color="#0000FF", mask=TrackMatte(layer="reveal"))
    # When: round-tripping the real public scene and sampling its curved source motion
    canvas = Canvas.from_json(canvas.to_json())
    for time, x in [(0, 30), (0.5, 50), (1, 70)]:
        image = canvas.render_frame(time)
        # Then: both targets follow the path, holes stay empty, and white source paint never leaks
        assert image.getpixel((x, 15)) == (255, 0, 0, 255)
        assert image.getpixel((x, 30)) == (0, 0, 0, 0)
        assert image.getpixel((x, 45)) == (0, 0, 255, 255)
        assert (255, 255, 255, 255) not in image.get_flattened_data()
