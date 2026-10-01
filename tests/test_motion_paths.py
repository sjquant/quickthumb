"""Bezier geometry, distance clocks, orientation and exporter boundaries."""

import json
import math
import re
from bisect import bisect_left
from html import unescape
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import jsonschema
import pytest
from PIL import Image
from quickthumb import (
    AnimationSpec,
    BackdropBlur,
    Canvas,
    ColorTrack,
    ExportPolicy,
    GifOptions,
    ImagePanTrack,
    KeyframeSpec,
    PositionKeyframeSpec,
    PositionTrack,
    RotationTrack,
    ScaleXTrack,
    StaggerSpec,
    TimingSpec,
    canvas_json_schema,
)
from quickthumb import _export_video as video
from quickthumb._export_html import _baked_motion_stops, _supports_transform_extensions_html
from quickthumb._motion_path import _arc, sample_segment
from quickthumb.errors import RenderingError, ValidationError
from quickthumb.models import ShapeLayer
from quickthumb.motion import (
    LayerState,
    NormalizedKeyframe,
    NormalizedTrack,
    Timeline,
    _geometry_in_motion,
    capabilities_for,
    compile_timeline,
)


def path(*, auto_orient=True, duration=1, loop=False):
    return PositionTrack(
        auto_orient=auto_orient,
        keyframes=[
            PositionKeyframeSpec(time=0, value=(0, 0), out_tangent=(0, 80)),
            PositionKeyframeSpec(
                time=duration,
                value=(0, 0) if loop else (100, 0),
                in_tangent=(100, 80) if loop else (0, 80),
            ),
        ],
    )


def animation(*tracks, duration=1, start=0, easing="linear"):
    return AnimationSpec.timeline(
        *tracks, timing=TimingSpec(start=start, duration=duration), easing=easing
    )


def scene(motion=None, **kwargs):
    return Canvas(180, 130).shape(
        "rectangle", (25, 30), 24, 12, "#F0804080", animation=motion or animation(path()), **kwargs
    )


def scalar(kind, *values):
    return kind(keyframes=[KeyframeSpec(time=i, value=value) for i, value in enumerate(values)])


def reference_point(points, u):
    return tuple(
        sum(
            weight * point[axis]
            for weight, point in zip(
                ((1 - u) ** 3, 3 * (1 - u) ** 2 * u, 3 * (1 - u) * u * u, u**3), points, strict=True
            )
        )
        for axis in (0, 1)
    )


@pytest.mark.parametrize(
    "points",
    [
        ((0, 0), (0, 80), (100, 80), (100, 0)),
        ((0, 0), (0, 0), (100, 0), (100, 0)),
        ((0, 0), (150, -70), (-30, 100), (0, 0)),
        ((0, 0), (100, 0), (-100, 0), (0, 0)),
    ],
)
def test_distance_progress_matches_independent_dense_cubic_reference(points):
    samples = [reference_point(points, i / 20000) for i in range(20001)]
    lengths = [0.0]
    for a, b in zip(samples, samples[1:], strict=False):
        lengths.append(lengths[-1] + math.dist(a, b))
    outgoing = tuple(b - a for a, b in zip(points[0], points[1], strict=True))
    incoming = tuple(b - a for a, b in zip(points[3], points[2], strict=True))
    for step in range(41):
        progress = step / 40
        distance = progress * lengths[-1]
        index = max(1, bisect_left(lengths, distance))
        fraction = (distance - lengths[index - 1]) / (lengths[index] - lengths[index - 1])
        expected = reference_point(points, (index - 1 + fraction) / 20000)
        actual, angle = sample_segment(points[0], points[3], outgoing, incoming, progress)
        assert actual == pytest.approx(expected, abs=0.0001)
        assert angle is None or math.isfinite(angle)


def test_samples_are_on_actual_cubic_not_flattened_chords():
    for step in range(1, 80):
        point, _ = sample_segment((0, 0), (100, 0), (0, 80), (0, 80), step / 80)
        low, high = 0.0, 1.0
        for _ in range(50):
            middle = (low + high) / 2
            if 100 * (3 * middle**2 - 2 * middle**3) < point[0]:
                low = middle
            else:
                high = middle
        u = (low + high) / 2
        assert point[1] == pytest.approx(240 * u * (1 - u), abs=1e-10)


