"""Nested counter clocks and authored stills survive every parent adapter."""

from io import BytesIO
from typing import cast

import pytest
from PIL import Image
from quickthumb import (
    AnimatedTextValue,
    Background,
    Canvas,
    ExportPolicy,
    GifOptions,
    GroupLayer,
    LayerClip,
    LayerMask,
    OpacityTrack,
    RotationTrack,
    TextLayer,
)
from quickthumb._export_html import HtmlExporter
from quickthumb._export_video import _SlideAnimator
from quickthumb._parent_render import ParentNode
from quickthumb.errors import RenderingError

from tests.test_parent_counters import FONT, motion, track
from tests.test_parent_diagnostics import composite, setup
from tests.test_parent_documents import embedded_png
from tests.test_parent_group_counters import freeze
from tests.test_parent_nested_diagnostics import nested_scene, target_measurement


def nested_clock_scene():
    def counter(name, delay, style, *, leaf=False):
        return TextLayer(
            type="text",
            id=name,
            content="stale",
            font=FONT,
            size=24,
            color="#FFFFFF",
            effects=[Background(color="#225588", padding=3)],
            value=AnimatedTextValue.model_validate(
                {
                    "from": -9999,
                    "to": 17,
                    "delay": delay,
                    "duration": 0.4,
                    "style": style,
                    "prefix": "$",
                    "suffix": " kg",
                    "grouping": True,
                    "easing": "linear",
                }
            ),
            clip=LayerClip(position=(0, 0), width=280, height=220) if leaf else None,
            mask=LayerMask(position=(0, 0), width=300, height=240, opacity=0.6) if leaf else None,
        )

    deep = GroupLayer(
        type="group",
        id="deep",
        children=[counter("leaf_counter", 1.6, "flip", leaf=True)],
        padding=4,
        clip=LayerClip(position=(12, 12), width=260, height=200, border_radius=6),
        mask=LayerMask(position=(0, 0), width=300, height=240, opacity=0.7),
    )
    middle = GroupLayer(
        type="group",
        id="middle",
        children=[counter("middle_counter", 1, "odometer"), deep],
        padding=4,
        gap=8,
        mask=LayerMask(position=(0, 0), width=300, height=240, opacity=0.8),
    )
    return (
        Canvas(320, 260)
        .null((6, 4), id="root", animation=motion(track(RotationTrack, -5, 8), duration=0.1))
        .group(
            [counter("root_counter", 0.4, "plain"), middle],
            position=(24, 20),
            padding=6,
            gap=8,
            id="group",
            parent="root",
            clip=LayerClip(position=(16, 12), width=270, height=220, border_radius=8),
            mask=LayerMask(position=(0, 0), width=300, height=240, opacity=0.9),
            animation=motion(track(RotationTrack, -3, 4), duration=0.2),
        )
    )


def frozen_scene(canvas):
    # Freeze counter glyphs explicitly, preserving every authored boundary and
    # animation. Static observations must never consult a sampled value clock.
    return Canvas(canvas.width, canvas.height, layers=[freeze(layer) for layer in canvas.layers])


def walk_measurements(items):
    for item in items:
        yield item
        yield from walk_measurements(item.children)


