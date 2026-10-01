"""Normalized pivots and independent scale in the shared affine geometry path."""

import json
from pathlib import Path
from typing import Any, cast

import jsonschema
import pytest
from PIL import Image
from quickthumb import (
    AnimationSpec,
    Canvas,
    GifOptions,
    KeyframeSpec,
    PositionTrack,
    RotationTrack,
    ScaleTrack,
    ScaleXTrack,
    ScaleYTrack,
    StaggerSpec,
    TimingSpec,
    canvas_json_schema,
)
from quickthumb import _export_base as base
from quickthumb import _export_video as video
from quickthumb.errors import ValidationError
from quickthumb.motion import (
    LayerState,
    NormalizedKeyframe,
    NormalizedTrack,
    Timeline,
    TimelineEvent,
    _geometry_in_motion,
    apply_transform,
    compile_timeline,
    sample_canonical_state,
    sample_canonical_targets,
    transform_matrix,
)


def track(kind, *values):
    return kind(
        keyframes=[KeyframeSpec(time=index, value=value) for index, value in enumerate(values)]
    )


def animation(*tracks, duration=1, **kwargs):
    return AnimationSpec.timeline(
        *tracks, timing=TimingSpec(duration=duration), easing="linear", **kwargs
    )


def scene(anchor=(0.5, 0.5), motion=None):
    return Canvas(128, 96).shape(
        "rectangle", (48, 36), 24, 16, "#FF2050", anchor=anchor, animation=motion
    )


@pytest.mark.parametrize("anchor", [(0, 0), (1, 1), (0.25, 0.75), [0, 1]])
def test_normalized_anchor_and_axis_tracks_roundtrip_schema_and_inspection(anchor):
    motion = animation(track(ScaleXTrack, 1, 2), track(ScaleYTrack, 1, 0.5))
    canvas = scene(anchor, motion)
    data = json.loads(canvas.to_json())
    jsonschema.validate(data, canvas_json_schema())
    restored = Canvas.from_json(canvas.to_json())
    assert restored.to_json() == canvas.to_json()
    state = restored.inspect_motion().slides[0].layers[0]
    assert state.static_state["anchor"] == list(anchor)
    assert state.final_state["scale_x"] == 2
    assert state.final_state["scale_y"] == 0.5
    assert {item.type for event in state.events for item in event.tracks} == {
        "scale_x",
        "scale_y",
    }
    assert {item.feature for item in restored.inspect_motion().capabilities} >= {
        "anchor",
        "scale_x",
        "scale_y",
    }
    sampled = sample_canonical_state(restored.layers[0], 0.5)
    assert sampled is not None and sampled.anchor == tuple(anchor)


@pytest.mark.parametrize(
    "anchor",
    [
        (-0.1, 0),
        (0, 1.1),
        (float("nan"), 0),
        (0, float("inf")),
        (True, 0),
        ("0.5", 0),
        None,
        (0,),
        (0, 0, 0),
        "center",
    ],
)
def test_invalid_anchor_rejected_at_layer_and_state_boundaries(anchor):
    with pytest.raises((ValidationError, ValueError)):
        scene(cast(Any, anchor))
    with pytest.raises((ValidationError, ValueError)):
        LayerState(anchor=cast(Any, anchor))


@pytest.mark.parametrize("kind", [ScaleXTrack, ScaleYTrack])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), True, "2"])
def test_axis_tracks_reject_nonfinite_or_nonnumeric_values(kind, value):
    with pytest.raises(ValidationError):
        track(kind, value)


def test_omitted_transform_options_keep_original_serialization():
    canvas = scene()
    explicit = scene((0.5, 0.5))
    assert canvas.to_json() == explicit.to_json()
    assert "anchor" not in json.loads(canvas.to_json())["layers"][0]
    assert not {"anchor", "scale_x", "scale_y"} & LayerState().model_dump().keys()
    assert "ScaleXTrack" in canvas_json_schema()["$defs"]
    assert "type" in canvas_json_schema()["$defs"]["ScaleYTrack"]["required"]


