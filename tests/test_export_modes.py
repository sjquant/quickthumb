"""Effective file execution and declared motion queries have distinct contracts."""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock

import pytest
from quickthumb import (
    Canvas,
    Deck,
    ExportPolicy,
    GifOptions,
    Morph,
    VideoOptions,
)
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


@pytest.mark.parametrize("kind", ["pdf", "svg"])
def test_concrete_static_query_matches_export_diagnostics(tmp_path, kind):
    canvas = parent_canvas()
    query = canvas.validate_export(kind.upper())
    result = canvas.export(tmp_path / f"canvas.{kind}")
    assert query == result.capability_report
    assert all(item.target == "raster" and item.fallback == "static" for item in query)
    path = tmp_path / f"existing.{kind}"
    path.write_bytes(b"existing")
    for method in (canvas.render, canvas.export):
        with pytest.raises(RenderingError, match="authored-static"):
            method(str(path), policy=ExportPolicy(unsupported_motion="error"))
        assert path.read_bytes() == b"existing"


@pytest.mark.parametrize("kind", ["canvas", "deck"])
@pytest.mark.parametrize("method", ["render", "export"])
@pytest.mark.parametrize("extension", ["pdf", "svg", "pptx", "html"])
def test_parent_document_strict_policy_precedes_invalid_quality(tmp_path, kind, method, extension):
    canvas = parent_canvas()
    source = canvas if kind == "canvas" else Deck().slide(canvas)
    path = tmp_path / f"existing.{extension}"
    path.write_bytes(b"existing")
    message = "sampled approximation" if extension == "html" else "authored-static"
    with pytest.raises(RenderingError, match=message):
        getattr(source, method)(
            str(path), quality=90, policy=ExportPolicy(unsupported_motion="error")
        )
    assert path.read_bytes() == b"existing"


@pytest.mark.parametrize("kind", ["canvas", "deck"])
@pytest.mark.parametrize("method", ["render", "export"])
def test_early_parent_document_preflight_is_reused(tmp_path, monkeypatch, kind, method):
    from quickthumb import _document

    canvas = parent_canvas()
    source = canvas if kind == "canvas" else Deck().slide(canvas)
    preflight = Mock(wraps=_document.preflight_export)
    monkeypatch.setattr(_document, "preflight_export", preflight)
    getattr(source, method)(str(tmp_path / "scene.pdf"), policy=ExportPolicy())
    preflight.assert_called_once()


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


@pytest.mark.parametrize("method", ["render", "export"])
def test_canvas_raster_override_and_deck_document_rejection_remain_distinct(tmp_path, method):
    canvas = parent_canvas()
    path = tmp_path / "output.svg"
    getattr(canvas, method)(
        str(path), format="PNG", policy=ExportPolicy(unsupported_motion="error")
    )
    assert path.read_bytes().startswith(b"\x89PNG")
    with pytest.raises(RenderingError, match="single .svg"):
        getattr(Deck().slide(canvas), method)(str(path))
    assert path.read_bytes().startswith(b"\x89PNG")
    with pytest.raises(RenderingError, match="format override"):
        getattr(Deck().slide(canvas), method)(str(tmp_path / "output.pdf"), format="PNG")


@pytest.mark.parametrize(
    "alias,family",
    [
        ("GIF", "raster"),
        ("PNG", "raster"),
        ("JPEG", "raster"),
        ("WEBP", "raster"),
        ("MP4", "video"),
        ("WEBM", "video"),
        ("HTM", "html"),
        ("HTML", "html"),
        ("PPTX", "pptx"),
    ],
)
def test_declared_aliases_preserve_capability_families(alias, family):
    assert parent_canvas().validate_export(alias) == parent_canvas().validate_export(family)


@pytest.mark.parametrize("target", ["JPG", "JPEG", "WEBP", "SVG", "PDF", "HTM"])
def test_new_concrete_formats_do_not_expand_motion_family_queries(target):
    from quickthumb.motion import capabilities_for

    assert parent_canvas().validate_export(target)
    with pytest.raises(ValidationError, match="target must be"):
        capabilities_for(target)
    with pytest.raises(ValidationError, match="target must be"):
        parent_canvas().inspect_motion(target=target)


@pytest.mark.parametrize("target", ["GIF", "PNG", "MP4", "WEBM"])
def test_existing_motion_family_aliases_remain_accepted(target):
    from quickthumb.motion import capabilities_for

    assert capabilities_for(target)
    assert parent_canvas().inspect_motion(target=target).diagnostics


def test_unlinked_concrete_static_queries_keep_native_geometry(tmp_path):
    canvas = Canvas(16, 16).shape("rectangle", (1, 1), 8, 8, "#FF0000")
    policy = ExportPolicy(unsupported_motion="error")
    for extension in ("svg", "pdf"):
        assert canvas.validate_export(extension, policy) == []
        result = canvas.export(tmp_path / f"native.{extension}", policy=policy)
        assert not result.fallback_diagnostics


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
    with pytest.raises(RenderingError, match="authored-static"):
        parent_canvas().export(
            tmp_path / "native.pptx", policy=ExportPolicy(pptx={"layer:1": "native"})
        )
    assert not (tmp_path / "native.pptx").exists()


@pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="media tools")
def test_reduced_parent_morph_receipt_matches_encoded_duration_and_count(tmp_path):
    deck = (
        Deck()
        .slide(parent_canvas(), duration=1)
        .slide(Canvas(16, 16).background(color="#0000FF"), duration=1, transition=Morph(duration=2))
    )
    path = tmp_path / "reduced.mp4"
    result = deck.export(
        path,
        animation=VideoOptions(fps=10),
        policy=ExportPolicy(unsupported_motion="error", reduced_motion=True),
    )
    stream = json.loads(
        subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-count_frames",
                "-show_entries",
                "stream=duration,nb_read_frames",
                "-of",
                "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )["streams"][0]
    assert float(stream["duration"]) == result.timing_metrics.duration == 2
    assert int(stream["nb_read_frames"]) == result.pixel_metrics.frame_count == 20
    assert result.timing_metrics.frame_count == 20
    assert not any(item.feature == "parent_morph" for item in result.capability_report)
