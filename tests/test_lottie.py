"""Public static-vector output and source-specific rejection before destination writes."""

import json
from pathlib import Path
from typing import cast

import jsonschema
import pytest
from examples.lottie_static import build_canvas
from quickthumb import AnimationSpec, Canvas, Deck, ExportPolicy, GifOptions, LottieOptions
from quickthumb.errors import RenderingError, ValidationError
from quickthumb.models import TextLayer


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
            Canvas(32, 32).text("한글", position=(0, 0), font="missing.ttf", id="text"),
            "content",
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
            Canvas(32, 32).group(
                [
                    {
                        "type": "shape",
                        "shape": "rectangle",
                        "width": 8,
                        "height": 8,
                        "color": "#000000",
                    }
                ]
            ),
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


def test_parent_frames_keep_local_coordinates_order_and_independent_opacity(tmp_path):
    from examples.lottie_parenting import build_canvas

    canvas = Canvas.from_json(build_canvas().to_json())
    output = tmp_path / "parenting.lot"
    result = canvas.export(output, animation=LottieOptions(fps=20, hold=0.5))
    payload = json.loads(output.read_text())
    jsonschema.validate(
        payload,
        json.loads((Path(__file__).parent / "fixtures/lottie/schema-1.0.1.json").read_text()),
    )
    by_name = {layer["nm"]: layer for layer in payload["layers"]}
    assert [layer["nm"] for layer in payload["layers"] if layer["ty"] == 4] == [
        "percent",
        "child",
        "panel",
    ]
    assert by_name["child"]["parent"] == by_name["panel [body frame]"]["ind"]
    assert by_name["middle"]["parent"] == by_name["root [body frame]"]["ind"]
    assert by_name["root [body frame]"]["parent"] == by_name["root"]["ind"]
    assert by_name["root"]["ty"] == 3 and "shapes" not in by_name["root"]
    assert by_name["root"]["ks"]["p"]["k"] == [64, 48, 0]
    assert by_name["percent"]["ks"]["p"]["k"] == [112, 84, 0]
    assert by_name["root"]["ks"]["o"]["k"] == by_name["panel"]["ks"]["o"]["k"] == 0
    assert by_name["child"]["ks"]["o"]["k"] == 75
    assert payload["assets"] == result.asset_manifest == []
    assert result.timing_metrics.frame_count == 30
    inspection = canvas.inspect_motion(target="lottie")
    child = next(layer for layer in inspection.slides[0].layers if layer.layer_id == "child")
    assert child.parent == "panel"
    assert (
        next(row for row in inspection.capabilities if row.feature == "parent").support == "partial"
    )


def test_parent_graph_errors_reach_lottie_before_destination_write(tmp_path):
    from quickthumb import NullLayer, ShapeLayer

    canvas = (
        Canvas(80, 60)
        .null(id="root")
        .shape("rectangle", (5, 5), 20, 10, "#FF0000", id="child", parent="root")
    )
    destination = tmp_path / "parenting.lot"
    destination.write_text("existing")
    root, child = canvas.layers
    assert isinstance(root, NullLayer) and isinstance(child, ShapeLayer)
    root.parent = "child"
    with pytest.raises(ValidationError) as caught:
        canvas.export(destination)
    assert caught.value.code == "parent_cycle"
    assert destination.read_text() == "existing"
    root.parent = None
    child.parent = "missing"
    with pytest.raises(ValidationError) as caught:
        canvas.export(destination)
    assert caught.value.code == "missing_parent"
    assert caught.value.details[0].path == "/layers/1/parent"
    assert caught.value.details[0].layer_id == "child"
    assert destination.read_text() == "existing"


