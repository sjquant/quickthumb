"""Lossless decoded pixels, exact export timing, and fresh-directory publication."""

import gc
import json
import os
import shutil
import struct
import subprocess
import threading
import wave
import weakref
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock

import jsonschema
import pytest
from PIL import Image, PngImagePlugin
from quickthumb import (
    AnimationSpec,
    AudioTrack,
    Canvas,
    Deck,
    ExportPolicy,
    Fade,
    ImageSequenceManifest,
    ImageSequenceOptions,
    ImageSequenceResult,
    VideoOptions,
)
from quickthumb import _export_image_sequence as sequence
from quickthumb import _export_video as video
from quickthumb import transitions as tr
from quickthumb._document import _contract_timeline_inputs
from quickthumb.errors import MissingAssetError, RenderingError, ValidationError


def decoded(directory: Path, extension="png") -> list[bytes]:
    payloads = []
    for path in sorted(directory.glob(f"*.{extension}")):
        with Image.open(path) as frame:
            assert frame.mode == "RGBA"
            payloads.append(frame.tobytes())
    return payloads


def reference(source, fps=10, hold=0.1, quality="standard", reduced=False) -> list[bytes]:
    canvases, transitions, durations = _contract_timeline_inputs(source, hold)
    if reduced:
        transitions = [None] * len(canvases)
    plan = video._deck_plan(
        canvases,
        transitions,
        1 / fps,
        hold,
        durations,
        quality=quality,
        reduced_motion=reduced,
    )
    shots = video._ordered_deck_shots(canvases, fps, None, plan)
    try:
        return [
            frame.tobytes()
            for frame, count in video._counted_video_shots(shots, fps)
            for _ in range(count)
        ]
    finally:
        shots.close()
        video._close_video_decoders(canvases)


def animated_canvas() -> Canvas:
    return Canvas(17, 9).shape("rectangle", (1, 1), 9, 7, "#E0406080", animation=Fade(duration=0.4))


@pytest.mark.parametrize(
    "field,values",
    [
        ("fps", [None, True, False, "30", 0, -1, 120.1, float("inf"), float("nan")]),
        ("hold", [None, True, False, "3", -1, float("inf"), float("nan")]),
        ("workers", [None, True, False, "2", 1.0, 0, 9]),
        ("render_quality", [None, "draft", 1]),
    ],
)
def test_options_reject_invalid_values(field, values):
    for value in values:
        with pytest.raises(ValidationError):
            ImageSequenceOptions(**{field: value})


@pytest.mark.parametrize(
    "field", ["matte", "transparent", "soundtrack", "loop", "max_size", "format"]
)
def test_sequence_options_forbid_unrelated_controls(field):
    with pytest.raises(ValidationError):
        ImageSequenceOptions.model_validate({field: None})


@pytest.mark.parametrize("kind", ["canvas", "deck"])
def test_default_manifest_is_compact_json_safe_and_actual(kind, tmp_path, monkeypatch):
    canvas = Canvas(1, 3).background(color="#325B7180")
    source = canvas if kind == "canvas" else Deck().slide(canvas)
    monkeypatch.setattr(source, "sample", Mock(side_effect=AssertionError("sample is not export")))
    result = source.export_image_sequence(tmp_path / "frames")
    manifest = json.loads(Path(result.manifest_path).read_text())
    expected = {
        "version": "1",
        "kind": kind,
        "format": "image_sequence",
        "encoding": "png",
        "filename_pattern": "%06d.png",
        "start_index": 0,
        "frame_count": 90,
        "fps": 30.0,
        "duration": 3.0,
        "width": 1,
        "height": 3,
        "mode": "RGBA",
        "bit_depth": 8,
        "alpha": "straight",
        "lossless": True,
        "quality": None,
        "matte": None,
    }
    assert manifest == expected
    assert len(list((tmp_path / "frames").iterdir())) == 91
    assert (
        result.model_dump(exclude={"output_directory", "manifest_path", "capability_report"})
        == manifest
    )
    assert result.output_directory == str(tmp_path / "frames")
    assert result.frame_count == len(decoded(tmp_path / "frames"))
    assert result.duration == result.frame_count / result.fps
    assert ImageSequenceManifest.model_validate_json(json.dumps(manifest)).model_dump() == manifest
    assert ImageSequenceResult.model_validate_json(result.model_dump_json()) == result
    jsonschema.validate(manifest, ImageSequenceManifest.model_json_schema())
    jsonschema.validate(result.model_dump(mode="json"), ImageSequenceResult.model_json_schema())
    assert set(manifest).isdisjoint(
        {"color_space", "asset_manifest", "timestamp", "files", "paths"}
    )


