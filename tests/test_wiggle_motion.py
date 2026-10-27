"""Seeded track offsets remain deterministic through seeking and real exports."""

import json
from io import BytesIO
from pathlib import Path
from typing import cast
from zipfile import ZipFile

import jsonschema
import pytest
from PIL import Image
from PIL.GifImagePlugin import GifImageFile
from quickthumb import (
    AnimationSpec,
    BlurTrack,
    Canvas,
    ClipProgressTrack,
    ColorTrack,
    ExportPolicy,
    ImagePanTrack,
    ImageZoomTrack,
    KeyframeSpec,
    OpacityTrack,
    PositionKeyframeSpec,
    PositionTrack,
    TimingSpec,
    Wiggle,
    canvas_json_schema,
)
from quickthumb.errors import RenderingError, ValidationError
from quickthumb.motion import compile_timeline, validate_export


def wiggle_scene(*, seed=156, parented=False) -> Canvas:
    canvas = Canvas(96, 96).background(color="#000000")
    if parented:
        canvas.null(position=(0, 0), id="root")
    return canvas.shape(
        "rectangle",
        (40, 40),
        12,
        12,
        "#FFFFFF",
        parent="root" if parented else None,
        animation=AnimationSpec.timeline(
            PositionTrack(
                keyframes=[KeyframeSpec(time=0, value=(0, 0))],
                wiggle=Wiggle(frequency=2, amplitude=12, seed=seed),
            ),
            timing=TimingSpec(duration=1),
        ),
    )


@pytest.mark.parametrize("workers", [1, 2])
def test_wiggle_seek_and_parallel_export(workers):
    """A stored seed produces identical sought and sequential GIF pixels for each worker count."""
    # Given: constant authored geometry carrying an event-local wiggle clock
    scene = wiggle_scene()
    document = scene.to_json()
    payload = json.loads(document)
    jsonschema.validate(payload, canvas_json_schema())
    restored = Canvas.from_json(document)
    assert payload["layers"][1]["animation"]["tracks"][0]["wiggle"]["seed"] == 156

    # When: seeking out of order before a sequential or spawned-worker export
    sought = {index: restored.render_frame(index / 10).tobytes() for index in reversed(range(11))}
    elapsed = 0
    with cast(
        GifImageFile, Image.open(BytesIO(restored.to_gif(fps=10, hold=0.1, workers=workers)))
    ) as gif:
        for index in range(gif.n_frames):
            gif.seek(index)
            # Then: the encoded frame at its displayed time matches the direct seek
            assert gif.convert("RGBA").tobytes() == sought[round(elapsed / 100)]
            elapsed += gif.info["duration"]
    assert elapsed == 1100
    assert sought[5] != sought[0]
    assert restored.render_frame(5).tobytes() == sought[10]
    assert wiggle_scene(seed=157).render_frame(0.5).tobytes() != sought[5]


