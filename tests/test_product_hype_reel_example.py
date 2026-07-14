"""Black-box integration coverage for the product hype reel example."""

import json


def test_product_hype_reel_meets_layout_and_pacing_contract():
    """The complete reel stays legible and gives every scene narration room."""
    # given: the public example composition
    from examples.product_hype_reel import BEAT, SCENE_DURATION, build_deck

    deck = build_deck()

    # when: the public serialization and diagnostics describe the finished reel
    slides = json.loads(deck.to_json())["slides"]
    scene_durations = [
        slide["transition"]["advance_after"]
        + (0 if slide["transition"]["effect"] == "cut" else slide["transition"]["duration"])
        for slide in slides
    ]
    first_animation_delays = [
        next(layer["animation"]["delay"] for layer in slide["layers"] if layer.get("animation"))
        for slide in slides
    ]
    transition_effects = [slide["transition"]["effect"] for slide in slides]
    findings = deck.diagnose()

    # then: every scene has reading room and no layout or legibility issue remains
    assert len(deck) == 8
    assert scene_durations == [SCENE_DURATION] * 8
    assert sum(scene_durations) == 36.0
    assert first_animation_delays == [BEAT / 2] * 8
    assert transition_effects == ["cut", "wipe", "push", "push", "push", "push", "fade", "zoom"]
    assert findings == []