def test_easing_applies_to_segment_distance_and_clamps_path_overshoot():
    linear = compile_timeline(animation(path()))
    eased = compile_timeline(animation(path(), easing="ease_in_quad"))
    assert eased.sample(0.5) == linear.sample(0.25)
    back = compile_timeline(animation(path(), easing="ease_in_back"))
    assert back.sample(0.1).position == (0, 0)
    legacy = compile_timeline(
        animation(
            PositionTrack(
                keyframes=[KeyframeSpec(time=0, value=(0, 0)), KeyframeSpec(time=1, value=(100, 0))]
            ),
            easing="ease_in_back",
        )
    )
    position = legacy.sample(0.1).position
    assert position is not None and position[0] < 0


def test_collinear_zero_handles_are_constant_speed():
    motion = animation(
        PositionTrack(
            keyframes=[
                PositionKeyframeSpec(time=0, value=(0, 0), out_tangent=(0, 0)),
                PositionKeyframeSpec(time=1, value=(100, 0), in_tangent=(0, 0)),
            ]
        )
    )
    for i in range(11):
        assert compile_timeline(motion).sample(i / 10).position == pytest.approx(
            (i * 10, 0), abs=0.00002
        )


@pytest.mark.parametrize(
    "bad", [(math.nan, 0), (math.inf, 0), (True, 0), ("1", 0), (0,), (0, 0, 0), "bad"]
)
def test_invalid_tangents_rejected(bad):
    with pytest.raises((ValueError, ValidationError)):
        PositionKeyframeSpec(time=0, value=(0, 0), out_tangent=bad)


def test_control_overflow_and_nonposition_path_metadata_rejected():
    with pytest.raises((ValueError, ValidationError), match="finite control"):
        PositionTrack(
            keyframes=[PositionKeyframeSpec(time=0, value=(1e308, 0), out_tangent=(1e308, 0))]
        )
    with pytest.raises((ValueError, ValidationError)):
        ImagePanTrack.model_validate(
            {"keyframes": [{"time": 0, "value": [0, 0], "out_tangent": [1, 1]}]}
        )
    with pytest.raises((ValueError, ValidationError)):
        ImagePanTrack.model_validate(
            {"auto_orient": True, "keyframes": [{"time": 0, "value": [0, 0]}]}
        )
    with pytest.raises(ValidationError):
        NormalizedTrack(
            property="rotation", keyframes=(NormalizedKeyframe(time=0, value=0, in_tangent=(0, 0)),)
        )
    with pytest.raises(ValidationError):
        NormalizedTrack(
            property="rotation", auto_orient=True, keyframes=(NormalizedKeyframe(time=0, value=0),)
        )


def test_legacy_model_and_normalized_serialization_unchanged():
    track = PositionTrack(
        keyframes=[KeyframeSpec(time=0, value=(0, 0)), KeyframeSpec(time=1, value=(5, 3))]
    )
    assert track.model_dump(mode="json") == {
        "type": "position",
        "keyframes": [
            {"type": "keyframe", "time": 0, "value": [0, 0]},
            {"type": "keyframe", "time": 1, "value": [5, 3]},
        ],
    }
    normalized = compile_timeline(animation(track)).events[0].tracks[0]
    assert normalized.model_dump(mode="json") == {
        "property": "position",
        "blend": "replace",
        "keyframes": [{"time": 0, "value": [0, 0]}, {"time": 1, "value": [5, 3]}],
    }
    for i in range(11):
        assert compile_timeline(animation(track)).sample(i / 10).position == (
            5 * (i / 10),
            3 * (i / 10),
        )


