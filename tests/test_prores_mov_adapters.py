"""Codec-free contracts for public ProRes MOV adapters and command-line dispatch."""

import inspect
import json
from pathlib import Path
from typing import Any, cast, get_args
from unittest.mock import Mock

import pytest
from quickthumb import (
    AnimationSpec,
    AudioTrack,
    Canvas,
    Deck,
    ExportPolicy,
    ExportResult,
    GifOptions,
    VideoOptions,
)
from quickthumb import _export_video as video
from quickthumb._base import FileFormat
from quickthumb._doctor import Environment, Requirements, check_environment
from quickthumb.cli import app
from quickthumb.errors import RenderingError, ValidationError
from quickthumb.motion import capabilities_for
from typer.testing import CliRunner


def document(kind: str) -> Canvas | Deck:
    canvas = Canvas(33, 25).shape("rectangle", (2, 3), 10, 12, "#E04060", opacity=0.5)
    return canvas if kind == "canvas" else Deck().slide(canvas, duration=0.75)


@pytest.fixture
def fake_writer(monkeypatch):
    def write(canvases, transitions, output_path, **kwargs):
        Path(output_path).write_bytes(b"mock ProRes MOV")

    writer = Mock(side_effect=write)
    monkeypatch.setattr(video, "write_animation", writer)
    return writer


@pytest.mark.parametrize("kind", ["canvas", "deck"])
def test_mov_bytes_signature_matches_existing_webm_convenience_api(kind):
    source = document(kind)
    assert inspect.signature(source.to_mov) == inspect.signature(source.to_webm)
    transparent = inspect.signature(source.to_mov).parameters["transparent"]
    assert transparent.kind == inspect.Parameter.KEYWORD_ONLY
    assert transparent.default is False


@pytest.mark.parametrize("kind", ["canvas", "deck"])
@pytest.mark.parametrize("transparent", [False, True])
def test_mov_bytes_forward_timing_audio_transparency_and_policy(monkeypatch, kind, transparent):
    source = document(kind)
    encoder = Mock(return_value=b"mock ProRes MOV")
    monkeypatch.setattr(video, "export_animation_bytes", encoder)
    soundtrack = AudioTrack(path="music.wav", volume=0.4, loop=True)
    policy = ExportPolicy(reduced_motion=True)

    result = source.to_mov(
        24, 1.25, "#123456", soundtrack, False, transparent=transparent, policy=policy
    )

    assert result == b"mock ProRes MOV"
    encoder.assert_called_once()
    canvases, transitions = encoder.call_args.args
    assert len(canvases) == 1
    assert canvases[0].width == 33 and canvases[0].height == 25
    assert transitions == [None]
    expected = {
        "format": "mov",
        "fps": 24,
        "slide_duration": 1.25,
        "matte": "#123456",
        "transparent": transparent,
        "soundtrack": soundtrack,
        "loop_audio": False,
        "reduced_motion": True,
    }
    if kind == "deck":
        expected.update(slide_audio=[None], slide_durations=[0.75], audio_durations=[0.75])
    assert encoder.call_args.kwargs == expected


@pytest.mark.parametrize("kind", ["canvas", "deck"])
def test_mov_bytes_default_to_opaque_thirty_fps_without_audio(monkeypatch, kind):
    encoder = Mock(return_value=b"mov")
    monkeypatch.setattr(video, "export_animation_bytes", encoder)

    assert document(kind).to_mov() == b"mov"

    options = encoder.call_args.kwargs
    assert options["format"] == "mov"
    assert options["fps"] == 30
    assert options["slide_duration"] == 3
    assert options["matte"] == "#000000"
    assert options["transparent"] is False
    assert options["soundtrack"] is None
    assert options["loop_audio"] is None
    assert options["reduced_motion"] is False


