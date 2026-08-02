"""Black-box integration coverage for the evidence-led investor deck example."""

import json


def test_investor_deck_exports_a_complete_investment_narrative(tmp_path):
    """The example exports ten readable slides with notes and stable formats."""
    # given: the public investor deck composition
    from examples.investor_deck import deck

    html_path = tmp_path / "investor.html"
    pptx_path = tmp_path / "investor.pptx"

    # when: consumers serialize, diagnose, and export the finished deck
    payload = json.loads(deck.to_json())
    findings = deck.diagnose()
    deck.render(str(html_path))
    deck.render(str(pptx_path))

    # then: the deck covers the full story and has no structural legibility issue
    assert len(payload["slides"]) == 10
    assert all(slide["notes"] for slide in payload["slides"])
    assert all(
        finding.code in {"edge-crowding", "layer-overlap", "low-contrast", "transition-repetition"}
        and finding.severity == "warning"
        for finding in findings
    )
    assert html_path.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert pptx_path.read_bytes().startswith(b"PK")
