"""An animated retained owner overrides structural motion across static boundaries."""

from io import BytesIO
from typing import cast

import pytest
from PIL import Image
from quickthumb import (
    AnimationSpec,
    Canvas,
    ColorTrack,
    ExportPolicy,
    Fade,
    GroupLayer,
    OpacityTrack,
    PositionKeyframeSpec,
    PositionTrack,
    RotationTrack,
    ScaleXTrack,
    ScaleYTrack,
    ShapeLayer,
    TextLayer,
    TimingSpec,
)
from quickthumb._export_html import HtmlExporter
from quickthumb._export_video import _SlideAnimator, animation_timeline
from quickthumb.errors import RenderingError
from quickthumb.motion import _has_transform_extensions

from tests.test_parent_composition import linked
from tests.test_parent_counters import motion, track
from tests.test_parent_diagnostics import setup
from tests.test_parent_documents import embedded_png
from tests.test_parent_nested_composition import nested_scene


def override_scene(kind="affine", *, invert=True):
    canvas = linked(nested_scene(invert=invert))
    owner = cast(GroupLayer, canvas.layers[-1])
    owner.animation = {
        "fade": AnimationSpec.fade(duration=1),
        "legacy": Fade(duration=1),
        "opacity": motion(track(OpacityTrack, 0.2, 0.9)),
        "rotation": motion(track(RotationTrack, -12, 20)),
        "empty": [],
        "affine": motion(
            track(RotationTrack, -12, 20),
            track(ScaleXTrack, 0.8, 1.2),
            track(OpacityTrack, 0.4, 0.9),
            track(ColorTrack, "#BB4422", "#2255CC"),
        ),
    }[kind]
    if kind == "affine":
        root = canvas.layers[0]
        root.position = (300, 12)
        root.animation = motion(
            track(RotationTrack, -5, 20),
            track(ScaleXTrack, -1, -1.2),
            track(ScaleYTrack, 1, 0.7),
        )
    middle = cast(GroupLayer, owner.children[0])
    inner = cast(GroupLayer, middle.children[1])
    wrapper = cast(GroupLayer, inner.children[0])
    text = cast(TextLayer, wrapper.children[0])
    suppressed = AnimationSpec.timeline(
        PositionTrack(
            keyframes=[
                PositionKeyframeSpec(time=0, value=(100, 50), in_tangent=(10, 0)),
                PositionKeyframeSpec(time=80, value=(-100, -50), out_tangent=(10, 0)),
            ]
        ),
        track(ColorTrack, "#00FF00", "#FF00FF"),
        timing=TimingSpec(duration=80, delay=40),
    )
    # Leave the composed inner group unanimated: the old export guard recurses
    # into it even when the top-level owner overrides the entire source.
    for child in (cast(ShapeLayer, middle.children[0]), text):
        child.animation = [suppressed, AnimationSpec.fade(duration=60, delay=30)]
    for group in (middle, wrapper):
        group.animation = AnimationSpec.fade(duration=80, delay=40)
    return canvas


def stripped_reference(canvas):
    reference = Canvas.from_json(canvas.to_json())

    def strip_descendants(layer):
        for child in getattr(layer, "children", ()):
            child.animation = None
            strip_descendants(child)

    # Retain the top-level owner, ancestor motion, layout and every boundary.
    strip_descendants(reference.layers[-1])
    return reference


@pytest.mark.parametrize("quality", ["standard", "high"])
@pytest.mark.parametrize("kind", ["fade", "legacy", "opacity", "rotation", "affine", "empty"])
def test_retained_owner_matches_independently_stripped_source_across_seeks(kind, quality):
    canvas = override_scene(kind, invert=quality == "high")
    reference = stripped_reference(canvas)
    before = canvas.to_json()
    if kind != "affine":
        assert not _has_transform_extensions(canvas.layers[-1])
    assert canvas._render_to_image().tobytes() == reference._render_to_image().tobytes()
    actual = _SlideAnimator(canvas, {}, quality=quality)
    expected = _SlideAnimator(reference, {}, quality=quality)
    node = actual._units[-1].parent_node
    reference_node = expected._units[-1].parent_node
    assert node.image.tobytes() == reference_node.image.tobytes()
    assert actual.duration == expected.duration == (0 if kind == "empty" else 1)
    assert actual.segments(0, 2) == expected.segments(0, 2)
    frames = []
    for time in (0.8, 0, 0.3, 1, 0.8):
        frame = actual.frame_at(time).tobytes()
        assert frame == expected.frame_at(time).tobytes()
        frames.append(frame)
    assert len(set(frames)) >= (1 if kind == "empty" else 3)
    if kind == "affine":
        matrix = node.plan.sample(0.3)[id(node)][0]
        assert matrix[0] * matrix[4] - matrix[1] * matrix[3] < 0
        assert abs(matrix[0] * matrix[1] + matrix[3] * matrix[4]) > 0.01
    assert canvas.to_json() == before