def test_wiggle_preserves_property_bounds_and_holds():
    """Wiggle offsets held numeric values while preserving each bounded property's valid range."""
    # Given: constant properties held for one full animation event
    modifier = Wiggle(frequency=3, amplitude=4, seed=156)
    timeline = compile_timeline(
        AnimationSpec.timeline(
            OpacityTrack(
                keyframes=[
                    KeyframeSpec(time=0, value=0.5, hold=True),
                    KeyframeSpec(time=1, value=0.75),
                ],
                wiggle=modifier,
            ),
            ClipProgressTrack(keyframes=[KeyframeSpec(time=0, value=0.5)], wiggle=modifier),
            ImageZoomTrack(keyframes=[KeyframeSpec(time=0, value=1.1)], wiggle=modifier),
            BlurTrack(keyframes=[KeyframeSpec(time=0, value=0.1)], wiggle=modifier),
            ImagePanTrack(keyframes=[KeyframeSpec(time=0, value=(0, 0))], wiggle=modifier),
            PositionTrack(keyframes=[KeyframeSpec(time=0, value=(0, 0))], wiggle=modifier),
            timing=TimingSpec(duration=1),
        )
    )

    # When: arbitrary samples cross both positive and negative noise offsets
    states = [timeline.sample(index / 100) for index in range(101)]

    # Then: the base hold does not stop the modifier and property constraints survive
    assert len({state.opacity for state in states}) > 2
    for state in states:
        assert 0 <= state.opacity <= 1
        assert 0 <= state.clip_progress <= 1
        assert state.image_zoom >= 1
        assert state.blur >= 0
        assert all(-1 <= component <= 1 for component in state.image_pan)
        assert state.position is not None
        assert all(abs(component) <= modifier.amplitude for component in state.position)
    assert timeline.sample(1).model_dump() == timeline.sample(10).model_dump()
    with pytest.raises(ValidationError):
        ColorTrack.model_validate(
            {
                "keyframes": [{"time": 0, "value": "#FF0000"}],
                "wiggle": modifier.model_dump(),
            }
        )
    with pytest.raises(ValidationError, match="remain finite"):
        PositionTrack(
            keyframes=[KeyframeSpec(time=0, value=(1e308, 0))], wiggle=Wiggle(amplitude=1e308)
        )


def test_wiggle_keeps_authored_path_heading():
    """Wiggle offsets a path's position while auto-orientation follows its authored heading."""
    # Given: one curved path, with and without a position modifier
    keys = [
        PositionKeyframeSpec(time=0, value=(0, 0), out_tangent=(0, 40)),
        PositionKeyframeSpec(time=1, value=(40, 0), in_tangent=(0, 40)),
    ]
    plain = compile_timeline(
        AnimationSpec.timeline(PositionTrack(keyframes=keys, auto_orient=True))
    )
    modified = compile_timeline(
        AnimationSpec.timeline(
            PositionTrack(
                keyframes=keys,
                auto_orient=True,
                wiggle=Wiggle(amplitude=12, seed=156),
            )
        )
    )

    # When/Then: sampling a shared time changes position without inventing a noisy heading
    assert modified.sample(0.5).position != plain.sample(0.5).position
    assert modified.sample(0.5).rotation == plain.sample(0.5).rotation


@pytest.mark.parametrize(("parented", "feature"), [(False, "wiggle"), (True, "parent")])
def test_wiggle_inspection_and_document_fallback(parented, feature):
    """Document exporters declare static wiggle handling, including parent-linked scenes."""
    # Given: a direct or parent-linked track carrying its seed and parameters
    scene = wiggle_scene(parented=parented)
    report = scene.inspect_motion(fps=2)
    layer = next(layer for layer in report.slides[0].layers if layer.events)

    # When/Then: inspection preserves the modifier and its sampled variation
    assert layer.events[0].tracks[0].wiggle == Wiggle(frequency=2, amplitude=12, seed=156)
    assert layer.samples[1]["position"] != layer.initial_state["position"]
    assert any(item.feature == "wiggle" for item in report.capabilities)
    for target in ("html", "pptx"):
        assert (
            next(
                item for item in validate_export(scene, target) if item.feature == feature
            ).fallback
            == "static"
        )
        with pytest.raises(RenderingError) as error:
            validate_export(scene, target, ExportPolicy(unsupported_motion="error"))
        assert error.value.code == "unsupported_capability"
    assert "@keyframes qt-" not in scene.to_html()
    with ZipFile(BytesIO(scene.to_pptx())) as archive:
        assert b"<p:timing" not in archive.read("ppt/slides/slide1.xml")


def test_wiggle_example_snapshot():
    """The seeded position and rotation example reproduces its intermediate pixels."""
    from examples.wiggle_motion import build_scene

    # Given: the documented seed comparison and its committed intermediate image
    with Image.open(Path(__file__).parent / "snapshots/wiggle_motion.png") as expected:
        # When/Then: a direct sample agrees without rendering earlier frames
        assert build_scene().render_frame(0.5).tobytes() == expected.convert("RGBA").tobytes()