def test_path_schema_roundtrip_inspection_and_reduced_motion():
    canvas = scene()
    specification = canvas.to_json()
    jsonschema.validate(json.loads(specification), canvas_json_schema())
    restored = Canvas.from_json(specification)
    assert restored.to_json() == specification
    for t in (0, 0.4, 1):
        assert restored.render_frame(t).tobytes() == canvas.render_frame(t).tobytes()
    timeline = compile_timeline(animation(path()))
    assert Timeline.model_validate_json(timeline.model_dump_json()) == timeline
    report = canvas.inspect_motion()
    track = report.slides[0].layers[0].events[0].tracks[0]
    assert track.auto_orient
    assert track.keyframes[0].out_tangent == (0, 80)
    assert "motion_path" in {item.feature for item in report.capabilities}
    assert (
        "motion_path"
        in canvas.inspect_motion(
            policy=ExportPolicy(reduced_motion=True)
        ).reduced_motion.removed_features
    )
    assert "@keyframes" not in canvas.to_html(policy=ExportPolicy(reduced_motion=True))


@pytest.mark.parametrize(
    "values,expected",
    [([(0, 0), (0, 100)], 90), ([(0, 0), (-100, 0)], 180), ([(0, 0), (0, -100)], -90)],
)
def test_linear_auto_heading_and_ordered_rotation_override(values, expected):
    oriented = PositionTrack(
        auto_orient=True,
        keyframes=[KeyframeSpec(time=i, value=value) for i, value in enumerate(values)],
    )
    rotation = scalar(RotationTrack, 20, 40)
    assert compile_timeline(animation(rotation, oriented)).sample(0.5).rotation == expected
    assert compile_timeline(animation(oriented, rotation)).sample(0.5).rotation == 30
    replacement = PositionTrack(keyframes=[KeyframeSpec(time=0, value=(0, 0))])
    state = compile_timeline(animation(oriented, replacement)).sample(0.5)
    assert state.rotation == expected and state.position == (0, 0)


def test_stationary_and_single_key_paths_retain_rotation():
    for track in (
        PositionTrack(auto_orient=True, keyframes=[KeyframeSpec(time=0, value=(0, 0))]),
        PositionTrack(
            auto_orient=True,
            keyframes=[
                PositionKeyframeSpec(time=0, value=(0, 0), out_tangent=(0, 0)),
                PositionKeyframeSpec(time=1, value=(0, 0), in_tangent=(0, 0)),
            ],
        ),
    ):
        timeline = compile_timeline(animation(track))
        assert timeline.sample(0.5, LayerState(rotation=32)).rotation == 32
        assert not _geometry_in_motion(timeline, 0.5)


def test_holds_endpoints_decimal_boundaries_and_out_of_order_sampling():
    track = PositionTrack(
        auto_orient=True,
        keyframes=[
            PositionKeyframeSpec(time=0.2, value=(0, 0), out_tangent=(0, 30)),
            PositionKeyframeSpec(time=0.7, value=(50, 0), in_tangent=(0, 30)),
            PositionKeyframeSpec(time=0.9, value=(50, 0)),
        ],
    )
    timeline = compile_timeline(animation(track, start=0.1))
    assert timeline.sample(0.05) == LayerState()
    assert timeline.sample(0.1).position == (0, 0)
    assert not _geometry_in_motion(timeline, 0.25)
    assert _geometry_in_motion(timeline, 0.5)
    assert not _geometry_in_motion(timeline, 0.8)
    assert timeline.sample(1).rotation == pytest.approx(-90, abs=0.01)
    assert timeline.sample(0.5) == timeline.sample(0.5)
    canvas = scene(animation(track, start=0.1))
    animator = video._SlideAnimator(canvas, {})
    for t in (1, 0.4, 0, 0.8, 0.2, 0.4):
        assert animator.frame_at(t).tobytes() == canvas.render_frame(t).tobytes()


def test_loops_select_affine_motion_and_respect_later_overrides():
    motion = animation(path(loop=True, auto_orient=False))
    timeline = compile_timeline(motion)
    assert timeline.sample(0).position == timeline.sample(1).position == (0, 0)
    assert timeline.sample(0.5).position != (0, 0)
    assert _geometry_in_motion(timeline, 0.5)
    assert not _geometry_in_motion(timeline, 0)
    assert not _geometry_in_motion(timeline, 1)
    still = PositionTrack(keyframes=[KeyframeSpec(time=0, value=(0, 0))])
    assert not _geometry_in_motion(
        compile_timeline(animation(path(loop=True, auto_orient=False), still)), 0.5
    )
    assert _geometry_in_motion(compile_timeline(animation(path(loop=True), still)), 0.5)
    assert not _geometry_in_motion(
        compile_timeline(animation(path(loop=True), still, scalar(RotationTrack, 0, 0))), 0.5
    )