@pytest.mark.parametrize("kind", ["canvas", "deck"])
@pytest.mark.parametrize(
    "format,kwargs,extension,mode,alpha,lossless,quality,matte,pixel",
    [
        ("JPEG", {}, "jpg", "RGB", "none", False, 90, "#FFFFFF", (187, 157, 142)),
        (
            "jpeg",
            {"quality": 25, "matte": "navy"},
            "jpg",
            "RGB",
            "none",
            False,
            25,
            "#000080",
            (60, 30, 79),
        ),
        ("WebP", {}, "webp", "RGBA", "straight", False, 80, None, (120, 60, 30, 128)),
        (
            "webp",
            {"lossless": True},
            "webp",
            "RGBA",
            "straight",
            True,
            None,
            None,
            (120, 60, 30, 128),
        ),
    ],
)
def test_encoded_frames_and_manifest_match_selected_format(
    kind, format, kwargs, extension, mode, alpha, lossless, quality, matte, pixel, tmp_path
):
    """JPEG flattens alpha; WebP preserves alpha, with manifest encoding and actual timing."""
    # Given: uniform translucent pixels with no profile or audio inputs.
    canvas = Canvas(24, 8).background(color="#783C1E80")
    source = canvas if kind == "canvas" else Deck().slide(canvas, duration=0.2)
    destination = tmp_path / "frames"
    # When: the public API encodes two canonical frames into the requested format.
    result = source.export_image_sequence(
        destination, format=format, **kwargs, options=ImageSequenceOptions(fps=10, hold=0.2)
    )
    # Then: both decoded files and the receipt describe the chosen representation.
    manifest = json.loads(Path(result.manifest_path).read_text())
    assert manifest["encoding"] == format.lower()
    assert manifest["filename_pattern"] == f"%06d.{extension}"
    assert (manifest["mode"], manifest["alpha"], manifest["lossless"]) == (mode, alpha, lossless)
    assert (manifest["quality"], manifest["matte"]) == (quality, matte)
    assert (result.frame_count, result.duration) == (2, 0.2)
    assert {path.name for path in destination.iterdir()} == {
        f"000000.{extension}",
        f"000001.{extension}",
        "manifest.json",
    }
    for path in sorted(destination.glob(f"*.{extension}")):
        with Image.open(path) as image:
            assert image.mode == mode and image.size == (24, 8)
            actual = image.getpixel((12, 4))
            assert isinstance(actual, tuple)
            assert all(
                abs(a - b) <= (0 if lossless else 5) for a, b in zip(actual, pixel, strict=True)
            )
            assert not {"icc_profile", "exif", "xmp"} & image.info.keys()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"format": None},
        {"format": "gif"},
        {"format": True},
        {"quality": 90},
        {"matte": "white"},
        {"lossless": True},
        {"format": "jpeg", "quality": True},
        {"format": "jpeg", "quality": 90.0},
        {"format": "jpeg", "quality": "90"},
        {"format": "jpeg", "quality": 0},
        {"format": "jpeg", "quality": 96},
        {"format": "jpeg", "lossless": False},
        {"format": "jpeg", "matte": 0},
        {"format": "jpeg", "matte": "#FFFFFF80"},
        {"format": "jpeg", "matte": "rgb(256,0,0)"},
        {"format": "jpeg", "matte": "rgb(101%,0%,0%)"},
        {"format": "webp", "matte": "white"},
        {"format": "webp", "lossless": 1},
        {"format": "webp", "lossless": "yes"},
        {"format": "webp", "lossless": True, "quality": 80},
    ],
)
def test_invalid_encoding_options_leave_output_untouched(kwargs, tmp_path):
    """Invalid or incompatible encoding arguments fail without creating output or staging."""
    # Given: a nonexistent destination inside an empty parent.
    destination = tmp_path / "frames"
    # When/Then: invalid public controls are rejected without filesystem mutation.
    with pytest.raises(ValidationError):
        Canvas(1, 1).export_image_sequence(destination, **kwargs)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("format", ["png", "webp"])