def test_deck_mov_bytes_preserve_explicit_narration_and_transition_schedule(monkeypatch, tmp_path):
    from quickthumb.transitions import Fade

    voice = tmp_path / "voice.wav"
    voice.write_bytes(b"mock audio; explicit duration avoids probing")
    first, second = Canvas(33, 25), Canvas(33, 25)
    transition = Fade(duration=0.2)
    track = AudioTrack(path=str(voice), volume=0.6)
    deck = (
        Deck()
        .slide(first, duration=0.5)
        .slide(second, duration=0.75, audio=track, transition=transition)
    )
    encoder = Mock(return_value=b"mov")
    monkeypatch.setattr(video, "export_animation_bytes", encoder)

    assert deck.to_mov(slide_duration=2, transparent=True) == b"mov"

    assert encoder.call_args.args == ([first, second], [None, transition])
    assert encoder.call_args.kwargs["slide_audio"] == [None, track]
    assert encoder.call_args.kwargs["slide_durations"] == [0.5, 0.75]
    assert encoder.call_args.kwargs["audio_durations"] == [0.5, 0.75]


@pytest.mark.parametrize("kind", ["canvas", "deck"])
@pytest.mark.parametrize("extension", ["mov", "MOV"])
@pytest.mark.parametrize("with_options", [False, True])
def test_mov_render_uses_animated_writer_and_namespaced_options(
    tmp_path, fake_writer, kind, extension, with_options
):
    source = document(kind)
    path = str(tmp_path / f"output.{extension}")
    options = (
        VideoOptions(
            fps=24,
            transparent=True,
            matte="#123456",
            workers=2,
            quality="high",
            soundtrack=AudioTrack(path="music.wav"),
            loop_audio=False,
        )
        if with_options
        else None
    )
    result = source.render(path, animation=options, policy=ExportPolicy(reduced_motion=True))

    assert result == (None if kind == "canvas" else [path])
    assert Path(path).read_bytes() == b"mock ProRes MOV"
    fake_writer.assert_called_once()
    assert fake_writer.call_args.args[2] == path
    assert fake_writer.call_args.kwargs["format"] == "mov"
    assert fake_writer.call_args.kwargs["animation"] is options
    assert fake_writer.call_args.kwargs["reduced_motion"] is True
    if kind == "deck":
        assert fake_writer.call_args.kwargs["slide_durations"] == [0.75]
        assert fake_writer.call_args.kwargs["audio_durations"] == [0.75]


def test_deck_mp4_keeps_static_default_while_mov_defaults_to_animation(
    monkeypatch, tmp_path, fake_writer
):
    deck = document("deck")
    static_writer = Mock()
    monkeypatch.setattr(Deck, "render_mp4", static_writer)

    mp4_path = str(tmp_path / "slides.mp4")
    mov_path = str(tmp_path / "slides.mov")
    assert deck.render(mp4_path) == [mp4_path]
    assert deck.render(mov_path) == [mov_path]

    static_writer.assert_called_once_with(mp4_path)
    fake_writer.assert_called_once()
    assert fake_writer.call_args.kwargs["format"] == "mov"


@pytest.mark.parametrize("kind", ["canvas", "deck"])
def test_mov_export_result_uses_video_capabilities_and_animated_timing(tmp_path, fake_writer, kind):
    source = document(kind)
    path = tmp_path / "result.MOV"
    result = source.export(path, animation=VideoOptions(fps=24, transparent=True))

    assert isinstance(result, ExportResult)
    assert result.kind == kind
    assert result.target == "video"
    assert result.output_format == "mov"
    assert result.written_paths == [str(path)]
    assert result.pixel_metrics.width == 33
    assert result.pixel_metrics.height == 25
    assert result.timing_metrics.fps == 24
    assert result.timing_metrics.duration == pytest.approx(3 if kind == "canvas" else 0.75)
    assert result.pixel_metrics.frame_count == result.timing_metrics.frame_count
    assert result.timing_metrics.frame_count == (72 if kind == "canvas" else 18)
    payload = json.loads(result.model_dump_json())
    assert payload["target"] == "video" and payload["output_format"] == "mov"
    assert Path(result.written_paths[0]).exists()


@pytest.mark.parametrize("kind", ["canvas", "deck"])
@pytest.mark.parametrize("target", ["mov", "MOV"])
def test_mov_motion_alias_uses_video_capabilities_and_policy(kind, target):
    canvas = Canvas(33, 25).shape(
        "rectangle", (2, 3), 10, 12, "#E04060", animation=AnimationSpec.fade()
    )
    source = canvas if kind == "canvas" else Deck().slide(canvas)
    policy = ExportPolicy(unsupported_motion="error", reduced_motion=True)

    assert capabilities_for(target) == capabilities_for("video")
    assert source.validate_export(target, policy) == source.validate_export("video", policy)


