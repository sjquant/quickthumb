"""Behavioral specifications for the production-style VideoLayer example."""

import json


def test_ordinary_moments_builds_a_two_minute_horizontal_video_story():
    """Given the public example, when serialized, then its story contract is preserved."""
    # Given: the public, locally reproducible example deck
    from examples.ordinary_moments import SCENE_DURATION, build_deck

    deck = build_deck()

    # When: the public composition is serialized
    payload = json.loads(deck.to_json())
    layers = [layer for slide in payload["slides"] for layer in slide["layers"]]

    # Then: it is a horizontal, eight-scene VideoLayer film of about two minutes
    assert payload["width"] == 1280
    assert payload["height"] == 720
    assert len(payload["slides"]) == 8
    assert (
        sum(
            slide["transition"]["advance_after"]
            + (0 if slide["transition"]["effect"] == "cut" else slide["transition"]["duration"])
            for slide in payload["slides"]
        )
        == 112.0
    )
    assert sum(layer["type"] == "video" for layer in layers) == 8
    assert all(layer["duration"] == SCENE_DURATION for layer in layers if layer["type"] == "video")


def test_ordinary_moments_keeps_caption_treatment_and_fallback_contracts_public():
    """Given the example, when inspected for export, then captions and fallbacks are explicit."""
    # Given: the public production example
    from examples.ordinary_moments import build_deck

    deck = build_deck()

    # When: public JSON and export capability diagnostics are inspected
    payload = deck.to_json()
    diagnostics = deck.validate_export("pptx")

    # Then: caption styling survives and document fallback is declared
    captions = [
        caption
        for slide in json.loads(payload)["slides"]
        for layer in slide["layers"]
        if layer["type"] == "video"
        for caption in layer["captions"]
    ]
    assert any(caption["background_opacity"] == 0.78 for caption in captions)
    assert any(caption["border_radius"] == 6 for caption in captions)
    assert any(
        item.feature == "video_layer" and item.fallback == "rasterize" for item in diagnostics
    )