def test_trim_keeps_fill_native_and_samples_cyclic_stroke_windows(tmp_path):
    from examples.lottie_trim import build_canvas

    canvas = Canvas.from_json(build_canvas().to_json())
    output = tmp_path / "trim.lot"
    receipt = canvas.export(output, animation=LottieOptions(fps=20, hold=0.5))
    payload = json.loads(output.read_text())
    schema = json.loads((Path(__file__).parent / "fixtures/lottie/schema-1.0.1.json").read_text())
    jsonschema.validate(payload, schema)
    stroke, fill, _transform = payload["layers"][0]["shapes"][0]["it"]
    assert [item["ty"] for item in fill["it"]] == ["sh", "fl", "tr"]
    modifier = stroke["it"][-2]
    assert modifier["ty"] == "tm" and modifier["m"] == 2
    # The non-grid delayed start and held boundary survive the same native clock.
    assert modifier["e"]["a"] == 1
    assert [key["t"] for key in modifier["e"]["k"]][:4] == [0, 1, 2, 2.5]
    assert modifier["e"]["k"][0]["s"] == [0]
    assert modifier["e"]["k"][-1]["s"] == [100]
    assert receipt.timing_metrics.frame_count == 33
    assert receipt.timing_metrics.duration == pytest.approx(1.65)
    assert payload["assets"] == []
    assert canvas.render_frame(0).getpixel((100, 75)) == (21, 154, 140, 96)
    assert canvas.inspect_motion().duration == pytest.approx(1.125)

    # A reversed interval is cyclic, not swapped by the native modifier.
    wrapped = Canvas(100, 60).path(
        "M10 20H90",
        (0, 0),
        100,
        60,
        None,
        stroke="#3757A0",
        stroke_width=4,
        trim_start=0.75,
        trim_end=0.25,
    )
    wrapped.export(output)
    native = json.loads(output.read_text())["layers"][0]["shapes"][0]["it"][0]["it"][-2]
    assert {name: native[name]["k"] for name in ("s", "e", "o")} == {"s": 0, "e": 50, "o": 270}
    pixels = wrapped.render_frame(0)
    gap, ink = pixels.getpixel((50, 20)), pixels.getpixel((15, 20))
    assert isinstance(gap, tuple) and gap[3] == 0
    assert isinstance(ink, tuple) and ink[3] > 245

    reduced = tmp_path / "reduced.lot"
    canvas.export(reduced, policy=ExportPolicy(reduced_motion=True))
    modifier = json.loads(reduced.read_text())["layers"][0]["shapes"][0]["it"][0]["it"][-2]
    assert modifier["e"] == {"a": 0, "k": 0}


def test_unrepresentable_trim_preserves_existing_destination(tmp_path):
    output = tmp_path / "trim.lot"
    output.write_text("existing")
    canvas = Canvas(100, 60).path(
        "M10 20H90",
        (0, 0),
        100,
        60,
        None,
        stroke="#3757A0",
        stroke_width=4,
        trim_start=0.5,
        trim_end=0.500001,
        id="too-thin",
    )
    assert canvas.validate_export("lottie")[0].support == "unsupported"
    with pytest.raises(RenderingError, match="precision") as caught:
        canvas.export(output)
    assert caught.value.details[0].layer_id == "too-thin"
    assert caught.value.details[0].path == "/layers/0/trim_start"
    assert output.read_text() == "existing"


def test_static_text_is_self_contained_outline_geometry(tmp_path):
    from examples.lottie_text import build_canvas

    canvas = Canvas.from_json(build_canvas().to_json())
    output = tmp_path / "text.lot"
    receipt = canvas.export(output, animation=LottieOptions(fps=30, hold=0.1))
    payload = json.loads(output.read_text())
    schema = json.loads((Path(__file__).parent / "fixtures/lottie/schema-1.0.1.json").read_text())
    jsonschema.validate(payload, schema)
    assert payload["assets"] == [] and "fonts" not in payload and "chars" not in payload
    assert [layer["nm"] for layer in payload["layers"]] == [
        "descenders",
        "spaced-holes",
        "default-face",
    ]
    for layer in payload["layers"]:
        assert layer["ty"] == 4 and layer["ks"]["p"]["k"] == [0, 0, 0]
        for glyph in layer["shapes"]:
            assert glyph["ty"] == "gr"
            assert all(shape["ty"] == "sh" for shape in glyph["it"][:-2])
            assert glyph["it"][-2]["r"] == 1  # Each glyph retains its own holes.
    assert len(payload["layers"][-1]["shapes"][0]["it"]) == 4  # O's two contours, fill, transform.
    assert receipt.timing_metrics.frame_count == 3
    assert all(row.support == "native" for row in receipt.capability_report)
    assert canvas.render_frame(0).getbbox() is not None

    # Two coincident opaque glyphs with opposite outer winding must not cancel.
    font_path = tmp_path / "opposite-winding.ttf"
    _opposite_winding_font(font_path)
    overlap = Canvas(80, 60).text(
        "AB",
        position=(20, 20),
        size=40,
        letter_spacing=-20,
        font=str(font_path),
        color="#FF0000",
        opacity=0.5,
    )
    overlap.export(output)
    native = json.loads(output.read_text())["layers"][0]
    jsonschema.validate(json.loads(output.read_text()), schema)
    assert len(native["shapes"]) == 2 and all(glyph["ty"] == "gr" for glyph in native["shapes"])
    assert native["ks"]["o"] == {"a": 0, "k": 50}
    assert all(glyph["it"][-2]["o"] == {"a": 0, "k": 100} for glyph in native["shapes"])
    pixel = overlap.render_frame(0).getpixel((28, 30))
    assert isinstance(pixel, tuple) and pixel[:3] == (255, 0, 0) and 127 <= pixel[3] <= 128