@pytest.mark.parametrize("anchor", [(0, 0), (0.5, 0.5), (1, 1), (0.2, 0.8)])
def test_transform_matrix_keeps_pivot_fixed_before_translation(anchor):
    state = LayerState(
        anchor=anchor, scale=1.2, scale_x=2, scale_y=-0.5, rotation=32, position=(7.5, -3.25)
    )
    size = (24, 16)
    pivot = (anchor[0] * size[0], anchor[1] * size[1])
    assert apply_transform(pivot, state, size) == pytest.approx((pivot[0] + 7.5, pivot[1] - 3.25))
    assert apply_transform((0, 0), LayerState(position=(10, 20))) == (10, 20)
    assert transform_matrix(state)[0][2] == 7.5


@pytest.mark.parametrize("size", [(float("nan"), 1), (-1, 1), (True, 1), (1,), None])
def test_transform_rejects_invalid_bounds(size):
    with pytest.raises(ValidationError, match="size"):
        transform_matrix(LayerState(), cast(Any, size))


def test_axes_sample_independently_and_compose_with_uniform_scale():
    timeline = compile_timeline(
        animation(track(ScaleTrack, 1, 2), track(ScaleXTrack, 1, 3), track(ScaleYTrack, 1, -1))
    )
    state = timeline.sample(0.5)
    assert (state.scale, state.scale_x, state.scale_y) == (1.5, 2, 0)
    assert apply_transform((1, 1), state) == (3, 0)
    assert Timeline.model_validate_json(timeline.model_dump_json()) == timeline
    assert _geometry_in_motion(timeline, 0.5, include_scale=False)
    assert not _geometry_in_motion(timeline, 1)


def test_normalized_multiply_and_later_replace_keep_axis_order():
    def event(value, blend):
        return TimelineEvent(
            source="timeline",
            start=0,
            delay=0,
            duration=1,
            tracks=(
                NormalizedTrack(
                    property="scale_x",
                    blend=blend,
                    keyframes=(NormalizedKeyframe(time=0, value=value),),
                ),
            ),
        )

    timeline = Timeline(events=(event(2, "replace"), event(3, "multiply")))
    assert timeline.sample(0).scale_x == 6
    assert Timeline(events=(*timeline.events, event(4, "replace"))).sample(0).scale_x == 4


@pytest.mark.parametrize("anchor", [(0, 0), (0.5, 0.5), (1, 1)])
@pytest.mark.parametrize("scales", [(2, 0.5), (-1, 1), (1, -1), (0, 1), (1, 0)])
@pytest.mark.parametrize("angle", [0, 90, 23])
def test_corner_pivots_signed_axes_and_zero_collapse_match_canvas_video(anchor, scales, angle):
    motion = animation(
        track(ScaleXTrack, 1, scales[0]),
        track(ScaleYTrack, 1, scales[1]),
        track(RotationTrack, 0, angle),
        track(PositionTrack, (0, 0), (0.25, -0.5)),
    )
    canvas = scene(anchor, motion)
    animator = video._SlideAnimator(canvas, {})
    for time in (0, 0.25, 0.75, 1, 1.3, 0.25):
        assert canvas.render_frame(time).tobytes() == animator.frame_at(time).tobytes()
    if 0 in scales:
        assert animator.frame_at(1).getbbox() is None


def test_quarter_turn_about_top_left_has_expected_opaque_bounds():
    canvas = scene((0, 0), animation(track(RotationTrack, 0, 90)))
    alpha = canvas.render_frame(1).getchannel("A").point(lambda value: 255 if value > 127 else 0)
    assert alpha.getbbox() == (32, 36, 48, 60)


def test_new_geometry_uses_one_affine_pass_and_preserves_source(monkeypatch):
    source = Image.new("RGBA", (12, 8), (255, 50, 10, 190))
    original = source.tobytes()
    monkeypatch.setattr(
        Image.Image, "resize", lambda *args, **kwargs: pytest.fail("separate resize")
    )
    monkeypatch.setattr(
        Image.Image, "rotate", lambda *args, **kwargs: pytest.fail("separate rotate")
    )
    result, _ = base.apply_canonical_geometry(
        source, LayerState(anchor=(0, 1), scale_x=1.7, scale_y=0.7, rotation=18), (20, 20)
    )
    assert result.getbbox()
    assert source.tobytes() == original


