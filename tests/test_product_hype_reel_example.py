"""Black-box integration coverage for the product hype reel example."""

import json


def test_product_hype_reel_meets_layout_and_pacing_contract():
    """The complete reel stays legible and gives every scene six beats to read."""
    # given: the public example composition
    from examples.product_hype_reel import BEAT, build_deck

    deck = build_deck()

    # when: the public serialization and diagnostics describe the finished reel
    slides = json.loads(deck.to_json())["slides"]
    scene_durations = [
        slide["transition"]["advance_after"]
        + (0 if slide["transition"]["effect"] == "cut" else slide["transition"]["duration"])
        for slide in slides
    ]
    findings = deck.diagnose()

    # then: every scene has reading room and no layout or legibility issue remains
    assert len(deck) == 8
    assert scene_durations == [6 * BEAT] * 8
    assert sum(scene_durations) == 22.5
    assert findings == []
