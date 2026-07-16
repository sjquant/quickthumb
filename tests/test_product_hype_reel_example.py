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
    """The example uses namespaced GIF options and audio only for video containers."""
    # given
    import examples.product_hype_reel as reel
    from quickthumb import Deck, GifOptions, VideoOptions

    calls: list[tuple[str, bool, bool]] = []
    gif_options: list[GifOptions] = []
    video_options: list[VideoOptions] = []

    class RecordingDeck:
        """Record the example's public export calls without encoding the full reel."""

        def render(self, output_path, **kwargs):
            suffix = Path(output_path).suffix
            calls.append((suffix, "soundtrack" in kwargs, "animation" in kwargs))
            if suffix == ".gif":
                gif_options.append(kwargs["animation"])
                Path(output_path).write_bytes(b"GIF89a")
            if suffix in (".mp4", ".webm"):
                video_options.append(kwargs["animation"])
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
        (".gif", False, True),
        (".pptx", False, False),
        (".html", False, False),
        (".mp4", False, True),
        (".webm", False, True),
    ]
    assert gif_options[0].fps == 8
    assert gif_options[0].max_size == (540, 960)
    assert gif_options[0].colors == 128
    assert all(
        options.soundtrack is not None and options.soundtrack.loop for options in video_options
    )