def test_authored_observations_and_override_diagnostics_match_stripped_reference():
    canvas = override_scene("rotation")
    reference = stripped_reference(canvas)
    before = canvas.to_json()
    assert canvas.inspect() == reference.inspect()
    assert canvas.diagnose() == reference.diagnose()
    assert not any(item.code == "motion-path-unused-handle" for item in canvas.diagnose().findings)
    sources, measured = setup(canvas)

    def visit(item):
        for child in item.children:
            assert sources.overridden(child)
            assert child.metadata["effective_animation"]
            visit(child)

    visit(measured[-1])
    assert canvas.to_json() == before


def test_suppressed_long_timing_does_not_extend_actual_export_windows():
    canvas = override_scene("opacity")
    reference = stripped_reference(canvas)
    before = canvas.to_json()
    assert animation_timeline([canvas], [None], 0.25) == ([0.0], 1.25)
    assert canvas.to_gif(fps=4, hold=0) == reference.to_gif(fps=4, hold=0)
    with Image.open(BytesIO(canvas.to_gif(fps=4, hold=0))) as gif:
        duration = 0
        for index in range(getattr(gif, "n_frames", 1)):
            gif.seek(index)
            duration += gif.info.get("duration", 0)
        assert duration == 1000
    # Inspection is authored-local, including suppressed specs; it is not an
    # effective renderer schedule. Keep that existing distinction explicit.
    assert canvas.inspect_motion(target="video", max_samples=2).duration > 100
    assert reference.inspect_motion(target="video", max_samples=2).duration == 1
    assert canvas.to_json() == before


@pytest.mark.parametrize("kind", ["html", "svg", "pdf", "pptx"])
def test_overridden_nested_specs_keep_authored_static_document_fallback(tmp_path, kind):
    canvas = override_scene("rotation")
    canvas.layers = [
        *Canvas(canvas.width, canvas.height).background(color="#FFFFFF").layers,
        *canvas.layers,
    ]
    before = canvas.to_json()
    expected = canvas._render_to_image()
    assert expected.tobytes() != canvas.render_frame(0).tobytes()
    payload = getattr(canvas, "to_" + kind)()
    if kind == "pdf":
        import pypdfium2

        with pypdfium2.PdfDocument(payload) as document:
            page = document[0]
            bitmap = page.render(scale=1)
            assert bitmap.to_pil().convert("RGB").tobytes() == expected.convert("RGB").tobytes()
            bitmap.close()
            page.close()
    else:
        actual = embedded_png(payload, kind)
        assert (actual.size, actual.tobytes()) == (expected.size, expected.tobytes())
    if kind == "html":
        assert not HtmlExporter(canvas).render_stage().timeline
        assert all(item.fallback == "static" for item in canvas.validate_export("html"))
    path = tmp_path / ("override." + kind)
    result = canvas.export(path)
    assert next(item for item in result.capability_report if item.feature == "parent").fallback == (
        "static"
    )
    for method in (canvas.render, canvas.export):
        path.write_bytes(b"existing")
        with pytest.raises(RenderingError, match="authored-static"):
            method(str(path), policy=ExportPolicy(unsupported_motion="error"))
        assert path.read_bytes() == b"existing"
    assert canvas.to_json() == before


@pytest.mark.parametrize(
    "policy",
    [
        ExportPolicy(reduced_motion=True),
        ExportPolicy(unsupported_motion="static"),
        ExportPolicy(unsupported_motion="rasterize"),
    ],
)
def test_overridden_nested_html_static_policies_preserve_the_whole_scene(policy):
    canvas = override_scene("opacity")
    assert embedded_png(canvas.to_html(policy=policy), "html").tobytes() == (
        canvas._render_to_image().tobytes()
    )


@pytest.mark.parametrize("unrelated_parent", [False, True])
def test_old_composed_descendant_export_guard_remains_for_unretained_groups(unrelated_parent):
    canvas = override_scene("rotation")
    owner = cast(GroupLayer, canvas.layers[-1])
    owner.parent = None
    if unrelated_parent:
        canvas.shape("rectangle", (280, 200), 10, 10, "#00FF00", parent="root")
    else:
        canvas.layers = [owner]
    with pytest.raises(RenderingError, match="cannot animate descendants"):
        _SlideAnimator(canvas, {})
