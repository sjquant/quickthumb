"""Effective file execution and declared motion queries have distinct contracts."""

from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock

import pytest
from quickthumb import Canvas, Deck, ExportPolicy, GifOptions, Morph, VideoOptions
from quickthumb.errors import RenderingError, ValidationError


def parent_canvas():
    return Canvas(16, 16).null(id="root").shape("rectangle", (2, 2), 8, 8, "#FF0000", parent="root")


def parent_deck():
    return (
        Deck()
        .slide(parent_canvas(), duration=0.1)
        .slide(Canvas(16, 16), duration=0.1, transition=Morph(duration=0.1))
    )


@pytest.mark.parametrize("strict", [False, True])
def test_narrated_mp4_export_matches_render_without_claiming_unused_morph(
    tmp_path, monkeypatch, strict
):
    deck = parent_deck()
    writer = Mock(side_effect=lambda path: Path(path).write_bytes(b"static"))
    monkeypatch.setattr(deck, "render_mp4", writer)
    policy = ExportPolicy(unsupported_motion="error" if strict else "warn")
    rendered = tmp_path / "render.MP4"
    exported = tmp_path / "export.MP4"

    assert deck.render(str(rendered), policy=policy) == [str(rendered)]
    result = deck.export(exported, policy=policy)

    assert rendered.read_bytes() == exported.read_bytes() == b"static"
    assert writer.call_count == 2
    assert result.target == "video" and result.output_format == "mp4"
    assert result.timing_metrics.duration == pytest.approx(0.2)
    assert not any(item.feature == "parent_morph" for item in result.capability_report)
    assert not result.fallback_diagnostics


@pytest.mark.parametrize("method", ["render", "export"])
def test_explicit_animated_mp4_strict_policy_preserves_existing_output(
    tmp_path, monkeypatch, method
):
    from quickthumb import _export_video

    writer = Mock()
    monkeypatch.setattr(_export_video, "write_animation", writer)
    destination = tmp_path / "existing.mp4"
    destination.write_bytes(b"existing")
    with pytest.raises(RenderingError, match="fade fallback"):
        getattr(parent_deck(), method)(
            str(destination),
            animation=VideoOptions(),
            policy=ExportPolicy(unsupported_motion="error"),
        )
    writer.assert_not_called()
    assert destination.read_bytes() == b"existing"


@pytest.mark.parametrize("reduced", [False, True])
def test_animated_export_reports_only_transitions_that_execute(tmp_path, monkeypatch, reduced):
    from quickthumb import _export_video

    writer = Mock(
        side_effect=lambda _, __, path, **kw: (Path(path).write_bytes(b"animated"), None)[1]
    )
    monkeypatch.setattr(_export_video, "write_animation", writer)
    policy = ExportPolicy(unsupported_motion="error" if reduced else "warn", reduced_motion=reduced)
    deck = parent_deck()
    result = deck.export(tmp_path / "animated.mp4", animation=VideoOptions(), policy=policy)

    assert writer.call_args.kwargs["reduced_motion"] is reduced
    morph = [item for item in result.capability_report if item.feature == "parent_morph"]
    assert [item.fallback for item in morph] == ([] if reduced else ["fade"])
    if reduced:
        assert result.timing_metrics.duration == pytest.approx(0.6)
        assert result.timing_metrics.frame_count == 18
    # A standalone MP4 query has no execution options, and keeps its declared meaning.
    with pytest.raises(RenderingError, match="fade fallback"):
        deck.validate_export(
            "mp4", ExportPolicy(unsupported_motion="error", reduced_motion=reduced)
        )


def test_reduced_motion_byte_and_png_execution_skip_unused_parent_morph(tmp_path, monkeypatch):
    from quickthumb import _export_video

    encoder = Mock(return_value=b"reduced")
    monkeypatch.setattr(_export_video, "export_animation_bytes", encoder)
    deck = parent_deck()
    policy = ExportPolicy(unsupported_motion="error", reduced_motion=True)
    assert deck.to_animated_mp4(policy=policy) == b"reduced"
    assert encoder.call_args.kwargs["reduced_motion"] is True