def test_exact_all_alpha_codes_hidden_rgb_metadata_and_independent_repeats(
    format, tmp_path, monkeypatch
):
    """Lossless sequence files retain every source alpha code and hidden RGB independently."""
    raw = bytes(channel for a in range(256) for channel in (a, 255 - a, 91, a)) * 3
    expected = Image.frombytes("RGBA", (256, 3), raw)
    expected.info.update(
        icc_profile=b"un-normalized profile", srgb=0, exif=b"metadata", transparency=0
    )
    monkeypatch.setattr(
        video, "_ordered_deck_shots", lambda *a, **k: (s for s in [video._Shot(expected, 0.3)])
    )
    path = tmp_path / "exact"
    result = Canvas(256, 3).export_image_sequence(
        path,
        format=format,
        lossless=True if format == "webp" else None,
        options=ImageSequenceOptions(fps=10, hold=0.3),
    )
    assert result.frame_count == 3
    assert decoded(path, format) == [raw] * 3
    files = sorted(path.glob(f"*.{format}"))
    assert len({file.stat().st_ino for file in files}) == 3
    if format == "png":
        png = files[0].read_bytes()
        chunks = []
        offset = 8
        while offset < len(png):
            size = struct.unpack(">I", png[offset : offset + 4])[0]
            chunks.append(png[offset + 4 : offset + 8])
            offset += 12 + size
        assert png[24:26] == bytes([8, 6])  # RGBA, eight bits per channel
        assert chunks == [b"IHDR", b"IDAT", b"IEND"]
    with Image.open(files[0]) as image:
        image.putpixel((0, 0), (0, 0, 0, 255))
        image.save(files[0])
    with Image.open(files[1]) as untouched:
        assert untouched.tobytes() == raw


@pytest.mark.parametrize("size", [(1, 1), (1, 3), (3, 1), (17, 9)])
def test_full_dimensions_edges_and_authored_background(size, tmp_path):
    canvas = Canvas(*size).background(color="#327B9140")
    canvas.shape("rectangle", (size[0] - 1, 0), 1, size[1], "#F03080")
    canvas.shape("rectangle", (0, size[1] - 1), size[0], 1, "#40D060")
    path = tmp_path / "edges"
    result = canvas.export_image_sequence(path, options=ImageSequenceOptions(hold=0))
    with Image.open(path / "000000.png") as frame:
        assert frame.size == size
        assert frame.getpixel((size[0] - 1, size[1] - 1)) == (64, 208, 96, 255)
        assert frame.tobytes() == canvas._render_to_image().tobytes()
    assert (result.width, result.height) == size


def test_fractional_timing_uses_cumulative_half_up_allocation(tmp_path):
    deck = Deck(1, 1, transition="cut")
    colors = ["#FF0000", "#00FF00", "#0000FF"]
    for color in colors:
        deck.slide(Canvas(1, 1).background(color=color), duration=0.25)
    result = deck.export_image_sequence(
        tmp_path / "fractional", options=ImageSequenceOptions(fps=10)
    )
    assert result.frame_count == 8
    assert result.duration == 0.8
    assert (
        decoded(tmp_path / "fractional")
        == [bytes([255, 0, 0, 255])] * 3
        + [bytes([0, 255, 0, 255])] * 2
        + [bytes([0, 0, 255, 255])] * 3
    )


@pytest.mark.parametrize("fps,hold", [(29.97, 0), (2.5, 0.1), (7.5, 0.333), (120, 0)])
@pytest.mark.parametrize("animated", [False, True])
def test_zero_subframe_and_fractional_holds_match_actual_export(tmp_path, fps, hold, animated):
    source = animated_canvas() if animated else Canvas(17, 9)
    expected = reference(source, fps, hold)
    result = source.export_image_sequence(
        tmp_path / "frames", options=ImageSequenceOptions(fps=fps, hold=hold)
    )
    assert decoded(tmp_path / "frames") == expected
    assert result.frame_count == len(expected)
    assert result.duration == len(expected) / fps