def _opposite_winding_font(path):
    """A real font whose A/B rectangles overlap but have opposite outer winding."""
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    builder = FontBuilder(1000, isTTF=True)
    builder.setupGlyphOrder([".notdef", "A", "B"])
    glyphs = {}
    points = [(0, 0), (500, 0), (500, 700), (0, 700)]
    for name in (".notdef", "A", "B"):
        pen = TTGlyphPen(None)
        if name != ".notdef":
            outline = points if name == "A" else list(reversed(points))
            pen.moveTo(outline[0])
            for point in outline[1:]:
                pen.lineTo(point)
            pen.closePath()
        glyphs[name] = pen.glyph()
    builder.setupCharacterMap({ord("A"): "A", ord("B"): "B"})
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics(dict.fromkeys(glyphs, (500, 0)))
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    builder.setupNameTable({"familyName": "Opposite", "styleName": "Regular"})
    builder.setupPost()
    builder.save(path)


@pytest.mark.parametrize(
    "options,field",
    [
        ({"content": "B\nO"}, "content"),
        ({"rotation": 15}, "rotation"),
        ({"color": "#159A8C80"}, "color"),
        ({"animation": AnimationSpec.fade()}, "animation"),
        ({"max_width": 50}, "max_width"),
        ({"font": "assets/fonts/RobotoFlex-Variable.ttf"}, "font"),
        ({"font": "https://invalid.example/font.ttf"}, "font"),
    ],
)
def test_unsupported_text_layout_is_actionable_before_write(tmp_path, options, field):
    canvas = Canvas(100, 60).text("BO", position=(5, 5), letter_spacing=1, id="label")
    layer = canvas.layers[0]
    assert isinstance(layer, TextLayer)
    canvas.layers = [layer.model_copy(update=options)]
    output = tmp_path / "text.lot"
    output.write_text("existing")
    rows = canvas.validate_export("lottie")
    assert rows[0].support == "unsupported" and f"/layers/0/{field}" in rows[0].message
    with pytest.raises(RenderingError) as caught:
        canvas.export(output, policy=ExportPolicy(unsupported_motion="static", reduced_motion=True))
    assert caught.value.details[0].layer_id == "label"
    assert caught.value.details[0].path == f"/layers/0/{field}"
    assert output.read_text() == "existing"


def test_missing_outline_dependency_keeps_shape_exports_usable(tmp_path, monkeypatch):
    import builtins

    original_import = builtins.__import__

    def unavailable(name, *args, **kwargs):
        if name.startswith("fontTools"):
            raise ImportError("fonttools unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", unavailable)
    output = tmp_path / "scene.lot"
    shape = Canvas(40, 30).shape("ellipse", (5, 5), 20, 15, "#159A8C")
    shape.export(output)
    previous = output.read_bytes()
    text = Canvas(40, 30).text("O", position=(5, 5), id="label")
    with pytest.raises(RenderingError, match=r"quickthumb\[lottie\]") as caught:
        text.export(output)
    assert caught.value.details[0].path == "/layers/0/font"
    assert caught.value.details[0].layer_id == "label"
    assert output.read_bytes() == previous


