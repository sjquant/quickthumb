"""Black-box integration coverage for the product hype reel example."""

import json
import tempfile
import wave
from pathlib import Path
from typing import cast


def test_product_hype_reel_meets_layout_and_pacing_contract():
    """The complete reel stays legible and gives every scene narration room."""
    # given: the public example composition
    from examples.product_hype_reel import BEAT, SCENE_DURATIONS, VOICEOVERS, build_deck

    deck = build_deck()
    voiceover_durations = []
    for voiceover_path in VOICEOVERS:
        with wave.open(str(voiceover_path), "rb") as voiceover:
            voiceover_durations.append(voiceover.getnframes() / voiceover.getframerate())

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
    findings = deck.diagnose().findings

    # then: every scene has reading room and nothing is left for a viewer to trip on
    assert len(deck) == 8
    assert scene_durations == list(SCENE_DURATIONS)
    assert sum(scene_durations) == 34.6875
    assert all(
        scene_duration - voiceover_duration >= BEAT * 0.6
        for scene_duration, voiceover_duration in zip(
            scene_durations, voiceover_durations, strict=True
        )
    )
    assert all(delay <= BEAT for delay in first_animation_delays)
    assert transition_effects == ["cut", "fade", "wipe", "cut", "wipe", "cut", "fade", "fade"]
    assert [
        (finding.slide_index, finding.layer_index, finding.code, finding.message)
        for finding in findings
    ] == []


def test_product_hype_reel_animates_the_readings_it_is_about():
    """Every scene that leads on a number counts to it rather than printing it."""
    # given: the public example composition
    from examples.product_hype_reel import build_deck

    deck = build_deck()

    # when: the animated numeric readouts are collected per scene
    slides = json.loads(deck.to_json())["slides"]
    counters = {
        index: [layer["value"] for layer in slide["layers"] if layer.get("value")]
        for index, slide in enumerate(slides)
    }

    # then: the five scenes built around a reading each animate exactly one
    assert {index for index, values in counters.items() if values} == {0, 2, 3, 4, 5}
    assert all(len(values) == 1 for values in counters.values() if values)

    # then: each one actually travels, and the adapting plan is the one that falls
    travelled = {
        index: (values[0]["from"], values[0]["to"]) for index, values in counters.items() if values
    }
    assert all(start != end for start, end in travelled.values())
    assert [index for index, (start, end) in travelled.items() if end < start] == [4]


def test_product_hype_reel_finishes_every_scene_inside_its_own_beat():
    """Given the film, when its slideshow timing is read, then no scene outruns itself."""
    # Given: the exported slideshow, whose runtime chains a slide group by group
    # and only advances once nothing is still waiting to play
    import html as html_module
    import re

    from examples.product_hype_reel import SCENE_DURATIONS, build_deck

    rendered = Path(tempfile.mkdtemp()) / "reel.html"
    build_deck().render(str(rendered))

    # When: each scene's nodes and its chained total are read back
    stages = [
        json.loads(html_module.unescape(stage))
        for stage in re.findall(r"data-qt-timeline='([^']*)'", rendered.read_text())
    ]
    chains = [
        sum(node["d"] for node in stage if node["tr"] == "after_previous") for stage in stages
    ]
    triggers = {node["tr"] for stage in stages for node in stage}

    # Then: nothing waits for a click, so a scene plays and advances on its own
    assert triggers <= {"after_previous", "with_previous"}

    # Then: every chain lands inside the beat its scene was cut to, so no layer
    # is scheduled after the film has already moved on
    assert len(chains) == len(SCENE_DURATIONS)
    assert all(
        chain <= duration + 0.01 for chain, duration in zip(chains, SCENE_DURATIONS, strict=True)
    )


def test_product_hype_reel_draws_its_comparisons_to_one_scale():
    """A length on screen means the same thing wherever the film draws it."""
    # given: the scene that claims a shorter session and the scene that claims growth
    from examples.product_hype_reel import build_deck

    slides = json.loads(build_deck().to_json())["slides"]

    # when: the bars each scene compares are read back off the composition
    plan_bars = [
        layer["width"]
        for layer in slides[4]["layers"]
        if layer["type"] == "shape" and layer["height"] == 14
    ]
    week_bars = [
        layer["height"]
        for layer in slides[6]["layers"]
        if layer["type"] == "shape" and layer["width"] == 66
    ]

    # then: the planned and adjusted sessions are drawn at the same pixels per minute
    planned, today = plan_bars
    assert planned / 32 == today / 24

    # then: the eight-week chart rises every single week, so the trend is not decoration
    assert len(week_bars) == 8
    assert week_bars == sorted(week_bars)
    assert len(set(week_bars)) == 8


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
    assert gif_options[0].max_size == (432, 768)
    assert gif_options[0].colors == 64
    assert all(
        options.soundtrack is not None and options.soundtrack.loop for options in video_options
    )