@pytest.mark.parametrize("kind", ["canvas", "deck"])
@pytest.mark.parametrize("override", ["subclass", "instance", "class"])
def test_export_keeps_render_override_dispatch_once(tmp_path, monkeypatch, kind, override):
    base = cast(Any, Canvas if kind == "canvas" else Deck)
    original = base.render
    calls = []

    if override == "subclass":

        class Custom(base):
            def render(self, path, **kwargs):
                calls.append(path)
                return super().render(path, **kwargs)

        source = Custom(16, 16)
    else:
        source = base(16, 16)
        if override == "instance":

            def replacement(path, **kwargs):
                calls.append(path)
                return original(source, path, **kwargs)

            monkeypatch.setattr(source, "render", replacement)
        else:

            def replacement(self, path, **kwargs):
                calls.append(path)
                return original(self, path, **kwargs)

            monkeypatch.setattr(base, "render", replacement)
    if isinstance(source, Deck):
        source.slide(Canvas(16, 16))
    result = source.export(tmp_path / "overridden.png")
    assert calls == [str(tmp_path / "overridden.png")]
    assert len(result.written_paths) == 1
    assert Path(result.written_paths[0]).exists()


@pytest.mark.parametrize("method", ["render", "export"])
def test_canvas_mp4_defaults_to_animated_writer(tmp_path, monkeypatch, method):
    from quickthumb import _export_video

    writer = Mock(
        side_effect=lambda _, __, path, **kw: (Path(path).write_bytes(b"animated"), None)[1]
    )
    monkeypatch.setattr(_export_video, "write_animation", writer)
    getattr(parent_canvas(), method)(str(tmp_path / "canvas.mp4"))
    writer.assert_called_once()
    assert writer.call_args.kwargs["format"] == "mp4"
    assert writer.call_args.kwargs["animation"] is None
    assert writer.call_args.kwargs["reduced_motion"] is False


@pytest.mark.parametrize("kind", ["canvas", "deck"])
@pytest.mark.parametrize("method", ["render", "export"])
@pytest.mark.parametrize(
    "extension,kwargs,message",
    [
        ("mp4", {"format": "PNG"}, "format override"),
        ("mp4", {"quality": 90}, "Quality parameter"),
        ("mp4", {"animation": GifOptions()}, "GifOptions"),
        ("gif", {"animation": VideoOptions()}, "VideoOptions"),
        ("pdf", {"animation": VideoOptions()}, "animation options"),
        ("png", {"quality": 90}, "Quality parameter"),
        ("invalid", {}, "Unsupported"),
    ],
)
def test_invalid_export_options_preserve_existing_output(
    tmp_path, kind, method, extension, kwargs, message
):
    canvas = Canvas(16, 16)
    source = canvas if kind == "canvas" else Deck().slide(canvas)
    path = tmp_path / f"existing.{extension}"
    path.write_bytes(b"existing")
    with pytest.raises((RenderingError, ValidationError), match=message):
        getattr(source, method)(str(path), **kwargs)
    assert path.read_bytes() == b"existing"


@pytest.mark.parametrize("target", ["GIF", "PNG", "MP4", "WEBM"])
def test_existing_motion_family_aliases_remain_accepted(target):
    from quickthumb.motion import capabilities_for

    assert capabilities_for(target)
    assert parent_canvas().inspect_motion(target=target).diagnostics


def test_deck_sequence_preserves_inner_canvas_render_override(tmp_path, monkeypatch):
    canvas = Canvas(16, 16)
    original = canvas.render
    renderer = Mock(side_effect=original)
    monkeypatch.setattr(canvas, "render", renderer)
    result = Deck().slide(canvas).export(tmp_path / "slides.png")
    renderer.assert_called_once()
    assert result.written_paths == [str(tmp_path / "slides_01.png")]


def test_static_raster_sequence_omits_unused_morph_and_keeps_native_policy_checks(tmp_path):
    result = parent_deck().export(
        tmp_path / "slides.png", policy=ExportPolicy(unsupported_motion="error")
    )
    assert len(result.written_paths) == 2
    assert not any(item.feature == "parent_morph" for item in result.capability_report)