@pytest.mark.parametrize("quality", ["standard", "high"])
def test_raster_video_paths_keep_geometry_color_and_spawn_parity(quality, tmp_path):
    canvas = scene(
        animation(path(), scalar(ColorTrack, "#FF0000", "#0000FF"), scalar(ScaleXTrack, 1, 1.2)),
        anchor=(0, 1),
        opacity=0.7,
    )
    animator = video._SlideAnimator(canvas, {}, quality=quality)
    for time in (0, 0.25, 0.5, 0.75, 1, 0.25):
        actual = animator.frame_at(time)
        if quality == "standard":
            assert actual.tobytes() == canvas.render_frame(time).tobytes()
        else:
            assert (
                actual.tobytes()
                == video._composite_frame(canvas, animator._units, time, render_scale=2).tobytes()
            )
    outputs = [tmp_path / f"path-{workers}.gif" for workers in (1, 2)]
    for workers, output in zip((1, 2), outputs, strict=True):
        canvas.render(str(output), animation=GifOptions(fps=4, quality=quality, workers=workers))
    assert outputs[0].read_bytes() == outputs[1].read_bytes()


def test_html_bakes_eased_samples_and_declares_approximation():
    canvas = scene(animation(path(), easing="ease_in_quad"))
    timeline = compile_timeline(canvas.layers[0].animation)
    stops, final = _baked_motion_stops(timeline.events[0])
    state = timeline.sample(0.5)
    assert state.position is not None
    assert float(stops[50]["--qt-motion-x"]) == state.position[0]
    assert float(stops[50]["--qt-motion-y"]) == state.position[1]
    assert float(final["--qt-motion-x"]) == 100
    html = canvas.to_html()
    match = re.search(r"data-qt-timeline='([^']*)'", html)
    assert match is not None
    assert json.loads(unescape(match[1]))[0]["e"] == "linear"
    assert "@keyframes" in html and "data:image/png" in html
    report = {item.feature: item for item in canvas.validate_export("html")}
    assert report["motion_path"].support == "partial"
    assert report["motion_path"].fallback is None
    assert "approximate" in report["motion_path"].message
    with pytest.raises(RenderingError, match="partial"):
        canvas.validate_export("html", ExportPolicy(unsupported_motion="error"))


def test_html_unwraps_auto_heading_but_preserves_authored_multiturns():
    curve = PositionTrack(
        auto_orient=True,
        keyframes=[
            PositionKeyframeSpec(time=0, value=(0, 0), out_tangent=(-50, 20)),
            PositionKeyframeSpec(time=1, value=(-100, 0), in_tangent=(50, 20)),
        ],
    )
    stops, _ = _baked_motion_stops(compile_timeline(animation(curve)).events[0])
    angles = [float(value["--qt-motion-rotation"]) for value in stops.values()]
    assert max(abs(a - b) for a, b in zip(angles, angles[1:], strict=False)) < 5
    stops, final = _baked_motion_stops(
        compile_timeline(animation(curve, scalar(RotationTrack, 0, 720))).events[0]
    )
    assert float(stops[50]["--qt-motion-rotation"]) == 360
    assert float(final["--qt-motion-rotation"]) == 720


def test_html_preserves_knots_and_holds_with_bounded_output():
    track = PositionTrack(
        auto_orient=True,
        keyframes=[
            KeyframeSpec(time=0.123, value=(0, 0)),
            KeyframeSpec(time=7.789, value=(100, 50)),
        ],
    )
    event = compile_timeline(animation(track, duration=1000)).events[0]
    stops, _ = _baked_motion_stops(event)
    assert len(stops) <= 4097
    assert {0, (0.123 / 1000) * 100, (7.789 / 1000) * 100, 100} <= stops.keys()
    many = PositionTrack(
        auto_orient=True, keyframes=[KeyframeSpec(time=i / 5000, value=(i, 0)) for i in range(5001)]
    )
    canvas = scene(animation(many))
    assert not _supports_transform_extensions_html(canvas.layers[0])
    assert all(item.fallback == "static" for item in canvas.validate_export("html"))


