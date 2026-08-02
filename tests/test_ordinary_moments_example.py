"""Behavioral specifications for the production-style VideoLayer example."""

import json


def test_ordinary_moments_tells_a_sixty_second_story_in_nine_scenes():
    """Given the public example, when serialized, then its story contract is preserved."""
    # Given: the public, locally reproducible example deck
    from examples.ordinary_moments import FILM_DURATION, build_deck

    deck = build_deck()

    # When: the public composition is serialized
    payload = json.loads(deck.to_json())
    slides = payload["slides"]

    # Then: nine landscape scenes fill exactly sixty seconds
    assert payload["width"] == 1280
    assert payload["height"] == 720
    assert len(slides) == 9
    assert (
        sum(
            slide["transition"]["advance_after"]
            + (0 if slide["transition"]["effect"] == "cut" else slide["transition"]["duration"])
            for slide in slides
        )
        == FILM_DURATION
    )

    # Then: the film argues, rather than lists, its case
    text_content = {
        layer["content"] for slide in slides for layer in slide["layers"] if layer["type"] == "text"
    }
    assert {
        "같은 영상을\n몇 번이나 다시 만드나요?",
        "구성은 한 번이면 됩니다.",
        "한 번의 구성에서\n세 개의 파일.",
        "다시 만들지 마세요.",
        "한 번 구성하세요.",
        "uv add quickthumb",
        "github.com/sjquant/quickthumb",
    } <= text_content

    # Then: on-screen product readouts match the values the film actually uses
    from examples.ordinary_moments import (
        FIRST_CUE,
        SECOND_CUE,
        SOUNDTRACK_FADE_OUT,
        SOUNDTRACK_VOLUME,
        TIME_SPEED,
    )

    assert {f"{TIME_SPEED:.2f}×", f"{SOUNDTRACK_VOLUME:.0%}", f"{SOUNDTRACK_FADE_OUT:.1f}s"} <= (
        text_content
    )
    assert f"CUE 1   00:0{FIRST_CUE[0]} – 00:0{FIRST_CUE[1]}" in text_content
    assert f"CUE 2   00:0{SECOND_CUE[0]} – 00:0{SECOND_CUE[1]}" in text_content

    # Then: nothing in the composition is broken or cropped away
    findings = deck.diagnose()
    assert not any(finding.severity == "error" for finding in findings)
    assert not {finding.code for finding in findings} & {
        "text-clipped",
        "caption-timing",
        "caption-overlap",
        "missing-glyph",
    }


def test_ordinary_moments_gives_every_clip_a_distinct_job():
    """Given the example, when its clips are inspected, then no scene repeats another."""
    # Given: the public example deck
    from examples.ordinary_moments import build_deck

    deck = build_deck()

    # When: every video layer is collected with the scene that hosts it
    slides = json.loads(deck.to_json())["slides"]
    clips = [[layer for layer in slide["layers"] if layer["type"] == "video"] for slide in slides]
    flattened = [clip for scene in clips for clip in scene]

    # Then: eight scenes carry footage and the closing card is graphic only
    assert sum(1 for scene in clips if scene) == 8
    assert not clips[-1]
    assert len({clip["source"] for clip in flattened}) == 5

    # Then: two scenes compose footage into frames instead of filling the screen
    full_bleed = [clip for clip in flattened if clip["width"] == 1280 and clip["height"] == 720]
    composed = [clip for clip in flattened if clip not in full_bleed]
    assert len(full_bleed) == 6
    assert len(composed) == 4

    # Then: the three aspect frames hold the same moment of the same source
    fit_frames = [clip for clip in clips[3] if clip["type"] == "video"]
    assert len({(clip["source"], clip["trim_start"], clip["trim_end"]) for clip in fit_frames}) == 1
    assert len({clip["width"] / clip["height"] for clip in fit_frames}) == 3

    # Then: a clip never plays faster than its source, only slower when stretched
    assert all(0 < clip["speed"] <= 1.0 for clip in flattened)


def test_ordinary_moments_keeps_caption_treatment_and_fallback_contracts_public():
    """Given the example, when inspected for export, then captions and fallbacks are explicit."""
    # Given: the public production example
    from examples.ordinary_moments import build_deck

    deck = build_deck()

    # When: public JSON and export capability diagnostics are inspected
    payload = deck.to_json()
    diagnostics = deck.validate_export("pptx")

    # Then: two timed cues carry the caption proof with its styling intact
    captions = [
        caption
        for slide in json.loads(payload)["slides"]
        for layer in slide["layers"]
        if layer["type"] == "video"
        for caption in layer["captions"]
    ]
    assert len(captions) == 2
    assert captions[0]["end"] <= captions[1]["start"]
    assert all(caption["background_opacity"] == 0.9 for caption in captions)
    assert all(caption["border_radius"] == 2 for caption in captions)

    # Then: the document fallback for video is declared rather than silent
    assert any(
        item.feature == "video_layer" and item.fallback == "rasterize" for item in diagnostics
    )
