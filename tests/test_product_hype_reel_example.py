"""Black-box integration coverage for the product hype reel example."""


def test_product_hype_reel_passes_all_layout_diagnostics():
    """The complete eight-scene reel stays legible and inside Reels-safe bounds."""
    # given: the public example composition
    from examples.product_hype_reel import build_deck

    deck = build_deck()

    # when: the same diagnostics used by the runnable example inspect the deck
    findings = deck.diagnose()

    # then: every scene is present and no layout or legibility issue remains
    assert len(deck) == 8
    assert findings == []