@pytest.mark.parametrize("unsupported", ["list", "stagger", "color"])
def test_unsupported_html_path_combinations_are_authored_static(unsupported):
    motion = animation(path())
    if unsupported == "list":
        motion = [motion, animation(path())]
    elif unsupported == "stagger":
        motion.stagger = StaggerSpec(delay=0.2, target="children")
    else:
        motion.tracks.append(scalar(ColorTrack, "#FF0000", "#00FF00"))
    canvas = scene(motion)
    assert "@keyframes" not in canvas.to_html()
    assert all(item.fallback == "static" for item in canvas.validate_export("html"))


def test_pptx_has_static_path_fallback_and_no_timing():
    canvas = scene()
    assert capabilities_for("pptx")["motion_path"].fallback == "static"
    assert all(item.fallback == "static" for item in canvas.validate_export("pptx"))
    with ZipFile(BytesIO(canvas.to_pptx())) as archive:
        assert b"<p:timing" not in archive.read("ppt/slides/slide1.xml")


def test_path_color_backdrop_group_conflict_is_not_silently_widened():
    child = (
        Canvas(100, 80)
        .shape("rectangle", (5, 5), 30, 20, "#FFFFFF80", effects=[BackdropBlur(radius=2)])
        .layers[0]
    )
    assert isinstance(child, ShapeLayer)
    canvas = Canvas(180, 130).group(
        [child.model_copy(update={"position": None})],
        position=(10, 10),
        animation=animation(path(), scalar(ColorTrack, "#FF0000", "#00FF00")),
    )
    report = canvas.validate_export("video")
    assert any(
        item.feature == "color" and item.support == "unsupported" and item.fallback is None
        for item in report
    )
    with pytest.raises(RenderingError, match="backdrop"):
        canvas.render_frame(0.5)


def test_geometry_cache_is_bounded_and_reused_across_compilation():
    _arc.cache_clear()
    motion = animation(path())
    for _ in range(3):
        compile_timeline(motion).sample(0.4)
    assert _arc.cache_info().misses == 1 and _arc.cache_info().hits == 2
    for i in range(80):
        sample_segment((0, 0), (i + 1, 0), (0, 1), (0, 1), 0.5)
    assert _arc.cache_info().currsize == 64
    curve = _arc(((0, 0), (0, 80), (100, 80), (100, 0)))
    assert len(curve.parameters) <= 4097


def snapshot_strip():
    strip = Image.new("RGBA", (180 * 5, 130 * 2))
    for row, oriented in enumerate((False, True)):
        canvas = scene(animation(path(auto_orient=oriented)))
        for col, time in enumerate((0, 0.25, 0.5, 0.75, 1)):
            strip.paste(canvas.render_frame(time), (180 * col, 130 * row))
    return strip


def test_motion_path_visual_snapshot():
    actual = snapshot_strip()
    expected = Image.open(Path(__file__).parent / "snapshots" / "motion_path.png").convert("RGBA")
    assert (actual.size, actual.tobytes()) == (expected.size, expected.tobytes())


def test_directionless_auto_orient_does_not_override_rotation_activity():
    rotating = scalar(RotationTrack, 0, 90)
    stationary = PositionTrack(
        auto_orient=True,
        keyframes=[
            PositionKeyframeSpec(time=0, value=(0, 0), out_tangent=(0, 0)),
            PositionKeyframeSpec(time=1, value=(0, 0)),
        ],
    )
    timeline = compile_timeline(animation(rotating, stationary))
    assert timeline.sample(0.5).rotation == 45
    assert _geometry_in_motion(timeline, 0.5)


def test_nonposition_tracks_reject_position_keyframe_instances_with_handles():
    key = PositionKeyframeSpec(time=0, value=(0, 0), out_tangent=(0, 0))
    with pytest.raises(ValidationError, match="position tracks"):
        ImagePanTrack(keyframes=[key])


