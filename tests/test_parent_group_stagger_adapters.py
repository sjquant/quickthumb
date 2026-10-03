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
    TextLayer,
)
from quickthumb._export_video import _SlideAnimator
from quickthumb._parent_render import ParentNode
from quickthumb.errors import RenderingError

from tests.test_parent_group_stagger import group_scene
from tests.test_parent_stagger import FONT, motion, track


def test_composed_target_clocks_continue_in_actual_gif_after_parent_settles():
    canvas = group_scene()
    cast(Any, canvas.layers[0]).animation = AnimationSpec.rise(distance=0, duration=0.1)
    animator = _SlideAnimator(canvas, {})
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
def test_composed_color_target_gifs_match_between_serial_and_spawn(tmp_path, quality):
    canvas = group_scene(
        animation=motion(
            track(ColorTrack, "#FF0000", "#0000FF"), track(RotationTrack, -12, 12), stagger=0.4
        )
    )
    paths = [tmp_path / "serial.gif", tmp_path / "spawn.gif"]
    for workers, path in zip((1, 2), paths, strict=True):
        canvas.render(str(path), animation=GifOptions(fps=5, quality=quality, workers=workers))
    assert paths[0].read_bytes() == paths[1].read_bytes()


@pytest.mark.parametrize(
    "kind",
    [
        "counter",
        "descendant_clip",
        "nested_mask",
        "stagger_parent",
        "independent",
        "backdrop",
    ],
)
@pytest.mark.parametrize("format", ["png", "gif", "html", "svg", "pptx", "pdf"])
def test_unsupported_composed_group_combinations_fail_before_paint_or_output(
    tmp_path, monkeypatch, kind, format
):
    canvas = group_scene()
    group = cast(GroupLayer, canvas.layers[-1])
    expected = "descendant boundaries cannot use stagger"
    if kind == "counter":
        group.children[0] = TextLayer(
            type="text",
            content="12",
            font=FONT,
            size=18,
            value=AnimatedTextValue.model_validate({"from": 1, "to": 12, "duration": 1}),
        )
        expected = "static text or group"
    elif kind == "descendant_clip":
        cast(Any, group.children[0]).clip = LayerClip(position=(0, 0), width=20, height=10)
    elif kind == "nested_mask":
        group.children[0] = GroupLayer(
            type="group",
            children=[group.children[0]],
            mask=LayerMask(position=(0, 0), width=20, height=10),
        )
    elif kind == "stagger_parent":
        # Zero delay does not establish an enclosing animated parent frame.
        cast(Any, group.animation).stagger.delay = 0
        group.children = group.children[:1]
        canvas.shape("rectangle", (0, 0), 5, 5, "#00FF00", parent="leaf")
        expected = "cannot be a parent"
    elif kind == "independent":
        group.animation = None
        cast(Any, group.children[0]).animation = AnimationSpec.fade(duration=1)
        expected = "independent descendant"
    else:
        canvas.shape("rectangle", (0, 0), 100, 100, "#FFFFFF", effects=[BackdropBlur(radius=3)])
        expected = "backdrop"
    monkeypatch.setattr(
        ParentNode, "render_source", lambda *a, **k: pytest.fail("preflight painted")
    )
    destination = tmp_path / ("existing." + format)
    for exporter in (canvas, Deck(canvas.width, canvas.height).slide(canvas)):
        destination.write_bytes(b"existing")
        with pytest.raises(RenderingError, match=expected):
            exporter.export(destination, policy=ExportPolicy(unsupported_motion="error"))
        assert destination.read_bytes() == b"existing"
    with pytest.raises(RenderingError, match=expected):
        canvas.render(str(destination))
    assert destination.read_bytes() == b"existing"
