"""Public static-vector output and source-specific rejection before destination writes."""

import json
from pathlib import Path

import jsonschema
import pytest
from examples.lottie_static import build_canvas
from quickthumb import AnimationSpec, Canvas, Deck, ExportPolicy, GifOptions, LottieOptions
from quickthumb.errors import RenderingError, ValidationError


def test_static_lottie_receipt_roundtrip_and_native_geometry(tmp_path):
    canvas = build_canvas().path(
        "M4 4H12V12H4Z",
        (220, 100),
        16,
        16,
        "#ABCDEF80",
        stroke="#3757A0",
        stroke_width=2,
        opacity=0.6,
        id="paint",
    )
    restored = Canvas.from_json(canvas.to_json())
    output = tmp_path / "scene.lot"
    result = restored.export(output, animation=LottieOptions(fps=30, hold=0.11))
    payload = json.loads(output.read_text())
    assert (payload["w"], payload["h"], payload["fr"], payload["op"]) == (240, 160, 30, 4)
    schema = json.loads((Path(__file__).parent / "fixtures/lottie/schema-1.0.1.json").read_text())
    jsonschema.validate(payload, schema)
    assert payload["assets"] == []
    assert [layer["nm"] for layer in payload["layers"]] == [
        "paint",
        "stroke",
        "hole",
        "triangle",
        "ellipse",
        "card",
        "layer:0",
    ]
    assert [shape["ty"] for shape in payload["layers"][0]["shapes"][0]["it"][:-1]] == [
        "sh",
        "st",
        "fl",
    ]
    assert payload["layers"][2]["shapes"][0]["it"][0]["ks"]["k"]["v"] == [
        [4, 4],
        [52, 4],
        [52, 44],
        [4, 44],
    ]
    assert payload["layers"][2]["shapes"][0]["it"][-2]["r"] == 2
    assert result.target == "lottie" and result.output_format == "lot"
    assert result.timing_metrics.frame_count == result.pixel_metrics.frame_count == 4
    assert result.timing_metrics.duration == pytest.approx(4 / 30)
    assert result.asset_manifest == result.fallback_diagnostics == []
    assert all(row.support == "native" for row in result.capability_report)
    assert restored.sample().frames[0].sha256 == canvas.sample().frames[0].sha256

    static_zero = tmp_path / "static-zero.lot"
    zero_receipt = restored.export(static_zero, animation=LottieOptions(fps=30, hold=0))
    zero_payload = json.loads(static_zero.read_text())
    jsonschema.validate(zero_payload, schema)
    assert zero_payload["op"] == zero_receipt.timing_metrics.frame_count == 1
    assert zero_receipt.timing_metrics.duration == pytest.approx(1 / 30)


@pytest.mark.parametrize(
    "canvas,field",
    [
        (
            Canvas(32, 32).custom(
                lambda *_: (_ for _ in ()).throw(AssertionError("callback executed"))
            ),
            "type",
        ),
        (
            Canvas(32, 32).text("unsupported", position=(0, 0), font="missing.ttf", id="text"),
            "type",
        ),
        (
            Canvas(32, 32).shape(
                "rectangle", (0, 0), 8, 8, "#000000", id="moving", animation=AnimationSpec.fade()
            ),
            "animation",
        ),
        (
            Canvas(32, 32).path(
                "M2 2L10 10", (0, 0), 20, 20, None, stroke="#000000", dash_array=(2, 2), id="dashed"
            ),
            "d",
        ),
        (Canvas(32, 32).path("M-1 0H10V10Z", (0, 0), 20, 20, id="clipped"), "d"),
        (
            Canvas(32, 32).path("M2 20C-20 -30 30 -30 30 20", (0, 0), 32, 32, id="curve-clipped"),
            "d",
        ),
        (
            Canvas(32, 32).path(
                "M100000000000010 100000000000010H100000000000090V100000000000090Z",
                (0, 0),
                32,
                32,
                view_box=(1e14, 1e14, 100, 100),
                id="precision",
            ),
            "d",
        ),
        (
            Canvas(32, 32).path(
                "M10 10L10 10", (0, 0), 20, 20, None, stroke="#000000", line_cap="round", id="dot"
            ),
            "d",
        ),
        (
            Canvas(32, 32)
            .null(id="parent")
            .shape("rectangle", (0, 0), 8, 8, "#000000", parent="parent"),
            "type",
        ),
    ],
)
def test_unsupported_source_reports_location_and_preserves_destination(tmp_path, canvas, field):
    destination = tmp_path / "scene.lot"
    destination.write_text("existing")
    rows = canvas.validate_export("lottie")
    assert rows[0].support == "unsupported"
    assert f"/layers/0/{field}" in rows[0].message
    with pytest.raises(RenderingError) as caught:
        canvas.export(destination, policy=ExportPolicy(unsupported_motion="static"))
    assert caught.value.details[0].path == f"/layers/0/{field}"
    assert caught.value.details[0].layer_id is not None
    assert destination.read_text() == "existing"


def test_lottie_route_rejects_wrong_options_and_deck_before_writes(tmp_path):
    output = tmp_path / "scene.lot"
    canvas = Canvas(8, 8)
    with pytest.raises(ValidationError, match="LottieOptions"):
        canvas.export(output, animation=GifOptions())
    with pytest.raises(RenderingError, match="raster output"):
        canvas.export(output, format="PNG")
    with pytest.raises(RenderingError, match="single Canvas"):
        Deck().slide(canvas).export(output)
    assert not output.exists()