def test_missing_glyph_is_not_silently_replaced(tmp_path):
    from fontTools.ttLib import TTFont

    font_path = tmp_path / "missing-B.ttf"
    with TTFont("assets/fonts/Roboto-Regular.ttf") as face:
        for table in face["cmap"].tables:
            if table.isUnicode():
                table.cmap.pop(ord("B"), None)
        face.save(font_path)
    canvas = Canvas(80, 50).text("B", position=(5, 5), font=str(font_path), id="missing-glyph")
    output = tmp_path / "text.lot"
    with pytest.raises(RenderingError, match="no glyph") as caught:
        canvas.export(output)
    assert caught.value.details[0].path == "/layers/0/content"
    assert caught.value.details[0].layer_id == "missing-glyph"
    assert not output.exists()


def test_path_morph_retains_canonical_shapes_and_held_clock(tmp_path):
    from examples.lottie_morph import build_canvas
    from quickthumb._export_lottie import _path_contours
    from quickthumb.motion import LayerState, compile_timeline

    canvas = build_canvas()
    output = tmp_path / "morph.lot"
    receipt = canvas.export(output, animation=LottieOptions(fps=4, hold=0.5))
    payload = json.loads(output.read_text())
    jsonschema.validate(
        payload,
        json.loads((Path(__file__).parent / "fixtures/lottie/schema-1.0.1.json").read_text()),
    )
    layer = canvas.layers[0]
    from quickthumb.models import PathLayer

    assert isinstance(layer, PathLayer)
    assert isinstance(layer.animation, AnimationSpec)
    timeline = compile_timeline(layer.animation)
    shape = payload["layers"][0]["shapes"][0]["it"][0]
    assert shape["ks"]["a"] == 1
    times = [key["t"] / 4 for key in shape["ks"]["k"]]
    assert times == [0, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75]
    for key, time in zip(shape["ks"]["k"], times, strict=True):
        data = timeline.sample(time, LayerState()).path_morph or layer.d
        expected = _path_contours(layer.model_copy(update={"d": data}))[0]["ks"]["k"]
        assert key["s"] == [expected] and key["h"] == 1
    assert payload["op"] == 9
    assert receipt.capability_report[0].support == "partial"


def test_path_morph_rejects_clipped_keys_before_writing(tmp_path):
    from quickthumb import KeyframeSpec, PathMorphTrack, TimingSpec

    first, last = "M10 10H50V50H10Z", "M70 10H110V50H70Z"
    canvas = Canvas(100, 100).path(
        first,
        (0, 0),
        100,
        100,
        "#159A8C",
        animation=AnimationSpec.timeline(
            PathMorphTrack(
                keyframes=[
                    KeyframeSpec(time=0, value=first),
                    KeyframeSpec(time=1, value=last),
                ]
            ),
            timing=TimingSpec(duration=1),
        ),
    )
    assert canvas.validate_export("lottie")[0].support == "unsupported"
    output = tmp_path / "existing.lot"
    output.write_text("keep")
    with pytest.raises(RenderingError, match="viewport"):
        canvas.export(output)
    assert output.read_text() == "keep"


@pytest.mark.parametrize(
    "authored,key",
    [
        ("M10 10H40V40H10Z", "M10 10H40V40H10Z M60 60H90V90H60Z"),
        ("M10 10H40V40H10Z M60 60H90V90H60Z", "M10 10H40V40H10Z"),
    ],
)
def test_morph_contour_count_must_match_authored_source(tmp_path, authored, key):
    from quickthumb import KeyframeSpec, PathMorphTrack, TimingSpec

    canvas = Canvas(100, 100).path(
        authored,
        (0, 0),
        100,
        100,
        "#159A8C",
        animation=AnimationSpec.timeline(
            PathMorphTrack(
                keyframes=[
                    KeyframeSpec(time=0, value=key),
                    KeyframeSpec(time=1, value=key),
                ]
            ),
            timing=TimingSpec(start=0.25, duration=1),
        ),
    )
    assert canvas.validate_export("lottie")[0].support == "unsupported"
    output = tmp_path / "existing.lot"
    output.write_text("keep")
    with pytest.raises(RenderingError, match="contour count"):
        canvas.export(output)
    assert output.read_text() == "keep"


