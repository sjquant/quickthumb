"""Black-box integration coverage for the product hype reel example."""

import json
from pathlib import Path
from typing import cast


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


def test_product_hype_reel_exports_each_supported_file_with_valid_audio_options(
    monkeypatch, tmp_path
):
    """The example only supplies a soundtrack to containers that can carry audio."""
    # given
    import examples.product_hype_reel as reel
    from quickthumb import Deck

    calls: list[tuple[str, bool]] = []

    class RecordingDeck:
        """Record the example's public export calls without encoding the full reel."""

        def to_gif(self, **kwargs):
            return b"GIF89a"

        def render(self, output_path, **kwargs):
            calls.append((Path(output_path).suffix, "soundtrack" in kwargs))
            return [str(output_path)]

        def __len__(self):
            return 8

    for name, suffix in {
        "OUT_GIF": ".gif",
        "OUT_MP4": ".mp4",
        "OUT_WEBM": ".webm",
        "OUT_PPTX": ".pptx",
        "OUT_HTML": ".html",
    }.items():
        monkeypatch.setattr(reel, name, tmp_path / f"reel{suffix}", raising=False)

    # when
    reel.export_reel(cast(Deck, RecordingDeck()))

    # then
    assert (tmp_path / "reel.gif").read_bytes() == b"GIF89a"
    assert calls == [
        (".pptx", False),
        (".html", False),
        (".mp4", True),
        (".webm", True),
    ]