def test_position_keyframe_schema_retains_required_type_tag():
    data = json.loads(scene().to_json())
    key = data["layers"][0]["animation"]["tracks"][0]["keyframes"][0]
    del key["type"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(data, canvas_json_schema())


def test_path_children_and_shared_specs_use_independent_source_adapters():
    motion = animation(path())
    child = scene(motion).layers[0].model_copy(update={"position": None})
    grouped = Canvas(260, 190).group([child], position=(30, 40))
    independent = Canvas(260, 190)
    for x in (30, 110):
        independent.shape("rectangle", (x, 40), 24, 12, "#FF0000", animation=motion)
    for canvas in (grouped, independent):
        animator = video._SlideAnimator(canvas, {})
        for time in (0, 0.5, 1, 0.5):
            assert animator.frame_at(time).tobytes() == canvas.render_frame(time).tobytes()
    assert len(video._SlideAnimator(independent, {})._units) == 2


def test_parent_path_retains_one_group_pivot_in_html_and_video():
    child = scene().layers[0].model_copy(update={"position": None, "animation": None})
    canvas = Canvas(260, 190).group(
        [child, child], direction="row", gap=30, position=(30, 40), animation=animation(path())
    )
    html = canvas.to_html()
    match = re.search(r"data-qt-timeline='([^']*)'", html)
    assert match is not None
    assert len(json.loads(unescape(match[1]))) == 1
    animator = video._SlideAnimator(canvas, {})
    assert len(animator._units) == 1
    for time in (0, 0.5, 1):
        assert animator.frame_at(time).tobytes() == canvas.render_frame(time).tobytes()


@pytest.mark.parametrize("nested", [False, True])
def test_path_groups_keep_counter_dynamic_and_child_viewport_overridden(nested):
    counter = (
        Canvas(160, 100)
        .counter(0, 100, 1, position=(0, 0), size=30, font="assets/fonts/Roboto-Medium.ttf")
        .layers[0]
    )
    image = (
        Canvas(160, 100)
        .image(
            "tests/fixtures/sample_image.jpg",
            (0, 0),
            60,
            40,
            fit="cover",
            animation=animation(
                PositionTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value=(0, 0)),
                        KeyframeSpec(time=1, value=(30, 40)),
                    ]
                )
            ),
        )
        .layers[0]
    )
    for child in (counter, image):
        if nested:
            child = Canvas(160, 100).group([child]).layers[0]
        canvas = Canvas(260, 190).group([child], position=(25, 30), animation=animation(path()))
        animator = video._SlideAnimator(canvas, {})
        for time in (0, 0.5, 1, 0.5):
            assert animator.frame_at(time).tobytes() == canvas.render_frame(time).tobytes()
    assert animator._units[0].timeline is not None


@pytest.mark.parametrize(
    "easing,times",
    [("ease_in_back", (0, 0.001, 0.1, 0.5)), ("ease_out_back", (0.5, 0.9, 0.999, 1))],
)
def test_clamped_path_plateaus_keep_identical_states_and_pixels(easing, times):
    curve = PositionTrack(
        auto_orient=True,
        keyframes=[
            PositionKeyframeSpec(time=0, value=(0, 0), out_tangent=(40, 40)),
            PositionKeyframeSpec(time=1, value=(100, 0), in_tangent=(0, 40)),
        ],
    )
    canvas = scene(animation(curve, easing=easing))
    timeline = compile_timeline(canvas.layers[0].animation)
    states = [timeline.sample(time) for time in times]
    assert all(state == states[0] for state in states)
    assert all(not _geometry_in_motion(timeline, time) for time in times)
    assert len({canvas.render_frame(time).tobytes() for time in times}) == 1


def test_html_cap_keeps_only_finite_in_range_stops_at_float_boundaries():
    curve = PositionTrack(
        auto_orient=True,
        keyframes=[KeyframeSpec(time=0.1 * (i / 4094), value=(i, 0)) for i in range(4095)],
    )
    stops, _ = _baked_motion_stops(compile_timeline(animation(curve, duration=0.1)).events[0])
    assert len(stops) <= 4097
    assert all(math.isfinite(percent) and 0 <= percent <= 100 for percent in stops)
    curve = PositionTrack(
        auto_orient=True,
        keyframes=[KeyframeSpec(time=0, value=(0, 0)), KeyframeSpec(time=1e308, value=(100, 0))],
    )
    stops, _ = _baked_motion_stops(compile_timeline(animation(curve, duration=1e308)).events[0])
    assert len(stops) <= 4097
    assert all(math.isfinite(percent) and 0 <= percent <= 100 for percent in stops)
    assert float(stops[100]["--qt-motion-x"]) == 100