@pytest.mark.parametrize(
    "transition",
    [
        tr.Cut(),
        tr.Fade(duration=0.2),
        tr.Random(duration=0.2),
        tr.Morph(duration=0.2),
        tr.Push(duration=0.2),
        tr.Cover(duration=0.2),
        tr.Uncover(duration=0.2),
        tr.Zoom(duration=0.2),
        tr.Newsflash(duration=0.2),
        tr.Wipe(duration=0.2),
        tr.Split(duration=0.2),
        tr.Blinds(duration=0.2),
        tr.Checker(duration=0.2),
        tr.Comb(duration=0.2),
        tr.Circle(duration=0.2),
        tr.Diamond(duration=0.2),
        tr.Wheel(duration=0.2),
        tr.Wedge(duration=0.2),
        tr.Dissolve(duration=0.2),
    ],
)
def test_transition_families_and_keyed_mixed_size_morph(transition, tmp_path):
    first = Canvas(17, 9).shape("rectangle", (1, 1), 8, 6, "#EF508080", motion_key="box")
    second = Canvas(9, 7).shape("rectangle", (2, 2), 6, 4, "#4080D040", motion_key="box")
    deck = Deck().slide(first, duration=0.1).slide(second, duration=0.1, transition=transition)
    expected = reference(deck)
    result = deck.export_image_sequence(
        tmp_path / "transition", options=ImageSequenceOptions(fps=10, hold=0.1)
    )
    assert decoded(tmp_path / "transition") == expected
    assert result.frame_count == len(expected)


@pytest.mark.parametrize("quality", ["standard", "high"])
@pytest.mark.parametrize("workers", [1, 2])
def test_canvas_deck_serial_spawn_parity_and_quality(quality, workers, tmp_path):
    for kind in ("canvas", "deck"):
        canvas = animated_canvas()
        source = canvas if kind == "canvas" else Deck().slide(canvas)
        expected = reference(source, quality=quality)
        path = tmp_path / kind
        result = source.export_image_sequence(
            path,
            options=ImageSequenceOptions(fps=10, hold=0.1, render_quality=quality, workers=workers),
        )
        assert decoded(path) == expected
        assert result.frame_count == 5
    assert decoded(tmp_path / "canvas") == decoded(tmp_path / "deck")


def test_reduced_motion_and_strict_parent_morph_policy(tmp_path):
    parented = (
        Canvas(17, 9)
        .null((2, 2), id="root")
        .shape(
            "rectangle",
            (0, 0),
            8,
            6,
            "#EF508080",
            parent="root",
            animation=AnimationSpec.fade(duration=0.4),
        )
    )
    deck = Deck().slide(parented).slide(Canvas(17, 9), transition=tr.Morph(duration=0.4))
    policy = ExportPolicy(unsupported_motion="error")
    assert deck.validate_export("image_sequence") == deck.validate_export("video")
    with pytest.raises(RenderingError, match="fade fallback"):
        deck.export_image_sequence(tmp_path / "strict", policy=policy)
    assert list(tmp_path.iterdir()) == []
    expected = reference(deck, reduced=True)
    result = deck.export_image_sequence(
        tmp_path / "reduced",
        options=ImageSequenceOptions(fps=10, hold=0.1),
        policy=ExportPolicy(reduced_motion=True),
    )
    assert decoded(tmp_path / "reduced") == expected
    assert result.frame_count == len(expected)


def test_morph_fallback_diagnostics_are_returned(tmp_path):
    first = (
        Canvas(17, 9)
        .null((2, 2), id="root")
        .shape("rectangle", (0, 0), 8, 6, "#FF0000", parent="root")
    )
    deck = Deck().slide(first).slide(Canvas(17, 9), transition=tr.Morph(duration=0.2))
    result = deck.export_image_sequence(
        tmp_path / "fallback", options=ImageSequenceOptions(fps=10, hold=0.1)
    )
    assert any(
        item.feature == "parent_morph" and item.fallback == "fade"
        for item in result.capability_report
    )


def test_no_audio_mux_ffmpeg_or_sampling_for_explicit_65_narrations(tmp_path, monkeypatch):
    voice = tmp_path / "voice.wav"
    voice.write_bytes(b"explicit visual duration; never decoded")
    deck = Deck(1, 1, transition="cut")
    for index in range(65):
        deck.slide(
            Canvas(1, 1).background(color=f"#{index:02x}0000"),
            duration=0.1,
            audio=AudioTrack(path=str(voice)),
        )
    forbidden = Mock(side_effect=AssertionError("silent frames must not encode or mix audio"))
    monkeypatch.setattr(video, "_ffmpeg_binary", forbidden)
    monkeypatch.setattr(video, "_video_audio_schedule", forbidden)
    monkeypatch.setattr(video, "_scheduled_audio_args", forbidden)
    monkeypatch.setattr(video, "_encode_video_file", forbidden)
    monkeypatch.setenv("QUICKTHUMB_FFMPEG", "/does-not-exist/ffmpeg")
    result = deck.export_image_sequence(tmp_path / "silent", options=ImageSequenceOptions(fps=10))
    assert result.frame_count == 65
    assert result.duration == 6.5
    assert {p.suffix for p in (tmp_path / "silent").iterdir()} == {".png", ".json"}
    assert decoded(tmp_path / "silent") == [bytes([index, 0, 0, 255]) for index in range(65)]
    forbidden.assert_not_called()


