"""Composed group stagger preserves partial export and unsupported-source guards."""

from io import BytesIO
from typing import Any, cast

import pytest
from PIL import Image
from quickthumb import (
    AnimatedTextValue,
    AnimationSpec,
    BackdropBlur,
    ColorTrack,
    Deck,
    ExportPolicy,
    GifOptions,
    GroupLayer,
    LayerClip,
    LayerMask,
    RotationTrack,
    ShapeLayer,
    TextLayer,
)
from quickthumb._export_video import _SlideAnimator
from quickthumb._parent_render import ParentNode
from quickthumb.errors import RenderingError, ValidationError

from tests.test_parent_group_stagger import group_scene, nested_scene
from tests.test_parent_stagger import FONT, motion, track


@pytest.mark.parametrize("scene", [group_scene, nested_scene])
def test_composed_target_clocks_continue_in_actual_gif_after_parent_settles(scene):
    canvas = scene()
    cast(Any, canvas.layers[0]).animation = AnimationSpec.rise(distance=0, duration=0.1)
    animator = _SlideAnimator(canvas, {})
    assert len(animator._units[-1].target_images) == 3
    assert animator.duration == pytest.approx(1.3)
    segments = animator.segments(0.1, 1.7)
    assert segments[0][0] == 0.1 and segments[-2][1] == 1.3
    assert all(active for _, _, active in segments[:-1])
    assert segments[-1] == (1.3, 1.7, False)
    with Image.open(BytesIO(canvas.to_gif(fps=10, hold=0.2))) as gif:
        instant, later, durations = 0, [], []
        for index in range(getattr(gif, "n_frames", 1)):
            gif.seek(index)
            duration = gif.info["duration"] / 1000
            durations.append(duration)
            if 0.8 <= instant < 1.3:
                later.append(gif.convert("RGBA").tobytes())
            instant += duration
    assert len(set(later)) >= 4
    assert sum(durations) == pytest.approx(1.5)


@pytest.mark.parametrize("quality", ["standard", "high"])
@pytest.mark.parametrize("scene", [group_scene, nested_scene])
def test_composed_color_target_gifs_match_between_serial_and_spawn(tmp_path, quality, scene):
    canvas = scene(
        animation=motion(
            track(ColorTrack, "#FF0000", "#0000FF"), track(RotationTrack, -12, 12), stagger=0.4
        )
    )
    paths = [tmp_path / "serial.gif", tmp_path / "spawn.gif"]
    for workers, path in zip((1, 2), paths, strict=True):
        canvas.render(str(path), animation=GifOptions(fps=5, quality=quality, workers=workers))
    assert paths[0].read_bytes() == paths[1].read_bytes()
    with Image.open(paths[0]) as gif:
        assert getattr(gif, "n_frames", 1) >= 5


@pytest.mark.parametrize("boundary", ["descendant_clip", "nested_mask"])
def test_descendant_boundaries_accept_root_stagger_without_changing_partial_policy(boundary):
    canvas = group_scene()
    group = cast(GroupLayer, canvas.layers[-1])
    if boundary == "descendant_clip":
        cast(Any, group.children[0]).clip = LayerClip(position=(0, 0), width=20, height=30)
    else:
        group.children[0] = GroupLayer(
            type="group",
            children=[group.children[0]],
            mask=LayerMask(position=(0, 0), width=30, height=30, opacity=0.4),
        )
    animator = _SlideAnimator(canvas, {})
    assert len(animator._units[-1].target_images) == 3
    assert animator.frame_at(0.1).tobytes() != animator.frame_at(0.9).tobytes()
    report = canvas.validate_export("video")
    assert next(item for item in report if item.feature == "parent").support == "full"
    assert next(item for item in report if item.feature == "stagger").support == "fallback"


def deepest_group(group):
    while children := [child for child in group.children if isinstance(child, GroupLayer)]:
        group = children[-1]
    return group