@pytest.mark.parametrize(
    "first,last,color",
    [
        ("M10 10H50V50H10Z M20 20H40V40H20Z", "M20 20H60V60H20Z M30 30H50V50H30Z", "#159A8C80"),
        ("M10 25Q40 10 70 25", "M10 45Q40 60 70 45", None),
    ],
)
def test_morph_native_geometry_repaints_canonical_frames(tmp_path, first, last, color):
    from PIL import ImageChops
    from quickthumb import KeyframeSpec, PathLayer, PathMorphTrack, TimingSpec

    canvas = Canvas(160, 140).path(
        first,
        (15, 10),
        120,
        120,
        color,
        view_box=(0, 0, 80, 80),
        stroke="#24433F",
        stroke_width=1.2,
        animation=AnimationSpec.timeline(
            PathMorphTrack(
                keyframes=[
                    KeyframeSpec(time=0, value=first),
                    KeyframeSpec(time=1, value=last),
                ]
            ),
            timing=TimingSpec(duration=1),
            easing="ease_in",
        ),
    )
    output = tmp_path / "morph.lot"
    canvas.export(output, animation=LottieOptions(fps=4, hold=0.5))
    payload = json.loads(output.read_text())
    jsonschema.validate(
        payload,
        json.loads((Path(__file__).parent / "fixtures/lottie/schema-1.0.1.json").read_text()),
    )
    paths = [item for item in payload["layers"][0]["shapes"][0]["it"] if item["ty"] == "sh"]
    for time in [0, 0.25, 0.5, 0.75, 1, 1.25]:
        commands = []
        for item in paths:
            prop = item["ks"]
            shape = (
                max((key for key in prop["k"] if key["t"] <= time * 4), key=lambda key: key["t"])[
                    "s"
                ][0]
                if prop["a"]
                else prop["k"]
            )
            vertices, incoming, outgoing = shape["v"], shape["i"], shape["o"]
            commands.append(f"M{vertices[0][0]} {vertices[0][1]}")
            for index in range(len(vertices) if shape["c"] else len(vertices) - 1):
                following = (index + 1) % len(vertices)
                a, b = vertices[index], vertices[following]
                commands.append(
                    f"C{a[0] + outgoing[index][0]} {a[1] + outgoing[index][1]} "
                    f"{b[0] + incoming[following][0]} {b[1] + incoming[following][1]} "
                    f"{b[0]} {b[1]}"
                )
            if shape["c"]:
                commands.append("Z")
        native = Canvas.from_json(canvas.to_json())
        source = canvas.layers[0]
        assert isinstance(source, PathLayer)
        native.layers = [source.model_copy(update={"d": " ".join(commands), "animation": None})]
        difference = ImageChops.difference(canvas.render_frame(time), native.render_frame(0))
        assert (
            sum(max(cast(tuple[int, ...], pixel)) > 16 for pixel in difference.get_flattened_data())
            / (160 * 140)
            < 0.02
        )


def test_morph_vertex_budget_is_shared_between_layers(tmp_path, monkeypatch):
    from quickthumb import KeyframeSpec, PathMorphTrack, TimingSpec, _sampling

    monkeypatch.setattr(_sampling, "_MAX_OBSERVATIONS", 30)
    animation = AnimationSpec.timeline(
        PathMorphTrack(
            keyframes=[
                KeyframeSpec(time=0, value="M10 10H40V40H10Z"),
                KeyframeSpec(time=1, value="M20 20H50V50H20Z"),
            ]
        ),
        timing=TimingSpec(duration=1),
    )
    canvas = Canvas(100, 100)
    for _ in range(2):
        canvas.path("M10 10H40V40H10Z", (0, 0), 100, 100, "#159A8C", animation=animation)
    output = tmp_path / "existing.lot"
    output.write_text("keep")
    with pytest.raises(RenderingError, match="total pose/vertex"):
        canvas.export(output, animation=LottieOptions(fps=4, hold=0.5))
    assert output.read_text() == "keep"