@pytest.mark.skipif(not shutil.which("ffprobe"), reason="ffprobe required for narration timing")
def test_real_narration_inference_beyond_64_inputs_is_visual_only(tmp_path, monkeypatch):
    voice = tmp_path / "voice.wav"
    with wave.open(str(voice), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(b"\0\0" * 800)
    deck = Deck(1, 1, transition="cut")
    for _ in range(65):
        deck.slide(Canvas(1, 1), audio=str(voice))
    monkeypatch.setattr(video, "_ffmpeg_binary", Mock(side_effect=AssertionError("no encoder")))
    result = deck.export_image_sequence(tmp_path / "inferred", options=ImageSequenceOptions(fps=10))
    assert result.frame_count == 65
    assert result.duration == 6.5


@pytest.mark.parametrize(
    "stage", ["plan", "producer", "png", "png_write", "manifest", "result", "close", "commit"]
)
def test_failure_cleans_owned_staging_and_closes_resources_before_publication(
    stage, tmp_path, monkeypatch
):
    original = RuntimeError(f"original {stage} failure")
    closed = Mock(wraps=video._PreparedAnimation.close)
    monkeypatch.setattr(video._PreparedAnimation, "close", lambda prepared: closed(prepared))
    if stage == "plan":
        monkeypatch.setattr(video, "_deck_plan", Mock(side_effect=original))
    elif stage == "producer":

        def broken(*args, **kwargs):
            yield video._Shot(Image.new("RGBA", (1, 1)), 0.1)
            raise original

        monkeypatch.setattr(video, "_ordered_deck_shots", broken)
    elif stage == "png":
        monkeypatch.setattr(sequence, "_encode_image_frame", Mock(side_effect=original))
    elif stage == "png_write":
        write = Path.write_bytes

        def broken_write(path, data):
            write(path, data[:10])
            raise original

        monkeypatch.setattr(Path, "write_bytes", broken_write)
    elif stage == "manifest":

        def broken_manifest(path, *args, **kwargs):
            path.write_bytes(b"partial manifest")
            raise original

        monkeypatch.setattr(Path, "write_text", broken_manifest)
    elif stage == "result":
        monkeypatch.setattr(sequence, "ImageSequenceResult", Mock(side_effect=original))
    elif stage == "close":
        closed.side_effect = original
    else:
        monkeypatch.setattr(sequence, "rename_exclusive", Mock(side_effect=original))
    with pytest.raises(RuntimeError) as error:
        Canvas(1, 1).export_image_sequence(
            tmp_path / "failed", options=ImageSequenceOptions(fps=10, hold=0.1)
        )
    assert error.value is original
    assert closed.call_count == 1
    assert list(tmp_path.iterdir()) == []


def test_producer_error_wins_over_shutdown_and_cleanup_errors(tmp_path, monkeypatch):
    original = RuntimeError("producer")

    def broken(*args, **kwargs):
        yield video._Shot(Image.new("RGBA", (1, 1)), 0.1)
        raise original

    monkeypatch.setattr(video, "_ordered_deck_shots", broken)
    monkeypatch.setattr(video._PreparedAnimation, "close", Mock(side_effect=RuntimeError("close")))
    monkeypatch.setattr(shutil, "rmtree", Mock(side_effect=OSError("cleanup")))
    with pytest.raises(RuntimeError) as error:
        Canvas(1, 1).export_image_sequence(
            tmp_path / "failed", options=ImageSequenceOptions(fps=10, hold=0.1)
        )
    assert error.value is original
    assert not (tmp_path / "failed").exists()


def test_closed_producer_and_decoders_precede_commit(tmp_path, monkeypatch):
    canvas = Canvas(1, 1)
    decoder = Mock()
    canvas._ctx.video_decoder_cache["test"] = decoder
    state = {"closed": False}

    def frames(*args, **kwargs):
        try:
            yield video._Shot(Image.new("RGBA", (1, 1)), 0.1)
        finally:
            state["closed"] = True

    original = sequence.rename_exclusive

    def commit(staging, destination):
        assert state["closed"]
        decoder.close.assert_called_once()
        assert not canvas._ctx.video_decoder_cache
        assert (staging / "manifest.json").is_file()
        original(staging, destination)

    monkeypatch.setattr(video, "_ordered_deck_shots", frames)
    monkeypatch.setattr(sequence, "rename_exclusive", commit)
    canvas.export_image_sequence(
        tmp_path / "closed", options=ImageSequenceOptions(fps=10, hold=0.1)
    )


def test_bounded_live_frame_retention(tmp_path, monkeypatch):
    references = []

    def frames(*args, **kwargs):
        for index in range(150):
            frame = Image.new("RGBA", (3, 3), (index, 0, 0, 128))
            references.append(weakref.ref(frame))
            gc.collect()
            assert sum(item() is not None for item in references) <= 3
            yield video._Shot(frame, 0.2)

    monkeypatch.setattr(video, "_ordered_deck_shots", frames)
    result = Canvas(3, 3).export_image_sequence(
        tmp_path / "bounded", options=ImageSequenceOptions(fps=10)
    )
    assert result.frame_count == 300
    gc.collect()
    assert not any(item() is not None for item in references)


@pytest.mark.parametrize("occupied", ["file", "directory", "empty", "symlink", "dangling"])
def test_actual_commit_preserves_concurrently_created_destination(occupied, tmp_path, monkeypatch):
    destination = tmp_path / "race"
    original = sequence.rename_exclusive

    def compete(staging, target):
        if occupied == "file":
            target.write_bytes(b"competitor")
        elif occupied in {"directory", "empty"}:
            target.mkdir()
            if occupied == "directory":
                (target / "sentinel").write_bytes(b"competitor")
        else:
            referent = tmp_path / "referent"
            if occupied == "symlink":
                referent.write_bytes(b"competitor")
            target.symlink_to(referent)
        original(staging, target)

    monkeypatch.setattr(sequence, "rename_exclusive", compete)
    with pytest.raises(FileExistsError):
        Canvas(1, 1).export_image_sequence(destination, options=ImageSequenceOptions(hold=0))
    assert os.path.lexists(destination)
    assert not list(tmp_path.glob(".quickthumb-images-*"))
    if occupied == "file":
        assert destination.read_bytes() == b"competitor"
    elif occupied == "directory":
        assert (destination / "sentinel").read_bytes() == b"competitor"
    elif occupied == "empty":
        assert list(destination.iterdir()) == []
    else:
        assert destination.is_symlink()


def test_two_real_exporters_publish_exactly_one_complete_sequence(tmp_path, monkeypatch):
    barrier = threading.Barrier(2)
    original = sequence.rename_exclusive

    def commit(staging, destination):
        barrier.wait(timeout=10)
        original(staging, destination)

    monkeypatch.setattr(sequence, "rename_exclusive", commit)

    def export(color):
        try:
            return (
                Canvas(1, 1)
                .background(color=color)
                .export_image_sequence(
                    tmp_path / "winner", options=ImageSequenceOptions(fps=10, hold=0.2)
                )
            )
        except FileExistsError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(export, ["#FF0000", "#0000FF"]))
    assert sum(result is not None for result in results) == 1
    assert len(list((tmp_path / "winner").iterdir())) == 3
    frames = decoded(tmp_path / "winner")
    assert frames in [[bytes([255, 0, 0, 255])] * 2, [bytes([0, 0, 255, 255])] * 2]
    assert not list(tmp_path.glob(".quickthumb-images-*"))