def test_delayed_counters_at_three_boundary_depths_extend_actual_gif_windows():
    canvas = nested_clock_scene()
    animator = _SlideAnimator(canvas, {})
    assert animator.duration == pytest.approx(2)
    assert animator.segments(0.2, 2.3) == [
        (0.2, 0.4, False),
        (0.4, 0.8, True),
        (0.8, 1, False),
        (1, 1.4, True),
        (1.4, 1.6, False),
        (1.6, 2, True),
        (2, 2.3, False),
    ]
    sources, measured = setup(canvas)
    by_id = {item.layer_id: item for item in walk_measurements(measured)}
    for name, depth in (("root_counter", 1), ("middle_counter", 2), ("leaf_counter", 3)):
        occurrence = sources.occurrences[name]
        assert len(occurrence.path) == depth
        assert sources.alpha(by_id[name]).getbbox() is not None
        for scope, _ in occurrence.path:
            owner = scope.node.layer if hasattr(scope, "node") else scope.layer
            assert owner.mask is not None and 0 < owner.mask.opacity < 1
    leaf = sources.occurrences["leaf_counter"].text
    assert leaf is not None and leaf.mask is not None
    windows = [(0.4, 0.8), (1, 1.4), (1.6, 2)]
    frames = [[] for _ in windows]
    with Image.open(BytesIO(canvas.to_gif(fps=10, hold=0.2))) as gif:
        milliseconds = 0
        for index in range(getattr(gif, "n_frames", 1)):
            gif.seek(index)
            for samples, (start, end) in zip(frames, windows, strict=True):
                if round(start * 1000) <= milliseconds < round(end * 1000):
                    samples.append(gif.convert("RGBA").tobytes())
            milliseconds += gif.info.get("duration", 0)
    assert milliseconds == 2200
    assert all(len(set(samples)) >= 3 for samples in frames)


@pytest.mark.parametrize("quality", ["standard", "high"])
def test_nested_counter_serial_and_spawn_gifs_match_after_ancestor_motion(tmp_path, quality):
    canvas = nested_clock_scene()
    original = canvas.to_json()
    paths = [tmp_path / "serial.gif", tmp_path / "spawn.gif"]
    for workers, path in zip((1, 2), paths, strict=True):
        canvas.render(str(path), animation=GifOptions(fps=5, quality=quality, workers=workers))
    assert paths[0].read_bytes() == paths[1].read_bytes()
    with Image.open(paths[0]) as gif:
        assert getattr(gif, "n_frames", 1) >= 6
    assert canvas.to_json() == original


@pytest.mark.parametrize("kind", ["html", "svg", "pdf", "pptx"])
def test_nested_counter_documents_freeze_whole_scene_and_keep_strict_destination(
    tmp_path, monkeypatch, kind
):
    canvas = nested_clock_scene().shape(
        "rectangle",
        (285, 230),
        16,
        12,
        "#FF3300",
        id="independent",
        animation=motion(track(OpacityTrack, 0.2, 0.7)),
    )
    canvas.layers = [*Canvas(320, 260).background(color="#FFFFFF").layers, *canvas.layers]
    original = canvas.to_json()
    reference = frozen_scene(canvas)
    expected = reference._render_to_image()
    assert expected.tobytes() == canvas._render_to_image().tobytes()
    assert expected.tobytes() != canvas.render_frame(0).tobytes()
    assert expected.tobytes() != canvas.render_frame(2).tobytes()
    output = getattr(canvas, "to_" + kind)()
    if kind == "pdf":
        import pypdfium2

        with pypdfium2.PdfDocument(output) as document:
            page = document[0]
            bitmap = page.render(scale=1)
            actual = bitmap.to_pil().convert("RGB")
            assert (actual.size, actual.tobytes()) == (
                expected.size,
                expected.convert("RGB").tobytes(),
            )
            bitmap.close()
            page.close()
    else:
        actual = embedded_png(output, kind)
        assert (actual.size, actual.tobytes()) == (expected.size, expected.tobytes())
    if kind == "html":
        stage = HtmlExporter(canvas).render_stage()
        assert not stage.timeline and not stage.keyframes
    destination = tmp_path / ("nested-counters." + kind)
    report = canvas.export(destination).capability_report
    assert {"parent", "animated_text_value"} <= {item.feature for item in report}
    assert any(item.layer_id == "independent" for item in report)
    assert all(item.support == "fallback" and item.fallback == "static" for item in report)
    monkeypatch.setattr(
        ParentNode, "render_source", lambda *args, **kwargs: pytest.fail("strict export painted")
    )
    monkeypatch.setattr(
        canvas, "_render_layer", lambda *args, **kwargs: pytest.fail("strict export painted")
    )
    for method in (canvas.render, canvas.export):
        destination.write_bytes(b"existing nested counter document")
        with pytest.raises(RenderingError, match="authored-static"):
            method(str(destination), policy=ExportPolicy(unsupported_motion="error"))
        assert destination.read_bytes() == b"existing nested counter document"
    assert canvas.to_json() == original