@pytest.mark.parametrize(
    "kind",
    [
        "direct_counter",
        "deep_counter",
        "sibling_counter",
        "descendant_stagger",
        "structural_group_stagger",
        "deep_stagger",
        "deep_stagger_empty_owner",
        "stagger_parent",
        "zero_delay_parent",
        "one_child_parent",
        "zero_delay_one_child_parent",
        "independent",
        "ancestor_only",
        "inner_override",
        "backdrop",
        "nested_backdrop",
    ],
)
@pytest.mark.parametrize("format", ["png", "gif", "html", "svg", "pptx", "pdf"])
def test_unsupported_composed_group_combinations_fail_before_paint_or_output(
    tmp_path, monkeypatch, kind, format
):
    canvas = nested_scene()
    group = cast(GroupLayer, canvas.layers[-1])
    deep = deepest_group(group)
    assert deep is not group
    if kind.endswith("counter"):
        counter = TextLayer(
            type="text",
            content="12",
            font=FONT,
            size=18,
            value=AnimatedTextValue.model_validate({"from": 1, "to": 12, "duration": 1}),
        )
        if kind == "direct_counter":
            group.children[0] = counter
        elif kind == "deep_counter":
            deep.children.append(counter)
            deep.animation = AnimationSpec.fade(duration=1)
        else:
            group.children.append(counter)
        expected = "require static content"
    elif "stagger" in kind and kind != "stagger_parent":
        target = (
            group.children[0]
            if kind == "descendant_stagger"
            else group.children[1]
            if kind == "structural_group_stagger"
            else deep.children[0]
        )
        cast(Any, target).animation = [
            AnimationSpec.fade(duration=1),
            AnimationSpec.rise(
                stagger=0 if kind == "descendant_stagger" else 0.1,
                target="children" if isinstance(target, GroupLayer) else "lines",
            ),
        ]
        if kind == "deep_stagger_empty_owner":
            group.animation = []
        expected = "cannot use stagger on structural descendants"
    elif kind.endswith("parent"):
        if "zero_delay" in kind:
            cast(Any, group.animation).stagger.delay = 0
        if "one_child" in kind:
            group.children = [group.children[-1]]
        canvas.shape("rectangle", (0, 0), 5, 5, "#00FF00", parent="leaf")
        expected = "cannot be a parent"
    elif kind in {"independent", "ancestor_only", "inner_override"}:
        group.animation = None
        cast(Any, deep.children[0]).animation = AnimationSpec.fade(duration=1)
        if kind == "ancestor_only":
            cast(Any, canvas.layers[0]).animation = AnimationSpec.fade(duration=1)
        elif kind == "inner_override":
            deep.animation = AnimationSpec.fade(duration=1)
        expected = "cannot animate descendants"
    else:
        if kind == "nested_backdrop":
            deep.children.append(
                ShapeLayer(
                    type="shape",
                    shape="rectangle",
                    position=(0, 0),
                    width=20,
                    height=20,
                    color="#FFFFFF",
                    effects=[BackdropBlur(radius=3)],
                )
            )
        else:
            canvas.shape("rectangle", (0, 0), 100, 100, "#FFFFFF", effects=[BackdropBlur(radius=3)])
        expected = "backdrop"
    monkeypatch.setattr(
        ParentNode, "render_source", lambda *a, **k: pytest.fail("preflight painted")
    )
    monkeypatch.setattr(canvas, "_render_layer", lambda *a, **k: pytest.fail("preflight painted"))
    monkeypatch.setattr(
        canvas._groups, "render_group_layer", lambda *a, **k: pytest.fail("preflight painted")
    )
    for observe in (canvas.inspect, canvas.diagnose, lambda: canvas.render_frame(0.5)):
        with pytest.raises(RenderingError, match=expected):
            observe()
    for target in ("raster", "video", "html", "pptx"):
        parent = next(item for item in canvas.validate_export(target) if item.feature == "parent")
        assert parent.support == "unsupported" and expected in parent.message
    destination = tmp_path / ("existing." + format)
    for exporter in (canvas, Deck(canvas.width, canvas.height).slide(canvas)):
        destination.write_bytes(b"existing")
        # Strict document policy can report the animated null ancestor first;
        # the capability row and observations above still prove the source guard.
        strict_expected = "opacity motion|" + expected if kind == "ancestor_only" else expected
        with pytest.raises(RenderingError, match=strict_expected):
            exporter.export(destination, policy=ExportPolicy(unsupported_motion="error"))
        assert destination.read_bytes() == b"existing"
    with pytest.raises(RenderingError, match=expected):
        canvas.render(str(destination))
    assert destination.read_bytes() == b"existing"


@pytest.mark.parametrize("direction", ["from_descendant", "to_descendant"])
@pytest.mark.parametrize("depth", ["direct", "deep"])
@pytest.mark.parametrize("format", ["png", "gif", "html", "svg", "pptx", "pdf"])
def test_nested_stagger_keeps_explicit_structural_links_guarded(
    tmp_path, monkeypatch, direction, depth, format
):
    canvas = nested_scene()
    group = cast(GroupLayer, canvas.layers[-1])
    descendant = group.children[0] if depth == "direct" else deepest_group(group).children[0]
    descendant.id = "structural"
    if direction == "from_descendant":
        cast(Any, descendant).parent = "root"
    else:
        canvas.shape("rectangle", (0, 0), 5, 5, "#00FF00", parent="root")
        cast(Any, canvas.layers[-1]).parent = "structural"
    monkeypatch.setattr(
        ParentNode, "render_source", lambda *a, **k: pytest.fail("preflight painted")
    )
    monkeypatch.setattr(canvas, "_render_layer", lambda *a, **k: pytest.fail("preflight painted"))
    expected = "auto-layout group descendant"
    for observe in (canvas.inspect, canvas.diagnose, lambda: canvas.render_frame(0.5)):
        with pytest.raises(ValidationError, match=expected):
            observe()
    destination = tmp_path / ("existing." + format)
    for exporter in (canvas, Deck(canvas.width, canvas.height).slide(canvas)):
        destination.write_bytes(b"existing")
        with pytest.raises(ValidationError, match=expected):
            exporter.export(destination, policy=ExportPolicy(unsupported_motion="error"))
        assert destination.read_bytes() == b"existing"
    with pytest.raises(ValidationError, match=expected):
        canvas.render(str(destination))
    assert destination.read_bytes() == b"existing"