def test_huge_finite_linear_endpoints_keep_finite_correct_heading():
    position, angle = sample_segment((-1e308, -1e308), (1e308, 5e307), None, None, 0.5)
    assert all(math.isfinite(value) for value in position)
    assert angle == pytest.approx(math.degrees(math.atan2(1.5, 2)))


def test_unused_endpoint_handles_are_diagnosed_and_schema_example_validates():
    curve = PositionTrack(
        keyframes=[
            PositionKeyframeSpec(time=0, value=(0, 0), in_tangent=(10, 0)),
            PositionKeyframeSpec(time=1, value=(20, 0), out_tangent=(10, 0)),
        ]
    )
    canvas = scene(animation(curve))
    finding = next(
        item for item in canvas.diagnose().findings if item.code == "motion-path-unused-handle"
    )
    assert finding.measured["unused_handles"] == ["in_tangent", "out_tangent"]
    assert finding.layer_id == "layer:0"
    child = canvas.layers[0].model_copy(update={"position": None})
    nested = Canvas(180, 130).group([child], position=(25, 30))
    findings = [
        item for item in nested.diagnose().findings if item.code == "motion-path-unused-handle"
    ]
    assert len(findings) == 1 and findings[0].layer_id == "layer:0:0"
    schema = canvas_json_schema()
    example = schema["$defs"]["PositionTrack"]["examples"][0]
    jsonschema.validate(example, {"$defs": schema["$defs"], "$ref": "#/$defs/PositionTrack"})


def test_shifted_decimal_knots_keep_incoming_heading_and_tiny_intervals_interpolate():
    track = PositionTrack(
        auto_orient=True,
        keyframes=[
            KeyframeSpec(time=0, value=(0, 0)),
            KeyframeSpec(time=0.7, value=(70, 0)),
            KeyframeSpec(time=1, value=(70, 30)),
        ],
    )
    timeline = compile_timeline(animation(track, start=0.1))
    assert timeline.sample(0.8).position == (70, 0)
    assert timeline.sample(0.8).rotation == 0
    assert timeline.sample(0.8 + 1e-8).rotation == 90
    assert timeline.sample(0.8 - 1e-8).rotation == 0
    tiny = PositionTrack(
        auto_orient=True,
        keyframes=[KeyframeSpec(time=0, value=(0, 0)), KeyframeSpec(time=1e-12, value=(10, 0))],
    )
    assert compile_timeline(animation(tiny, duration=1e-12)).sample(5e-13).position == (5, 0)


def test_html_retained_static_parent_does_not_advertise_child_animation():
    child = scene().layers[0].model_copy(update={"position": None})
    canvas = Canvas(260, 190).group([child], position=(30, 40), animation=animation(path()))
    assert "@keyframes" not in canvas.to_html()
    assert all(item.fallback == "static" for item in canvas.validate_export("html"))


def test_optional_path_benchmark_preserves_default_workload():
    from benchmarks.animated_export import MEASURABLE_SCENES, measure_jitter
    from benchmarks.scenes import SCENES, build_scene

    assert "motion_path" not in SCENES and "motion_path" in MEASURABLE_SCENES
    assert measure_jitter("motion_path") is None
    deck = build_scene("motion_path")
    assert deck.sample(time=0.5).frames[0].to_image().getbbox()


def test_normalized_track_copy_invalidates_derived_path_metadata():
    original = NormalizedTrack(
        property="position", keyframes=(NormalizedKeyframe(time=0, value=(0, 0)),)
    )
    assert not original.is_path and not original.has_direction and original.path_times == (0,)
    keys = (NormalizedKeyframe(time=0, value=(0, 0)), NormalizedKeyframe(time=1, value=(0, 20)))
    changed = original.model_copy(update={"auto_orient": True, "keyframes": keys})
    assert changed.is_path and changed.has_direction and changed.path_times == (0, 1)
    assert not original.is_path and original.path_times == (0,)