@pytest.mark.parametrize("kind", ["canvas", "deck"])
def test_mov_export_policy_failure_precedes_writer_and_preserves_destination(
    monkeypatch, tmp_path, fake_writer, kind
):
    from quickthumb import motion

    path = tmp_path / "existing.mov"
    path.write_bytes(b"previous export")
    policy = ExportPolicy(unsupported_motion="error")
    preflight = Mock(side_effect=RenderingError("injected unsupported motion"))
    monkeypatch.setattr(motion, "_validate_export", preflight)

    with pytest.raises(RenderingError, match="injected unsupported motion"):
        document(kind).export(path, policy=policy)

    assert preflight.call_args.args[1:] == ("video", policy)
    assert preflight.call_args.kwargs["parent_document_format"] == "mov"
    fake_writer.assert_not_called()
    assert path.read_bytes() == b"previous export"


def test_mov_does_not_expand_raster_file_format_or_add_codec_options():
    assert set(get_args(FileFormat)) == {"JPEG", "WEBP", "PNG"}
    for option in ("codec", "profile", "pix_fmt"):
        with pytest.raises(ValidationError, match=option):
            VideoOptions.model_validate({option: "prores"})


@pytest.mark.parametrize("value", [0, 1, "true", "false", None, [], {}])
def test_mov_video_options_keep_strict_transparency_contract(value):
    with pytest.raises(ValidationError, match="transparent"):
        VideoOptions.model_validate({"transparent": value})
    with pytest.raises(ValidationError, match="transparent"):
        VideoOptions.model_validate_json(json.dumps({"transparent": value}))


@pytest.mark.parametrize("kind", ["canvas", "deck"])
@pytest.mark.parametrize("value", [0, 1, "true", None])
def test_mov_bytes_reject_non_boolean_transparency_before_timeline(monkeypatch, kind, value):
    planner = Mock(side_effect=AssertionError("timeline must not be built"))
    monkeypatch.setattr(video, "_deck_plan", planner)
    monkeypatch.setattr(video, "_ffmpeg_binary", Mock(side_effect=AssertionError("no encoder")))

    with pytest.raises(ValidationError, match="transparent.*boolean"):
        document(kind).to_mov(transparent=cast(Any, value))

    planner.assert_not_called()


@pytest.mark.parametrize("kind", ["canvas", "deck"])
def test_mov_rejects_gif_options_before_codec_or_output(monkeypatch, tmp_path, kind):
    path = tmp_path / "existing.mov"
    path.write_bytes(b"previous export")
    monkeypatch.setattr(video, "_ffmpeg_binary", Mock(side_effect=AssertionError("no encoder")))

    with pytest.raises(ValidationError, match="GifOptions.*GIF"):
        document(kind).render(str(path), animation=GifOptions(fps=12))

    assert path.read_bytes() == b"previous export"
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("kind", ["canvas", "deck"])
@pytest.mark.parametrize("option", [{"format": "PNG"}, {"quality": 90}])
def test_mov_rejects_raster_controls_before_writer(tmp_path, fake_writer, kind, option):
    path = tmp_path / "existing.mov"
    path.write_bytes(b"previous export")

    with pytest.raises(RenderingError, match="format override|Quality parameter"):
        document(kind).render(str(path), **option)

    fake_writer.assert_not_called()
    assert path.read_bytes() == b"previous export"


def test_mov_rejects_canvas_debug_before_writer(tmp_path, fake_writer):
    with pytest.raises(RenderingError, match="Debug render"):
        Canvas(33, 25).render(str(tmp_path / "debug.mov"), debug=True)
    fake_writer.assert_not_called()


@pytest.mark.parametrize("entrypoint", ["bytes", "render", "export"])
def test_empty_deck_mov_fails_before_encoder(monkeypatch, tmp_path, entrypoint):
    monkeypatch.setattr(video, "_ffmpeg_binary", Mock(side_effect=AssertionError("no encoder")))
    deck = Deck()
    path = tmp_path / "empty.mov"

    with pytest.raises((RenderingError, ValidationError), match="no slides"):
        if entrypoint == "bytes":
            deck.to_mov()
        elif entrypoint == "render":
            deck.render(str(path))
        else:
            deck.export(path)

    assert not path.exists()