@pytest.mark.parametrize(
    "policy",
    [
        ExportPolicy(reduced_motion=True),
        ExportPolicy(unsupported_motion="static"),
        ExportPolicy(unsupported_motion="rasterize"),
    ],
)
def test_nested_counter_html_static_policies_use_explicit_settled_reference(policy):
    canvas = nested_clock_scene()
    expected = frozen_scene(canvas)._render_to_image()
    actual = embedded_png(canvas.to_html(policy=policy), "html")
    assert (actual.size, actual.tobytes()) == (expected.size, expected.tobytes())
    assert all(item.fallback == "static" for item in canvas.validate_export("html", policy))


@pytest.mark.parametrize("style", ["plain", "odometer", "flip"])
@pytest.mark.parametrize("invert", [False, True])
def test_nested_counter_static_observations_and_diagnostic_sources_match_frozen_reference(
    style, invert, monkeypatch
):
    canvas = nested_scene(leaf=True, invert=invert, rotation=17)
    root = cast(GroupLayer, canvas.layers[-1])
    outer = cast(GroupLayer, root.children[1])
    wrapper = cast(GroupLayer, outer.children[1])
    inner = cast(GroupLayer, wrapper.children[0])
    target = cast(TextLayer, inner.children[1])
    target.id = "counter"
    target.content = "stale"
    target.value = AnimatedTextValue.model_validate(
        {
            "from": -8888,
            "to": 17,
            "delay": 0.4,
            "duration": 0.8,
            "style": style,
            "prefix": "$",
            "suffix": " kg",
            "grouping": True,
            "easing": "linear",
        }
    )
    canvas.layers[1].animation = motion(track(RotationTrack, -8, 12), duration=0.2)
    reference = frozen_scene(canvas)
    original = canvas.to_json()
    assert canvas.inspect() == reference.inspect()
    assert canvas.diagnose().model_dump() == reference.diagnose().model_dump()
    for debug in (False, True):
        assert canvas._render_to_image(debug=debug).tobytes() == (
            reference._render_to_image(debug=debug).tobytes()
        )

    observed = []
    for scene in (canvas, reference):
        sources, measured = setup(scene)
        item = target_measurement(measured)
        occurrence = sources.occurrences["counter"]
        assert len(occurrence.path) == 3
        assert item.metadata["content"] == "$17 kg"
        assert occurrence.text is not None and occurrence.text.value is None
        assert occurrence.text.mask is not None
        assert all(
            (scope.node.layer if hasattr(scope, "node") else scope.layer).mask is not None
            for scope, _ in occurrence.path
        )
        running = scene._create_canvas()
        scene._render_layer(running, scene.layers[0])
        images = sources.text_images(running, item)
        assert images[1].getbbox() is not None
        alpha = sources.alpha(item)
        assert alpha.getbbox() is not None
        assert composite(scene, sources, measured).tobytes() == scene._render_to_image().tobytes()
        repeated = sources.text_images(running, item)
        assert [image.tobytes() for image in repeated] == [image.tobytes() for image in images]
        observed.append((alpha.tobytes(), *(image.tobytes() for image in images)))
    assert observed[0] == observed[1]
    animator = _SlideAnimator(canvas, {})
    for instant in (0.9, 0.2, 1.2, 0.9):
        animator.frame_at(instant)
        assert canvas._ctx.motion_time is None
    assert canvas.diagnose().model_dump() == reference.diagnose().model_dump()
    monkeypatch.setattr(
        ParentNode, "render_source", lambda *args, **kwargs: pytest.fail("inspection painted")
    )
    assert canvas.inspect() == reference.inspect()
    assert canvas.to_json() == original
