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
    assert [shape["ty"] for shape in payload["layers"][0]["shapes"]] == ["sh", "st", "fl"]
    assert payload["layers"][2]["shapes"][0]["ks"]["k"]["v"] == [[4, 4], [52, 4], [52, 44], [4, 44]]
    assert payload["layers"][2]["shapes"][-1]["r"] == 2
    assert result.target == "lottie" and result.output_format == "lot"
    assert result.timing_metrics.frame_count == result.pixel_metrics.frame_count == 4
    assert result.timing_metrics.duration == pytest.approx(4 / 30)
    assert result.asset_manifest == result.fallback_diagnostics == []
    assert all(row.support == "native" for row in result.capability_report)
    assert restored.sample().frames[0].sha256 == canvas.sample().frames[0].sha256


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
        (Canvas(32, 32).path("M0 0Q5 5 10 0", (0, 0), 20, 20, id="curve"), "d"),
        (Canvas(32, 32).path("M-1 0H10V10Z", (0, 0), 20, 20, id="clipped"), "d"),
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
