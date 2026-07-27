import json
from io import BytesIO
from zipfile import ZipFile

import pytest
from quickthumb import Canvas, Deck, Morph
from quickthumb.errors import ValidationError


def scene(*layers):
    canvas = Canvas(320, 180)
    for content, position, key in layers:
        canvas.text(content, position=position, motion_key=key)
    return canvas


def test_should_round_trip_layer_identity_and_morph_transition():
    # Given a layer with an authored local id and cross-scene key
    canvas = Canvas(320, 180).text("title", position=(0, 0), id="title", motion_key="hero")
    deck = Deck(slides=[canvas, Canvas(320, 180)], transition=Morph(duration=0.8))

    # When the public models are serialized and restored
    restored = Canvas.from_json(canvas.to_json())
    payload = json.loads(canvas.to_json())

    # Then identity and transition contracts survive unchanged
    assert restored.layers[0].id == "title"
    assert restored.layers[0].motion_key == "hero"
    assert deck.default_transition.effect == "morph"
    assert payload["layers"][0]["motion_key"] == "hero"


def test_should_interpolate_a_unique_match_and_define_enter_exit_states():
    # Given source and target scenes with one shared and two one-sided layers
    source = scene(("old", (0, 0), "hero"), ("gone", (10, 10), "gone"))
    target = scene(("new", (100, 40), "hero"), ("new", (20, 20), "new"))
    deck = Deck(slides=[source, target])

    # When the morph is sampled halfway through
    states = {item.motion_key: item for item in deck.sample_morph(0, 1, 0.5)}

    # Then the shared layer moves deterministically and one-sided layers fade
    assert deck.match_layers(0, 1) == (("layer:0", "layer:0", "hero"),)
    assert states["hero"].state.position == (50.0, 20.0)
    assert states["gone"].behavior == "exit"
    assert states["gone"].state.opacity == 0.5
    assert states["new"].behavior == "enter"
    assert states["new"].state.opacity == 0.5


def test_should_ignore_duplicate_motion_keys_and_crossfade_charts():
    # Given duplicate source identity and a chart identity
    source = scene(("one", (0, 0), "duplicate"), ("two", (10, 10), "duplicate"))
    target = scene(("chart label", (20, 20), "duplicate"))
    target.chart(
        {"type": "bar", "data": [1, 2]},
        position=(10, 10),
        width=80,
        height=60,
        motion_key="chart",
    )
    source.chart(
        {"type": "bar", "data": [2, 3]},
        position=(0, 0),
        width=80,
        height=60,
        motion_key="chart",
    )
    deck = Deck(slides=[source, target])

    # When matching and sampling the transition
    assert deck.match_layers(0, 1) == (("layer:2", "layer:1", "chart"),)
    chart = next(item for item in deck.sample_morph(0, 1, 0.5) if item.motion_key == "chart")

    # Then duplicate identity is safely ignored and chart motion uses cross-fade
    assert chart.behavior == "crossfade"
    assert all(item.motion_key != "duplicate" for item in deck.sample_morph(0, 1, 0.5))


def test_should_fallback_morph_to_fade_for_document_exporters():
    # Given a Morph deck containing ordinary keyed text layers
    source = scene(("old", (0, 0), "hero"))
    target = scene(("new", (40, 20), "hero"))
    deck = Deck(slides=[source, target], transition=Morph())

    # When document exporters compile the transition
    html = deck.to_html()
    pptx = deck.to_pptx()
    slide_xml = b"".join(
        ZipFile(BytesIO(pptx)).read(name)
        for name in ZipFile(BytesIO(pptx)).namelist()
        if name.startswith("ppt/slides/slide")
    )

    # Then both retain the transition timing while using the safe fade fallback
    assert "data-qt-dur=" in html
    assert "data-qt-transition=\"qt-t1" in html
    assert "morph" not in html.lower()
    assert b"<p:fade/>" in slide_xml


@pytest.mark.parametrize("field", ["id", "motion_key"])
def test_should_reject_invalid_layer_identity(field):
    # Given an identity that cannot be stable or safely serialized
    kwargs = {field: "not valid"}

    # When a public Canvas builder receives it, then validation is explicit
    with pytest.raises(ValidationError, match="identity values"):
        Canvas(100, 100).text("bad", position=(0, 0), **kwargs)