def test_ambiguous_commit_error_never_deletes_published_directory(tmp_path, monkeypatch):
    original = sequence.rename_exclusive
    error = OSError("ambiguous commit acknowledgment")

    def committed_then_failed(staging, destination):
        original(staging, destination)
        staging.mkdir()
        (staging / "foreign").write_bytes(b"do not delete replacement")
        raise error

    monkeypatch.setattr(sequence, "rename_exclusive", committed_then_failed)
    with pytest.raises(OSError) as caught:
        Canvas(1, 1).export_image_sequence(
            tmp_path / "published", options=ImageSequenceOptions(hold=0)
        )
    assert caught.value is error
    assert len(decoded(tmp_path / "published")) == 1
    assert (tmp_path / "published" / "manifest.json").is_file()
    assert (
        next(tmp_path.glob(".quickthumb-images-*/foreign")).read_bytes()
        == b"do not delete replacement"
    )


def test_staging_replacement_is_preserved_and_not_published(tmp_path, monkeypatch):
    original = video._PreparedAnimation.close

    def replace(prepared):
        original(prepared)
        staging = next(tmp_path.glob(".quickthumb-images-*"))
        staging.rename(tmp_path / "owned-moved")
        staging.mkdir()
        (staging / "foreign").write_bytes(b"competitor")

    monkeypatch.setattr(video._PreparedAnimation, "close", replace)
    with pytest.raises(RenderingError, match="staging directory changed"):
        Canvas(1, 1).export_image_sequence(
            tmp_path / "destination", options=ImageSequenceOptions(hold=0)
        )
    assert not (tmp_path / "destination").exists()
    assert next(tmp_path.glob(".quickthumb-images-*/foreign")).read_bytes() == b"competitor"