@pytest.mark.parametrize("quality", ["standard", "high"])
def test_explicit_default_anchor_keeps_all_sampled_pixels(quality):
    motion = animation(
        track(ScaleTrack, 1, 1.15),
        track(RotationTrack, 0, 12),
        track(PositionTrack, (0, 0), (2.3, -0.4)),
    )
    original = scene(motion=motion)
    data = json.loads(original.to_json())
    data["layers"][0]["anchor"] = [0.5, 0.5]
    explicit = Canvas.from_json(json.dumps(data))
    before, after = (
        video._SlideAnimator(original, {}, quality=quality),
        video._SlideAnimator(explicit, {}, quality=quality),
    )
    for time in [None, 0, 0.1, 0.5, 1, 1.5]:
        if time is None:
            assert original._render_to_image().tobytes() == explicit._render_to_image().tobytes()
        else:
            assert before.frame_at(time).tobytes() == after.frame_at(time).tobytes()


@pytest.mark.parametrize("parent_motion", [False, True])
def test_group_and_nested_child_keep_their_rendered_bounds_pivot(parent_motion):
    motion = animation(track(ScaleXTrack, 1, 1.5), track(RotationTrack, 0, 12))
    child = {"type": "shape", "shape": "rectangle", "width": 24, "height": 16, "color": "#FF2050"}
    if not parent_motion:
        child.update(anchor=(0, 0), animation=motion)
    canvas = Canvas(128, 96).group(
        [child], position=(48, 36), anchor=(0, 0), animation=motion if parent_motion else None
    )
    animator = video._SlideAnimator(canvas, {})
    for time in (0, 0.5, 1):
        assert canvas.render_frame(time).tobytes() == animator.frame_at(time).tobytes()


def test_shared_animation_objects_do_not_combine_independent_layer_pivots():
    motion = animation(track(ScaleXTrack, 1, 2))
    canvas = scene((0, 0), motion).shape(
        "rectangle", (90, 36), 10, 16, "#00FF00", anchor=(1, 0), animation=motion
    )
    animator = video._SlideAnimator(canvas, {})
    assert len(animator._units) == 2
    assert canvas.render_frame(0.5).tobytes() == animator.frame_at(0.5).tobytes()


def test_image_axis_scale_moves_outer_frame_while_uniform_scale_remains_viewport_zoom():
    path = "tests/fixtures/sample_image.jpg"
    motion = animation(track(ScaleTrack, 1, 1.5), track(ScaleXTrack, 1, 1.5))
    canvas = Canvas(128, 96).image(
        path, (48, 36), 24, 16, fit="cover", anchor=(0, 0), animation=motion
    )
    animator = video._SlideAnimator(canvas, {})
    for time in (0, 0.5, 1):
        assert canvas.render_frame(time).tobytes() == animator.frame_at(time).tobytes()
    alpha = animator.frame_at(1).getchannel("A").point(lambda value: 255 if value > 127 else 0)
    assert alpha.getbbox() == (48, 36, 84, 52)


def test_staggered_target_clocks_preserve_anchor_and_axis_state():
    motion = animation(track(ScaleXTrack, 1, 2), track(RotationTrack, 0, 20))
    motion.stagger = StaggerSpec(delay=0.5, target="lines")
    canvas = Canvas(180, 160).text(
        "ONE\nTWO\nTHREE",
        position=(40, 40),
        size=20,
        font="assets/fonts/Roboto-Medium.ttf",
        color="#FFFFFF",
        anchor=(0, 0),
        animation=motion,
    )
    states = sample_canonical_targets(canvas.layers[0], 0.75, 3)
    assert states is not None and states[0] is not None and states[1] is not None
    assert states[0].anchor == states[1].anchor == (0, 0)
    assert states[2] is None
    animator = video._SlideAnimator(canvas, {})
    for time in (0.25, 0.75, 1.2, 2):
        assert canvas.render_frame(time).tobytes() == animator.frame_at(time).tobytes()


@pytest.mark.parametrize("quality", ["standard", "high"])
def test_new_transforms_keep_worker_gif_bytes_and_timing(quality, tmp_path):
    motion = animation(
        track(ScaleXTrack, 1, 1.5), track(ScaleYTrack, 1, 0.5), track(RotationTrack, 0, 22)
    )
    canvas = scene((0, 1), motion)
    outputs = [tmp_path / f"{workers}.gif" for workers in (1, 2)]
    for workers, output in zip((1, 2), outputs, strict=True):
        canvas.render(str(output), animation=GifOptions(fps=4, quality=quality, workers=workers))
    assert outputs[0].read_bytes() == outputs[1].read_bytes()