def environment(tools=()) -> Environment:
    return Environment(
        environ={},
        which=lambda name: f"/mock/bin/{name}" if name in tools else None,
        has_module=lambda name: False,
        find_font=lambda family: None,
        registered_plugins=lambda: (),
    )


def test_mov_doctor_requires_ffmpeg_and_only_requires_ffprobe_for_video_layers():
    missing = check_environment("MOV", env=environment())
    assert missing.workflow == "mov"
    assert not missing.ok
    assert {finding.check: finding.status for finding in missing.findings} == {
        "tool:ffmpeg": "error",
        "tool:ffprobe": "warning",
    }
    assert missing.errors[0].remedy and "FFmpeg" in missing.errors[0].remedy
    assert check_environment("mov", env=environment({"ffmpeg"})).ok

    layers = check_environment("mov", Requirements(video_layers=True), env=environment({"ffmpeg"}))
    assert [(finding.check, finding.status) for finding in layers.errors] == [
        ("tool:ffprobe", "error")
    ]


@pytest.mark.parametrize("kind", ["canvas", "deck"])
def test_cli_mov_extension_dispatches_and_prints_written_path(tmp_path, fake_writer, kind):
    spec = tmp_path / "source.json"
    spec.write_text(document(kind).to_json())
    output = tmp_path / "render.MOV"

    result = CliRunner().invoke(app, ["render", str(spec), "--output", str(output)])

    assert result.exit_code == 0, result.output
    assert result.output.strip() == str(output)
    assert output.read_bytes() == b"mock ProRes MOV"
    fake_writer.assert_called_once()
    assert fake_writer.call_args.kwargs["format"] == "mov"
    assert fake_writer.call_args.kwargs["animation"] is None


@pytest.mark.parametrize("kind", ["canvas", "deck"])
@pytest.mark.parametrize("error_format", ["text", "json"])
def test_cli_mov_encoder_errors_preserve_output_and_are_structured(
    monkeypatch, tmp_path, kind, error_format
):
    spec = tmp_path / "source.json"
    spec.write_text(document(kind).to_json())
    output = tmp_path / "existing.mov"
    output.write_bytes(b"previous export")
    monkeypatch.setattr(
        video,
        "write_animation",
        Mock(side_effect=RenderingError("ProRes encoder unavailable", code="export_failed")),
    )

    result = CliRunner().invoke(
        app,
        ["render", str(spec), "-o", str(output), "--error-format", error_format],
    )

    assert result.exit_code == 2
    assert "Traceback" not in result.output
    if error_format == "json":
        error = json.loads(result.output)["errors"][0]
        assert error["code"] == "export_failed"
        assert error["category"] == "export"
        assert error["message"] == "ProRes encoder unavailable"
    else:
        assert "error[export_failed]" in result.output
        assert "ProRes encoder unavailable" in result.output
    assert output.read_bytes() == b"previous export"


@pytest.mark.parametrize("kind", ["canvas", "deck"])
@pytest.mark.parametrize("option", [["--format", "PNG"], ["--quality", "90"]])
def test_cli_mov_rejects_raster_controls_without_overwriting(tmp_path, fake_writer, kind, option):
    spec = tmp_path / "source.json"
    spec.write_text(document(kind).to_json())
    output = tmp_path / "existing.mov"
    output.write_bytes(b"previous export")

    result = CliRunner().invoke(app, ["render", str(spec), "-o", str(output), *option])

    assert result.exit_code == 2
    assert "error[" in result.output
    assert "Traceback" not in result.output
    fake_writer.assert_not_called()
    assert output.read_bytes() == b"previous export"


@pytest.mark.parametrize("available", [False, True])
def test_cli_mov_doctor_reports_readiness_as_json(monkeypatch, available):
    from quickthumb import cli

    report = check_environment("mov", env=environment({"ffmpeg"} if available else ()))
    checker = Mock(return_value=report)
    monkeypatch.setattr(cli, "check_environment", checker)

    result = CliRunner().invoke(app, ["doctor", "mov", "--format", "json"])

    assert result.exit_code == (0 if available else 1)
    payload = json.loads(result.output)
    assert payload["workflow"] == "mov"
    assert payload["ok"] is available
    assert checker.call_args.args[0] == "mov"
