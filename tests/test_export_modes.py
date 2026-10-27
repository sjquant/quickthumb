"""Effective file execution and declared motion queries have distinct contracts."""

import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from quickthumb import (
    AnimationSpec,
    Canvas,
    Deck,
    ExportPolicy,
    GifOptions,
    GroupLayer,
    ImageSequenceOptions,
    LayerClip,
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


@pytest.mark.parametrize("method", ["render", "export"])
@pytest.mark.parametrize("animation", [None, VideoOptions()])
def test_mp4_strict_policy_preserves_existing_output(tmp_path, monkeypatch, method, animation):
    """Default and configured MP4 reject unsupported motion before replacing a file."""
    from quickthumb import _export_video

    writer = Mock()
    monkeypatch.setattr(_export_video, "write_animation", writer)
    destination = tmp_path / "existing.mp4"
    destination.write_bytes(b"existing")
    with pytest.raises(RenderingError, match="fade fallback"):
        getattr(parent_deck(), method)(
            str(destination),
            animation=animation,
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


@pytest.mark.parametrize(
    "kind,extension",
    [
        ("canvas", "pdf"),
        ("canvas", "svg"),
        ("canvas", "pptx"),
        ("canvas", "html"),
        ("deck", "pdf"),
        ("deck", "pptx"),
        ("deck", "html"),
    ],
)
@pytest.mark.parametrize("method", ["render", "export"])
def test_parent_document_strict_policy_preserves_output(tmp_path, kind, method, extension):
    canvas = parent_canvas()
    source = canvas if kind == "canvas" else Deck().slide(canvas)
    path = tmp_path / f"existing.{extension}"
    path.write_bytes(b"existing")
    message = "sampled approximation" if extension == "html" else "authored-static"
    with pytest.raises(RenderingError, match=message):
        getattr(source, method)(str(path), policy=ExportPolicy(unsupported_motion="error"))
    assert path.read_bytes() == b"existing"


def test_reduced_motion_byte_and_png_execution_skip_unused_parent_morph(tmp_path, monkeypatch):
    from quickthumb import _export_video

    encoder = Mock(return_value=b"reduced")
    monkeypatch.setattr(_export_video, "export_animation_bytes", encoder)
    deck = parent_deck()
    policy = ExportPolicy(unsupported_motion="error", reduced_motion=True)
    assert deck.to_mp4(policy=policy) == b"reduced"
    assert encoder.call_args.kwargs["reduced_motion"] is True
    result = deck.export_image_sequence(
        tmp_path / "frames", options=ImageSequenceOptions(fps=10), policy=policy
    )
    assert not any(item.feature == "parent_morph" for item in result.capability_report)


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


@pytest.mark.parametrize("method", ["render", "export", "image_sequence"])
@pytest.mark.parametrize("reduced", [False, True])
def test_animated_and_reduced_execution_reject_unsupported_geometry(tmp_path, method, reduced):
    canvas = parent_canvas()
    canvas.layers = [
        canvas.layers[0],
        GroupLayer(
            type="group",
            parent="root",
            children=[
                canvas.layers[1].model_copy(
                    update={
                        "parent": None,
                        "position": (0, 0),
                        "clip": LayerClip(position=(0, 0), width=4, height=4),
                        "animation": AnimationSpec.fade(),
                    }
                )
            ],
        ),
    ]
    deck = Deck().slide(canvas)
    path = tmp_path / "existing.mp4"
    path.write_bytes(b"existing")
    policy = ExportPolicy(unsupported_motion="error", reduced_motion=reduced)
    with pytest.raises(RenderingError, match="descendant boundaries cannot animate descendants"):
        if method == "image_sequence":
            deck.export_image_sequence(tmp_path / "frames", policy=policy)
        else:
            getattr(deck, method)(
                str(path), animation=VideoOptions() if reduced else None, policy=policy
            )
    assert path.read_bytes() == b"existing"
    assert not (tmp_path / "frames").exists()


@pytest.mark.parametrize("kind", ["canvas", "deck"])
@pytest.mark.parametrize("method", ["render", "export"])
@pytest.mark.parametrize(
    "extension,kwargs,message",
    [
        ("mp4", {"format": "PNG"}, "format override"),
        ("mp4", {"quality": 90}, "Quality parameter"),
        ("mp4", {"animation": GifOptions()}, "VideoOptions"),
        ("mp4", {"animation": VideoOptions(transparent=True)}, "transparent output"),
        ("gif", {"animation": VideoOptions()}, "GifOptions"),
        ("pdf", {"animation": VideoOptions()}, "animation options"),
        ("png", {"quality": 90}, "Quality parameter"),
        ("invalid", {}, "Unsupported"),
        ("bin", {"format": "SVG"}, "format must"),
        ("pdf", {"format": "PNG"}, "format override"),
        ("html", {"format": "PNG"}, "format override"),
        ("svg", {"format": "PNG"}, "format override"),
        ("jpg", {"quality": True}, "integer between 1 and 95"),
        ("jpg", {"quality": 0}, "integer between 1 and 95"),
        ("jpg", {"quality": 96}, "integer between 1 and 95"),
        ("webp", {"quality": 101}, "integer between 1 and 100"),
    ],
)
def test_invalid_export_options_preserve_existing_output(
    tmp_path, kind, method, extension, kwargs, message
):
    """Invalid file options fail before reading an unavailable asset or writing any output."""
    # Given: a missing input asset and an existing destination
    canvas = Canvas(16, 16).image(str(tmp_path / "missing.png"), position=(0, 0), width=8, height=8)
    source = canvas if kind == "canvas" else Deck().slide(canvas)
    path = tmp_path / f"existing.{extension}"
    path.write_bytes(b"existing")

    # When / Then: option errors take precedence over input reads and all writes
    with pytest.raises((RenderingError, ValidationError), match=message):
        getattr(source, method)(str(path), **kwargs)
    assert path.read_bytes() == b"existing"
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("kind", ["canvas", "deck"])
@pytest.mark.parametrize(
    "filename,format,encoded_format,result_format,quality",
    [
        ("photo.jpg", None, "JPEG", "jpeg", 95),
        ("photo.png", "jPeG", "JPEG", "jpeg", 95),
        ("photo.bin", "PNG", "PNG", "png", None),
        ("photo", "WEBP", "WEBP", "webp", 100),
    ],
)
def test_raster_format_selection_matches_result(
    tmp_path, kind, filename, format, encoded_format, result_format, quality
):
    """Canvas and Deck encode the selected raster format and report the actual files."""
    # Given: the same scene exported alone or as two Deck slides
    from PIL import Image

    canvas = Canvas(16, 16).background(color="#123456")
    source = canvas if kind == "canvas" else Deck(slides=[canvas, canvas])
    output = tmp_path / filename

    # When: an extension or explicit raster format selects the encoding
    result = source.export(output, format=format, quality=quality)

    # Then: metadata names the encoding, and Deck paths identify numbered slide files
    expected = (
        [str(output)]
        if kind == "canvas"
        else [str(output.with_name(f"{output.stem}_{index:02}{output.suffix}")) for index in (1, 2)]
    )
    assert result.written_paths == expected
    assert result.output_format == result_format
    assert result.target == "raster"
    for path in result.written_paths:
        with Image.open(path) as image:
            assert image.format == encoded_format
            assert image.size == (16, 16)


@pytest.mark.parametrize(
    "alias,family",
    [
        ("GIF", "raster"),
        ("PNG", "raster"),
        ("JPEG", "raster"),
        ("WEBP", "raster"),
        ("MP4", "video"),
        ("MOV", "video"),
        ("WEBM", "video"),
        ("IMAGE_SEQUENCE", "video"),
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


@pytest.mark.parametrize("target", ["GIF", "PNG", "MP4", "MOV", "WEBM", "IMAGE_SEQUENCE"])
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