def test_worker_failure_closes_pool_and_leaves_no_output(tmp_path, monkeypatch):
    from quickthumb import _render_workers as workers

    original = workers.ParallelFrames.__exit__
    closed = []

    def close(self, *args):
        closed.append(self)
        original(self, *args)

    def fail(*args, **kwargs):
        raise RenderingError("worker failed")
        yield

    monkeypatch.setattr(workers.ParallelFrames, "frames", fail)
    monkeypatch.setattr(workers.ParallelFrames, "__exit__", close)
    with pytest.raises(RenderingError, match="worker failed"):
        animated_canvas().export_image_sequence(
            tmp_path / "worker", options=ImageSequenceOptions(fps=10, hold=0.1, workers=2)
        )
    assert len(closed) == 1
    assert list(tmp_path.iterdir()) == []


def test_real_spawn_failure_shuts_down_executor(tmp_path, monkeypatch):
    from quickthumb import _render_workers as workers

    asset = tmp_path / "source.png"
    Image.new("RGBA", (8, 6), "red").save(asset)
    source = Canvas(17, 9).image(str(asset), (1, 1), 8, 6, animation=Fade(duration=0.3))
    original_enter = workers.ParallelFrames.__enter__
    original_exit = workers.ParallelFrames.__exit__
    shutdown = []

    def enter(self):
        asset.unlink()  # Parent preparation succeeded; the spawned worker must fail.
        return original_enter(self)

    def exit_pool(self, *args):
        assert self.executor is not None
        original_exit(self, *args)
        shutdown.append(self.executor)

    monkeypatch.setattr(workers.ParallelFrames, "__enter__", enter)
    monkeypatch.setattr(workers.ParallelFrames, "__exit__", exit_pool)
    with pytest.raises((MissingAssetError, RenderingError, FileNotFoundError)):
        source.export_image_sequence(
            tmp_path / "worker", options=ImageSequenceOptions(fps=10, hold=0.1, workers=2)
        )
    assert shutdown == [None]
    assert list(tmp_path.iterdir()) == []


@pytest.mark.skipif(
    not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
    reason="video source needs FFmpeg/ffprobe",
)
def test_captioned_video_morph_timing_silent_output_and_decoder_closure(tmp_path, monkeypatch):
    source_path = tmp_path / "video.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=48x32:r=10:d=0.4",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=8000:duration=0.4",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(source_path),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )

    def scene(label):
        return Canvas(48, 32).video(
            str(source_path),
            (0, 0),
            48,
            32,
            motion_key="clip",
            captions=[{"text": label, "start": 0.1, "end": 0.3, "size": 8}],
        )

    first, second = scene("ONE"), scene("TWO")
    morph = Deck().slide(first).slide(second, transition=tr.Morph(duration=0.2))
    fade = Deck().slide(first).slide(second, transition=tr.Fade(duration=0.2))
    expected = reference(fade, hold=0)
    forbidden = Mock(side_effect=AssertionError("sequence must not mux embedded video audio"))
    monkeypatch.setattr(video, "_video_audio_schedule", forbidden)
    result = morph.export_image_sequence(
        tmp_path / "captions", options=ImageSequenceOptions(fps=10, hold=0)
    )
    assert decoded(tmp_path / "captions") == expected
    assert any(
        item.feature == "morph_caption_timing" and item.fallback == "fade"
        for item in result.capability_report
    )
    assert all(not canvas._ctx.video_decoder_cache for canvas in (first, second))
    assert {path.suffix for path in (tmp_path / "captions").iterdir()} == {".png", ".json"}
    assert len(set(expected)) > 2  # Captions and their fades actually changed the pixels.
    forbidden.assert_not_called()
    # Caption timing fallback is diagnostic under the existing video policy,
    # including strict policy. This exporter must preserve that exact behavior.
    strict = ExportPolicy(unsupported_motion="error")
    strict_result = morph.export_image_sequence(
        tmp_path / "strict-caption", options=ImageSequenceOptions(fps=10, hold=0), policy=strict
    )
    assert strict_result.capability_report == morph.validate_export("video", strict)
    assert decoded(tmp_path / "strict-caption") == expected


