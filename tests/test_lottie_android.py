"""Android-compatible wire order and canonical global trim across contours."""

import json

import pytest
from quickthumb import AnimationSpec, Canvas, KeyframeSpec, LottieOptions, TimingSpec, TrimEndTrack
from quickthumb._document import canonical_json
from quickthumb.errors import RenderingError


def test_lottie_type_precedes_geometry_without_changing_document_json(tmp_path):
    from examples.lottie_static import build_canvas

    canvas = build_canvas()
    spec = canvas.to_json()
    first, second = tmp_path / "first.lot", tmp_path / "second.lot"
    canvas.export(first)
    Canvas.from_json(spec).export(second)
    assert first.read_bytes() == second.read_bytes()
    assert canvas.to_json() == spec
    assert canonical_json({"ty": "sh", "ks": {"k": 1}}) == '{"ks":{"k":1},"ty":"sh"}'
    objects = []

    def ordered(pairs):
        value = dict(pairs)
        if "ty" in value:
            objects.append(value)
            assert pairs[0][0] == "ty"
        return value

    json.loads(first.read_text(), object_pairs_hook=ordered)
    assert len(objects) > 10


@pytest.mark.parametrize(
    "start,end,offset,expected",
    [
        (0.5, 0.9, 0, [(37.5, 225), (50, 0)]),
        (0.9, 0.2, 0, [(25, 0), (50, 180)]),
        (0.3, 0.2, 0, [(87.5, 135), (100, 0)]),
        (0.5, 0.5, 0, [(0, 0), (0, 0)]),
        (0, 0.2, -0.1, [(12.5, 0), (50, 180)]),
    ],
)
def test_global_trim_maps_unequal_contours_without_repainting(
    tmp_path, start, end, offset, expected
):
    output = tmp_path / "trim.lot"
    (
        Canvas(100, 60)
        .path(
            "M10 10H90 M10 30H30",
            (0, 0),
            100,
            60,
            None,
            stroke="#3757A080",
            stroke_width=2,
            trim_start=start,
            trim_end=end,
            trim_offset=offset,
        )
        .export(output)
    )
    stroke = json.loads(output.read_text())["layers"][0]["shapes"][0]["it"][0]["it"]
    assert [item["ty"] for item in stroke] == ["gr", "gr", "st", "tr"]
    for group, (extent, offset_degrees) in zip(stroke[:2], expected, strict=True):
        assert [item["ty"] for item in group["it"]] == ["sh", "tm", "tr"]
        trim = group["it"][1]
        assert trim["m"] == 1
        assert trim["s"]["k"] == 0
        assert trim["e"]["k"] == pytest.approx(extent)
        assert trim["o"]["k"] == pytest.approx(offset_degrees)


def test_multi_contour_trim_keeps_sample_budget_and_destination(tmp_path):
    output = tmp_path / "too-large.lot"
    output.write_text("existing")
    canvas = Canvas(32, 32).path(
        "M5 5L6 5 " * 1000,
        (0, 0),
        32,
        32,
        None,
        stroke="#3757A0",
        stroke_width=1,
        animation=AnimationSpec.timeline(
            TrimEndTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=1)]),
            timing=TimingSpec(duration=1),
        ),
    )
    with pytest.raises(RenderingError, match="trim samples"):
        canvas.export(output, animation=LottieOptions(fps=120))
    assert output.read_text() == "existing"


def test_morph_updates_global_length_weights_and_preserves_shared_paint(tmp_path):
    from examples.lottie_trim_multi import build_canvas

    canvas = build_canvas()
    output = tmp_path / "morph-trim.lot"
    canvas.export(output)
    layers = {layer["nm"]: layer for layer in json.loads(output.read_text())["layers"]}
    stroke = layers["morph"]["shapes"][0]["it"][0]["it"]
    outer, inner = [group["it"][1] for group in stroke[:2]]
    # Outer/inner perimeters change from 160/60 to 150/54; keep the authored
    # global 0.8→0.4 window, rather than reusing the initial contour weights.
    assert outer["e"]["k"][0]["s"] == pytest.approx([55])
    assert outer["e"]["k"][-1]["s"] == pytest.approx([54.4])
    assert inner["e"]["k"][0]["s"] == pytest.approx([100 * 44 / 60])
    assert inner["e"]["k"][-1]["s"] == pytest.approx([100 * 40.8 / 54])
    assert inner["o"]["k"][0]["s"] == pytest.approx([96])
    assert inner["o"]["k"][-1]["s"] == pytest.approx([88])
    pixel = canvas.render_frame(0).getpixel((220, 360))
    assert isinstance(pixel, tuple)
    assert pixel[3] == 128


def test_full_animated_trim_keeps_complete_curved_contours(tmp_path):
    output = tmp_path / "full.lot"
    Canvas(120, 80).path(
        "M10 20Q30 5 50 30 M60 30Q75 65 100 20",
        (0, 0),
        120,
        80,
        None,
        stroke="#3757A0",
        stroke_width=2,
        animation=AnimationSpec.timeline(
            TrimEndTrack(keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=1, value=1)]),
            timing=TimingSpec(duration=1),
        ),
    ).export(output)
    stroke = json.loads(output.read_text())["layers"][0]["shapes"][0]["it"][0]["it"]
    for group in stroke[:2]:
        trim = group["it"][1]
        assert {name: trim[name]["k"] for name in ("s", "e", "o")} == {"s": 0, "e": 100, "o": 0}
