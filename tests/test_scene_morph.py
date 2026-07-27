import json
from io import BytesIO
from typing import Literal, cast
from zipfile import ZipFile

import pytest
from PIL import Image
from quickthumb import AnimationSpec, Canvas, Deck, KeyframeSpec, Morph, PositionTrack
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


def test_should_resolve_percentage_positions_and_fade_unkeyed_layers():
    # Given scenes with percentage-positioned shared content and unkeyed layers
    source = Canvas(200, 100).text("shared", position=("10%", "20%"), motion_key="hero")
    source.text("old-only", position=(0, 0))
    target = Canvas(400, 200).text("shared", position=("50%", "60%"), motion_key="hero")
    target.text("new-only", position=(0, 0))
    deck = Deck(slides=[source, target])

    # When sampling halfway through the transition
    states = deck.sample_morph(0, 1, 0.5)

    # Then percentages resolve in each scene's coordinate space and unkeyed layers fade
    hero = next(item for item in states if item.motion_key == "hero")
    unkeyed = [item for item in states if item.motion_key is None]
    assert hero.state.position == (110.0, 70.0)
    assert len(unkeyed) == 2
    assert {item.behavior for item in unkeyed} == {"enter", "exit"}


def test_should_interpolate_colors_for_matched_shape_layers():
    # Given a keyed shape whose color changes between scenes
    source = Canvas(100, 100).shape("rectangle", (0, 0), 20, 20, "#FF0000", motion_key="color-box")
    target = Canvas(100, 100).shape(
        "rectangle", (20, 20), 20, 20, "#0000FF", motion_key="color-box"
    )

    # When sampling halfway through the Morph
    state = Deck(slides=[source, target]).sample_morph(0, 1, 0.5)[0]

    # Then the existing color interpolation contract is reused
    assert state.state.color == "#800080"


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
    source = Canvas(320, 180).text("old", position=(0, 0), id="source_title", motion_key="hero")
    target = Canvas(320, 180).text("new", position=(40, 20), id="target_title", motion_key="hero")
    deck = Deck(slides=[source, target], transition=Morph())

    # When document exporters compile the transition
    html = deck.to_html()
    pptx = deck.to_pptx()
    with ZipFile(BytesIO(pptx)) as archive:
        slide_xml = b"".join(
            archive.read(name) for name in archive.namelist() if name.startswith("ppt/slides/slide")
        )

    # Then HTML carries per-element identities while PPTX keeps its safe fallback
    assert "data-qt-dur=" in html
    assert 'data-qt-transition="qt-t1' in html
    assert 'data-qt-morph="1"' in html
    assert 'data-qt-motion-key="hero"' in html
    assert "function morphElements" in html
    assert b"p14:morph" in slide_xml
    assert b"!!qt-morph-hero-0" in slide_xml
    assert b"<p:fade/>" in slide_xml


def test_should_render_a_keyed_shape_at_an_intermediate_morph_position():
    # Given two slides with the same keyed shape at different positions
    source = Canvas(160, 100).shape("rectangle", (0, 40), 20, 20, "#FF0000", motion_key="box")
    target = Canvas(160, 100).shape("rectangle", (100, 40), 20, 20, "#FF0000", motion_key="box")
    deck = Deck(slides=[source, target], transition=Morph(duration=1))

    # When the public animated export is sampled at a fixed frame rate
    image: Image.Image = Image.open(BytesIO(deck.to_gif(fps=4, slide_duration=0.1)))
    red_bounds = []
    for index in range(int(getattr(image, "n_frames", 1))):
        image.seek(index)
        frame = image.convert("RGBA")
        points = [
            (x, y)
            for y in range(frame.height)
            for x in range(frame.width)
            if (pixel := cast(tuple[int, int, int, int], frame.getpixel((x, y))))[0] > 200
            and pixel[1] < 50
            and pixel[2] < 50
            and pixel[3] > 0
        ]
        if points:
            red_bounds.append((min(x for x, _ in points), max(x for x, _ in points)))

    # Then at least one rendered frame contains the shared element in flight
    assert any(0 < left < 80 and 20 < right < 120 for left, right in red_bounds)


@pytest.mark.parametrize("field", ["id", "motion_key"])
def test_should_reject_invalid_layer_identity(field: Literal["id", "motion_key"]):
    # Given an identity that cannot be stable or safely serialized
    # When a public Canvas builder receives it, then validation is explicit
    with pytest.raises(ValidationError, match="identity values"):
        if field == "id":
            Canvas(100, 100).text("bad", position=(0, 0), id="not valid")
        else:
            Canvas(100, 100).text("bad", position=(0, 0), motion_key="not valid")


def test_should_reject_duplicate_authored_layer_ids_without_mutating_the_canvas():
    # Given a canvas with one authored local id
    canvas = Canvas(100, 100).text("first", position=(0, 0), id="title")

    # When a second layer reuses that id
    with pytest.raises(ValidationError, match="duplicate layer id"):
        canvas.text("second", position=(0, 0), id="title")

    # Then the rejected layer is not appended
    assert len(canvas.layers) == 1


def test_should_keep_canvas_layers_read_only_through_the_public_collection():
    # Given a canvas with one public layer
    canvas = Canvas(100, 100).text("title", position=(0, 0))

    # When a caller mutates the returned layer collection
    layers = canvas.layers
    layers.clear()

    # Then the canvas itself remains unchanged
    assert len(canvas.layers) == 1

    # When a caller replaces the collection and later mutates its input list
    replacement = [canvas.layers[0]]
    canvas.layers = replacement
    replacement.clear()

    # Then the assigned canvas collection remains isolated as well
    assert len(canvas.layers) == 1


def test_should_sample_layer_timeline_at_the_morph_scene_time():
    # Given a keyed source layer with a canonical position timeline
    animation = AnimationSpec(
        tracks=[
            PositionTrack(
                keyframes=[
                    KeyframeSpec(time=0, value=(0, 0)),
                    KeyframeSpec(time=1, value=(20, 0)),
                ]
            )
        ]
    )
    source = Canvas(100, 100).shape(
        "rectangle", (0, 0), 10, 10, "#FF0000", motion_key="hero", animation=animation
    )
    target = Canvas(100, 100).shape("rectangle", (100, 0), 10, 10, "#FF0000", motion_key="hero")

    # When Morph is sampled halfway through a two-second transition
    state = Deck(slides=[source, target]).sample_morph(0, 1, 0.5, duration=2)[0]

    # Then the source timeline is sampled at its settled transition time before interpolation
    assert state.state.position == (60.0, 0.0)