@pytest.mark.parametrize("format,extension", [("png", "png"), ("jpeg", "jpg"), ("webp", "webp")])
def test_repeated_shot_encodes_once_into_independent_files(
    format, extension, tmp_path, monkeypatch
):
    """A repeated canonical shot is encoded once into 90 independent frame files."""
    encoder = Mock(wraps=sequence._encode_image_frame)
    monkeypatch.setattr(sequence, "_encode_image_frame", encoder)
    Canvas(1, 1).export_image_sequence(tmp_path / "repeat", format=format)
    assert encoder.call_count == 1
    assert len(list((tmp_path / "repeat").glob(f"*.{extension}"))) == 90


@pytest.mark.parametrize("fail", [False, True])
@pytest.mark.parametrize("encoding", ["png", "webp"])
def test_encoder_metadata_is_suppressed_without_mutating_producer(fail, encoding, monkeypatch):
    """Lossless frame encoders retain hidden RGB without inheriting or mutating metadata."""
    frame = Image.new("RGBA", (1, 1), (32, 64, 96, 0))
    frame.info = {"icc_profile": b"profile", "exif": b"EXIF", "gamma": 0.45455}
    pnginfo = PngImagePlugin.PngInfo()
    pnginfo.add(b"sRGB", b"\0")
    frame.encoderinfo = {
        "icc_profile": b"encoder profile",
        "pnginfo": pnginfo,
        "exif": b"encoder EXIF",
        "transparency": 0,
        "dpi": (144, 144),
    }
    previous_info = frame.info.copy()
    previous_encoder = frame.encoderinfo
    if fail:
        monkeypatch.setattr(frame, "save", Mock(side_effect=OSError("PNG encoder failed")))
        with pytest.raises(OSError, match="PNG encoder failed"):
            sequence._encode_image_frame(frame, encoding=encoding, lossless=True)
    else:
        with Image.open(
            BytesIO(sequence._encode_image_frame(frame, encoding=encoding, lossless=True))
        ) as decoded_frame:
            assert decoded_frame.tobytes() == bytes([32, 64, 96, 0])
            assert not {"icc_profile", "exif", "xmp", "gamma", "srgb"} & decoded_frame.info.keys()
    assert frame.info == previous_info
    assert frame.encoderinfo is previous_encoder
    assert frame.tobytes() == bytes([32, 64, 96, 0])


def test_success_relinquishes_staging_without_cleanup(tmp_path, monkeypatch):
    cleanup = Mock(wraps=sequence.cleanup_owned_staging)
    monkeypatch.setattr(sequence, "cleanup_owned_staging", cleanup)
    result = Canvas(1, 1).export_image_sequence(
        tmp_path / "success", options=ImageSequenceOptions(hold=0)
    )
    assert result.frame_count == 1
    cleanup.assert_not_called()


def test_rejected_parallel_canvas_does_not_create_staging(tmp_path):
    class CustomCanvas(Canvas):
        pass

    with pytest.raises(ValidationError, match="built-in Canvas"):
        CustomCanvas(1, 1).export_image_sequence(
            tmp_path / "bad", options=ImageSequenceOptions(workers=2)
        )
    assert list(tmp_path.iterdir()) == []


def test_options_are_revalidated_and_other_option_models_rejected(tmp_path):
    canvas = Canvas(1, 1)
    invalid = ImageSequenceOptions.model_construct(fps=False)
    for options in (invalid, VideoOptions(), {"fps": 10}):
        with pytest.raises(ValidationError):
            canvas.export_image_sequence(tmp_path / "bad", options=cast(Any, options))
    assert list(tmp_path.iterdir()) == []


def test_still_png_export_keeps_numbered_deck_rasters(tmp_path):
    """Still PNG files retain Canvas pixels and numbered Deck destinations."""
    canvas = animated_canvas()
    still = tmp_path / "still.png"
    canvas.render(str(still))
    with Image.open(still) as image:
        assert image.tobytes() == canvas._render_to_image().tobytes()
    deck = Deck().slide(canvas)
    paths = deck.render(str(tmp_path / "slides.png"))
    assert len(paths) == 1
    assert len(list(tmp_path.glob("*.png"))) == 2