def test_anchor_and_axis_visual_snapshot():
    motion = animation(
        track(ScaleXTrack, 1, 1.6), track(ScaleYTrack, 1, 0.6), track(RotationTrack, 0, 60)
    )
    strip = Image.new("RGBA", (128 * 3, 96 * 3))
    for row, anchor in enumerate([(0, 0), (0.5, 0.5), (1, 1)]):
        canvas = scene(anchor, motion)
        for column, time in enumerate([0, 0.5, 1]):
            strip.paste(canvas.render_frame(time), (128 * column, 96 * row))
    expected = Image.open(Path(__file__).parent / "snapshots" / "anchor_scale_motion.png").convert(
        "RGBA"
    )
    assert (strip.mode, strip.size, strip.tobytes()) == (
        expected.mode,
        expected.size,
        expected.tobytes(),
    )


@pytest.mark.parametrize("quality", ["standard", "high"])
@pytest.mark.parametrize("anchor", [(0, 0), (0.25, 0.75), (1, 1)])
def test_pixel_centroid_matches_independent_forward_affine(quality, anchor):
    motion = animation(
        track(ScaleXTrack, 1.7),
        track(ScaleYTrack, 0.7),
        track(ScaleTrack, 1.2),
        track(RotationTrack, 23),
        track(PositionTrack, (2.25, -0.75)),
    )
    canvas = scene(anchor, motion)
    frame = video._SlideAnimator(canvas, {}, quality=quality).frame_at(0.5)
    alpha = list(frame.getchannel("A").get_flattened_data())
    mass = sum(alpha)
    actual = (
        sum((i % frame.width + 0.5) * value for i, value in enumerate(alpha)) / mass,
        sum((i // frame.width + 0.5) * value for i, value in enumerate(alpha)) / mass,
    )
    state = compile_timeline(motion).sample(0.5, LayerState(anchor=anchor))
    x, y = apply_transform((12, 8), state, (24, 16))
    assert actual == pytest.approx((48 + x, 36 + y), abs=0.12)


@pytest.mark.parametrize("opacity,clip", [(0.4, 0.5), (0, 1), (1, 0)])
def test_anchor_axis_clip_and_opacity_order_is_shared(opacity, clip):
    from quickthumb import ClipProgressTrack, OpacityTrack

    canvas = scene(
        (0, 1),
        animation(
            track(ScaleXTrack, 1, 1.5),
            track(RotationTrack, 0, 23),
            track(OpacityTrack, opacity),
            track(ClipProgressTrack, clip),
        ),
    )
    animator = video._SlideAnimator(canvas, {})
    for time in (0, 0.5, 1, 2):
        actual = canvas.render_frame(time)
        assert actual.tobytes() == animator.frame_at(time).tobytes()
        if opacity == 0 or clip == 0:
            assert actual.getbbox() is None


@pytest.mark.parametrize("motion", [animation(track(ScaleXTrack, 1, 2)), AnimationSpec.pop()])
def test_pptx_declares_and_emits_static_anchor_fallback(motion):
    from io import BytesIO
    from zipfile import ZipFile

    from quickthumb import ExportPolicy
    from quickthumb.errors import RenderingError
    from quickthumb.motion import capabilities_for

    canvas = scene((0, 0), motion)
    diagnostics = canvas.validate_export("pptx")
    assert any(item.feature == "anchor" and item.fallback == "static" for item in diagnostics)
    assert capabilities_for("pptx")["scale_x"].fallback == "static"
    with pytest.raises(RenderingError, match="export policy"):
        canvas.validate_export("pptx", ExportPolicy(unsupported_motion="error"))
    with ZipFile(BytesIO(canvas.to_pptx())) as archive:
        slide = archive.read("ppt/slides/slide1.xml").decode()
    assert "<p:timing>" not in slide


def test_html_capabilities_match_supported_mapping_and_unsupported_composition():
    from quickthumb import ExportPolicy
    from quickthumb.errors import RenderingError

    canvas = scene((0, 0), animation(track(ScaleXTrack, 1, 2)))
    mapped = canvas.validate_export("html", ExportPolicy(unsupported_motion="error"))
    assert {item.feature for item in mapped} == {"anchor", "scale_x"}
    assert all(item.support == "full" and item.fallback is None for item in mapped)
    fallback = scene((0, 0), AnimationSpec.pop())
    assert all(item.fallback == "static" for item in fallback.validate_export("html"))
    with pytest.raises(RenderingError, match="export policy"):
        fallback.validate_export("html", ExportPolicy(unsupported_motion="error"))


def test_anchor_example_runs_and_keeps_reference_crosshairs_visible(monkeypatch):
    import runpy

    monkeypatch.setattr(Canvas, "render", lambda *args, **kwargs: None)
    monkeypatch.setattr(Path, "write_text", lambda *args, **kwargs: None)
    monkeypatch.setattr(Path, "mkdir", lambda *args, **kwargs: None)
    monkeypatch.setattr(Image.Image, "save", lambda *args, **kwargs: None)
    result = runpy.run_path("examples/transform_anchors.py", run_name="__main__")
    canvas = result["build_scene"]()
    assert len(canvas.layers) == 13


def test_parent_animation_overrides_child_anchors_as_one_group():
    parent = animation(track(RotationTrack, 0, 45))
    canvas = Canvas(160, 130).group(
        [
            {
                "type": "shape",
                "shape": "rectangle",
                "width": 24,
                "height": 16,
                "color": "#FF2050",
                "anchor": (0, 0),
            },
            {
                "type": "shape",
                "shape": "rectangle",
                "width": 12,
                "height": 24,
                "color": "#40D0A0",
                "anchor": (0, 0),
            },
        ],
        direction="row",
        gap=8,
        position=(65, 55),
        animation=parent,
    )
    animator = video._SlideAnimator(canvas, {})
    assert len(animator._units) == 1
    for time in (0, 0.25, 0.5, 1):
        assert canvas.render_frame(time).tobytes() == animator.frame_at(time).tobytes()


def test_html_validate_does_not_claim_backdrop_prefix_transform_support():
    from quickthumb import BackdropBlur

    canvas = scene((0, 0), animation(track(ScaleXTrack, 1, 2)))
    canvas.shape("rectangle", (0, 0), 100, 50, "#20406080", effects=[BackdropBlur(radius=2)])
    assert all(item.fallback == "static" for item in canvas.validate_export("html"))


@pytest.mark.parametrize("nested", [False, True])
def test_anchored_group_keeps_intrinsic_counter_content_dynamic(nested):
    child = (
        Canvas(160, 80)
        .counter(0, 100, 1, position=(0, 0), size=30, font="assets/fonts/Roboto-Medium.ttf")
        .layers[0]
    )
    if nested:
        child = Canvas(160, 100).group([child]).layers[0]
    parent = animation(track(RotationTrack, 0, 0))
    canvas = Canvas(160, 100).group([child], position=(20, 20), anchor=(0, 0), animation=parent)
    animator = video._SlideAnimator(canvas, {})
    frames = [animator.frame_at(time).tobytes() for time in (0, 0.5, 1)]
    assert len(set(frames)) == 3
    assert frames == [canvas.render_frame(time).tobytes() for time in (0, 0.5, 1)]


@pytest.mark.parametrize("nested", [False, True])
def test_retained_parent_keeps_child_viewport_animation_overridden(nested):
    child = (
        Canvas(160, 100)
        .image(
            "tests/fixtures/sample_image.jpg",
            (0, 0),
            60,
            40,
            fit="cover",
            animation=animation(track(ScaleTrack, 1, 2)),
        )
        .layers[0]
    )
    if nested:
        child = (
            Canvas(160, 100)
            .group([child], clip={"position": (0, 0), "width": 160, "height": 100})
            .layers[0]
        )
    canvas = Canvas(160, 100).group(
        [child], position=(20, 20), anchor=(0, 0), animation=animation(track(RotationTrack, 0, 0))
    )
    animator = video._SlideAnimator(canvas, {})
    frames = [animator.frame_at(time).tobytes() for time in (0, 0.5, 1)]
    assert len(set(frames)) == 1
    assert frames == [canvas.render_frame(time).tobytes() for time in (0, 0.5, 1)]