def test_curved_paths_keep_relative_tangents_closed_seams_and_no_raster_assets(tmp_path):
    from examples.lottie_paths import build_canvas

    canvas = Canvas.from_json(build_canvas().to_json())
    destination = tmp_path / "curves.lot"
    result = canvas.export(destination)
    payload = json.loads(destination.read_text())
    schema = json.loads((Path(__file__).parent / "fixtures/lottie/schema-1.0.1.json").read_text())
    jsonschema.validate(payload, schema)
    by_id = {layer["nm"]: layer for layer in payload["layers"]}
    quadratic = by_id["quadratic"]["shapes"][0]["it"][0]["ks"]["k"]
    # Q(40,0) from (8,40) becomes exact relative cubic tangents.
    assert quadratic["o"][0] == pytest.approx([64 / 3, -80 / 3])
    assert quadratic["i"][1] == pytest.approx([-64 / 3, -80 / 3])
    closed = by_id["closed"]["shapes"][0]["it"][0]["ks"]["k"]
    assert closed["v"] == [[12, 32], [52, 32]]
    assert closed["i"][0] == [0, 28]
    assert closed["o"][0] == [0, -28]
    assert closed["c"] is True
    arc = by_id["arc-hole"]["shapes"][0]["it"][0]["ks"]["k"]
    assert arc["v"][0] == [12, 40] and arc["c"] is True
    assert any(handle != [0, 0] for handle in arc["o"])
    assert payload["assets"] == result.asset_manifest == []
    assert all(row.support == "native" for row in result.capability_report)


def test_pose_motion_samples_boundaries_composition_and_final_hold(tmp_path):
    from examples.lottie_motion import build_canvas

    canvas = Canvas.from_json(build_canvas().to_json())
    output = tmp_path / "motion.lot"
    receipt = canvas.export(output, animation=LottieOptions(fps=20, hold=0.5))
    payload = json.loads(output.read_text())
    jsonschema.validate(
        payload,
        json.loads((Path(__file__).parent / "fixtures/lottie/schema-1.0.1.json").read_text()),
    )
    path = next(layer for layer in payload["layers"] if layer["nm"] == "path")
    opacity = {key["t"]: key["s"][0] for key in path["ks"]["o"]["k"]}
    assert opacity[2.0] == 60  # Authored alpha before the event starts at frame2.5.
    assert opacity[2.5] == 30
    assert opacity[12.5] == 60  # Exact held-key boundary, independent of the fps grid.
    assert opacity[22.5] == pytest.approx(45)
    shape = next(layer for layer in payload["layers"] if layer["nm"] == "shape")
    shape_opacity = {key["t"]: key["s"][0] for key in shape["ks"]["o"]["k"]}
    assert shape_opacity[2.5] == pytest.approx(49.8779296875)  # Another layer's authored cut.
    assert receipt.timing_metrics.frame_count == payload["op"] == 33
    assert receipt.timing_metrics.duration == 1.65
    assert path["ks"]["p"]["k"][-1]["s"] == [45, 115, 0]
    assert path["ks"]["r"]["k"][-1]["s"] == [5]
    assert all(row.support == "partial" for row in receipt.capability_report)
    inspection = canvas.inspect_motion(target="lottie", fps=20)
    assert inspection.duration == 1.125
    assert all(row.support == "partial" for row in inspection.capabilities)
    assert receipt.asset_manifest == []

    no_hold_path = tmp_path / "motion-zero.lot"
    no_hold = canvas.export(no_hold_path, animation=LottieOptions(fps=20, hold=0))
    no_hold_payload = json.loads(no_hold_path.read_text())
    jsonschema.validate(
        no_hold_payload,
        json.loads((Path(__file__).parent / "fixtures/lottie/schema-1.0.1.json").read_text()),
    )
    assert no_hold_payload["op"] == no_hold.timing_metrics.frame_count == 23
    assert no_hold.timing_metrics.duration == 1.15
    assert (
        next(layer for layer in no_hold_payload["layers"] if layer["nm"] == "path")["ks"]
        == path["ks"]
    )

    reduced = canvas.export(
        tmp_path / "reduced.lot",
        animation=LottieOptions(fps=20, hold=0.5),
        policy=ExportPolicy(reduced_motion=True),
    )
    reduced_payload = json.loads((tmp_path / "reduced.lot").read_text())
    assert all(
        property["a"] == 0
        for layer in reduced_payload["layers"]
        for property in layer["ks"].values()
    )
    assert reduced.timing_metrics.frame_count == 10 and reduced.timing_metrics.duration == 0.5
    assert all(row.support == "native" for row in reduced.capability_report)
    assert canvas.inspect_motion(target="lottie").duration == 1.125


def test_pose_plan_limit_and_clipped_source_preserve_existing_output(tmp_path):
    from quickthumb import KeyframeSpec, PositionTrack, TimingSpec

    output = tmp_path / "existing.lot"
    output.write_text("existing")
    for position, duration, message in [((-1, 5), 1, "fit inside"), ((5, 5), 10000, "100000 pose")]:
        canvas = Canvas(50, 40).shape(
            "rectangle",
            position,
            20,
            20,
            "#159A8C",
            id="moving",
            animation=AnimationSpec.timeline(
                PositionTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value=(0, 0)),
                        KeyframeSpec(time=duration, value=(10, 0)),
                    ]
                ),
                timing=TimingSpec(duration=duration),
            ),
        )
        with pytest.raises(RenderingError, match=message) as caught:
            canvas.export(output)
        assert caught.value.details[0].layer_id == "moving"
        assert caught.value.details[0].path is not None
        assert caught.value.details[0].path.startswith("/layers/0/")
        assert output.read_text() == "existing"
