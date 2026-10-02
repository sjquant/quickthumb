"""The scalar byte API and format-specific file options share one setup boundary."""

import inspect
import json
import math
import shutil
import subprocess
import weakref
from io import BytesIO
from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock

import pytest
from PIL import Image, ImageSequence
from quickthumb import AudioTrack, Canvas, Deck, Fade, GifOptions, VideoOptions
from quickthumb import _export_video as video
from quickthumb import transitions as tr
from quickthumb.errors import ValidationError


@pytest.mark.parametrize("owner", [Canvas, Deck])
def test_byte_signatures_preserve_existing_parameters_and_add_only_keyword_controls(owner):
    hold = "hold" if owner is Canvas else "slide_duration"
    methods = ["to_gif", "to_mp4" if owner is Canvas else "to_animated_mp4", "to_webm", "to_mov"]
    for method in methods:
        parameters = inspect.signature(getattr(owner, method)).parameters
        expected = [
            ("self", inspect.Parameter.empty),
            ("fps", 20.0 if method == "to_gif" else 30.0),
            (hold, 3.0),
        ]
        expected += (
            [("loop", 0), ("matte", "#000000")]
            if method == "to_gif"
            else [("matte", "#000000"), ("soundtrack", None), ("loop_audio", None)]
        )
        assert [
            (p.name, p.default) for p in parameters.values() if p.kind == p.POSITIONAL_OR_KEYWORD
        ] == expected
        old_names = [name for name, _ in expected]
        old_names += ["transparent", "policy"] if method in ("to_webm", "to_mov") else ["policy"]
        assert list(parameters)[: len(old_names)] == old_names
        added = {"workers": 1, "quality": "standard"}
        if method == "to_gif":
            added.update(max_size=None, colors=None)
        for name, default in added.items():
            assert parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
            assert parameters[name].default == default
        assert set(parameters) == {name for name, _ in expected} | set(added) | {"policy"} | (
            {"transparent"} if method in ("to_webm", "to_mov") else set()
        )
    assert inspect.signature(owner.to_webm, eval_str=True) == inspect.signature(
        owner.to_mov, eval_str=True
    )
    assert inspect.signature(owner.to_webm).parameters["transparent"].default is False
    assert list(inspect.signature(Deck.to_mp4).parameters) == [
        "self",
        "fps",
        "slide_duration",
        "policy",
    ]
    assert list(inspect.signature(Deck.render_mp4).parameters) == [
        "self",
        "output_path",
        "default_duration",
        "fps",
    ]


@pytest.mark.parametrize("options", [GifOptions, VideoOptions])
def test_hold_roundtrips_omit_only_the_default(options):
    assert options().hold == 3.0
    assert "hold" not in options().model_dump()
    assert "hold" not in json.loads(options(hold=3).model_dump_json())
    assert options.model_validate_json(options().model_dump_json()).hold == 3.0
    for hold in (0, 0.125, 2):
        configured = options(hold=hold)
        assert configured.model_dump()["hold"] == hold
        assert options.model_validate_json(configured.model_dump_json()).hold == hold
    assert options.model_json_schema()["properties"]["hold"] == {
        "default": 3.0,
        "minimum": 0,
        "title": "Hold",
        "type": "number",
    }
    with pytest.raises(ValidationError, match="slide_duration"):
        options.model_validate({"slide_duration": 1})


@pytest.mark.parametrize("options", [GifOptions, VideoOptions])
@pytest.mark.parametrize("hold", [None, True, False, "0.2", -0.1, math.inf, -math.inf, math.nan])
def test_hold_model_validation_is_strict_finite_and_nonnegative(options, hold):
    with pytest.raises(ValidationError, match="hold"):
        options.model_validate({"hold": hold})


@pytest.mark.parametrize(
    "field,value",
    [
        ("fps", True),
        ("fps", "10"),
        ("loop", True),
        ("loop", "2"),
        ("colors", "2"),
        ("max_size", ["4", "4"]),
    ],
)
def test_model_coercion_does_not_leak_into_raw_gif_arguments(field, value, tmp_path):
    options = GifOptions.model_validate({field: value, "hold": 0.1})
    Canvas(4, 4).render(tmp_path / "coerced.gif", animation=options)
    with pytest.raises(ValidationError):
        Canvas(4, 4).to_gif(hold=0.1, **{field: value})


@pytest.mark.parametrize("options,format", [(GifOptions, "gif"), (VideoOptions, "webm")])
@pytest.mark.parametrize(
    "field,value",
    [
        ("fps", True),
        ("fps", "10"),
        ("hold", False),
        ("hold", "0.2"),
        ("hold", -0.1),
        ("hold", math.inf),
        ("workers", True),
        ("workers", "2"),
        ("workers", 0),
        ("quality", None),
    ],
)
@pytest.mark.parametrize("constructor", ["construct", "copy"])
def test_invalid_constructed_model_values_are_not_recoerced(
    options, format, field, value, constructor, tmp_path
):
    invalid = (
        options.model_construct(**{field: value})
        if constructor == "construct"
        else options().model_copy(update={field: value})
    )
    with pytest.raises(ValidationError):
        Canvas(4, 4).render(tmp_path / f"invalid.{format}", animation=invalid)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("kind", ["canvas", "deck"])
@pytest.mark.parametrize("format", ["gif", "mp4", "webm", "mov"])
@pytest.mark.parametrize(
    "kwargs",
    [
        {"workers": True},
        {"workers": "2"},
        {"workers": 0},
        {"workers": 9},
        {"quality": None},
        {"quality": "low"},
    ],
)
def test_public_byte_render_controls_reject_invalid_values(kind, format, kwargs):
    canvas = Canvas(4, 4)
    source = canvas if kind == "canvas" else Deck().slide(canvas)
    method = "to_animated_mp4" if kind == "deck" and format == "mp4" else f"to_{format}"
    with pytest.raises(ValidationError):
        getattr(source, method)(**kwargs)


@pytest.mark.parametrize("format", ["webm", "mov"])
@pytest.mark.parametrize("transparent", [None, 0, 1, "true"])
def test_transparent_remains_strict_for_constructed_models_and_bytes(format, transparent, tmp_path):
    with pytest.raises(ValidationError, match="transparent"):
        getattr(Canvas(4, 4), f"to_{format}")(transparent=transparent)
    with pytest.raises(ValidationError, match="transparent"):
        Canvas(4, 4).render(
            tmp_path / f"invalid.{format}",
            animation=VideoOptions.model_construct(transparent=transparent),
        )


def _scene():
    return Canvas(16, 12).shape(
        "rectangle", (2, 2), 10, 7, "#E53B7580", animation=Fade(duration=0.2)
    )


@pytest.mark.parametrize("kind", ["canvas", "deck"])
@pytest.mark.parametrize("quality,workers", [("standard", 1), ("high", 2)])
def test_gif_file_and_byte_controls_match_encoded_pixels_timing_and_receipt(
    kind, quality, workers, tmp_path
):
    canvas = _scene()
    source = canvas if kind == "canvas" else Deck().slide(canvas, transition=tr.Cut())
    options = GifOptions(
        fps=10,
        hold=0.2,
        loop=2,
        matte="#124578",
        max_size=(8, 8),
        colors=4,
        quality=quality,
        workers=workers,
    )
    destination = tmp_path / "file.gif"
    receipt = source.export(destination, animation=options)
    hold_kwargs: dict[str, Any] = {("hold" if kind == "canvas" else "slide_duration"): options.hold}
    data = source.to_gif(
        **hold_kwargs,
        fps=10,
        loop=2,
        matte=options.matte,
        max_size=(8, 8),
        colors=4,
        quality=quality,
        workers=workers,
    )
    assert data == destination.read_bytes()
    with Image.open(BytesIO(data)) as encoded:
        assert encoded.size == (8, 6)
        assert encoded.info["loop"] == 2
        frames = [frame.copy() for frame in ImageSequence.Iterator(encoded)]
        duration = sum(frame.info["duration"] for frame in frames) / 1000
        assert len(encoded.getcolors(256) or []) <= 4
        assert receipt.timing_metrics.duration == duration == 0.4
        assert receipt.timing_metrics.frame_count == len(frames)


@pytest.mark.parametrize("surface", ["file", "bytes"])
@pytest.mark.parametrize("format", ["mp4", "webm", "mov"])
def test_deck_schedule_is_synchronous_once_and_used_before_prepared_entry(
    surface, format, tmp_path, monkeypatch
):
    deck = Deck().slide(Canvas(4, 4), transition=tr.Cut())
    events = []

    def schedule(hold):
        events.append(("schedule", hold))
        return [0.45], [0.45]

    def enter(prepared):
        assert events == [("schedule", 0.15)]
        assert prepared._slide_duration == 0.15
        assert prepared._slide_durations == [0.45]
        events.append("enter")
        return original_enter(prepared)

    def encode(
        prepared,
        format,
        path,
        soundtrack,
        loop_audio,
        slide_audio,
        offsets,
        durations,
        total,
        **kwargs,
    ):
        assert events == [("schedule", 0.15), "enter"]
        assert slide_audio == [None] and durations == [0.45]
        list(prepared.frame_runs())
        facts = prepared.frame_facts
        assert facts.duration == 0.5
        Path(path).write_bytes(b"encoded")
        return facts

    original_enter = video._PreparedAnimation.__enter__
    monkeypatch.setattr(deck, "_animation_audio_schedule", schedule)
    monkeypatch.setattr(video._PreparedAnimation, "__enter__", enter)
    monkeypatch.setattr(video, "_encode_prepared_video", encode)
    if surface == "file":
        receipt = deck.export(
            tmp_path / f"file.{format}", animation=VideoOptions(fps=10, hold=0.15)
        )
        assert receipt.timing_metrics.duration == 0.5
    else:
        method = "to_animated_mp4" if format == "mp4" else f"to_{format}"
        assert getattr(deck, method)(fps=10, slide_duration=0.15) == b"encoded"
    assert events == [("schedule", 0.15), "enter"]


@pytest.mark.parametrize(
    "options,format",
    [(GifOptions, "mp4"), (GifOptions, "webm"), (GifOptions, "mov"), (VideoOptions, "gif")],
)
def test_wrong_option_family_and_subclasses_reject_before_narration_probe(
    options, format, tmp_path, monkeypatch
):
    class CustomOptions(options):
        tag: str = "subclass"

    deck = Deck().slide(Canvas(4, 4), audio=str(tmp_path / "missing.wav"))
    schedule = Mock(side_effect=AssertionError("must not probe"))
    monkeypatch.setattr(deck, "_animation_audio_schedule", schedule)
    for configured in (options(), CustomOptions()):
        with pytest.raises(ValidationError, match="only supported"):
            deck.render(tmp_path / f"file.{format}", animation=configured)
    schedule.assert_not_called()


@pytest.mark.parametrize("surface", ["file", "bytes"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("slide_durations", []),
        ("audio_durations", []),
        ("audio_offsets", []),
        ("audio_timeline_duration", 0.0),
    ],
)
@pytest.mark.parametrize("format", ["gif", "webm"])
def test_schedule_rejects_all_mixed_precomputed_inputs_before_call(
    surface, field, value, format, monkeypatch, tmp_path
):
    scheduler = Mock(side_effect=AssertionError("must not call"))
    monkeypatch.setattr(
        video._PreparedAnimation, "__enter__", Mock(side_effect=AssertionError("must not enter"))
    )
    kwargs: dict[str, Any] = {field: value, "audio_schedule": scheduler}
    with pytest.raises(ValidationError, match="precomputed timing"):
        if surface == "file":
            video.write_animation(
                [Canvas(4, 4)], [None], str(tmp_path / f"file.{format}"), format, **kwargs
            )
        else:
            video.export_animation_bytes([Canvas(4, 4)], [None], format, **kwargs)
    scheduler.assert_not_called()
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("surface", ["file", "bytes"])
def test_schedule_error_and_invalid_return_happen_before_rendering_or_temp_output(
    surface, monkeypatch, tmp_path
):
    monkeypatch.setattr(
        video._PreparedAnimation, "__enter__", Mock(side_effect=AssertionError("must not enter"))
    )
    monkeypatch.setattr(
        video.tempfile, "mkstemp", Mock(side_effect=AssertionError("must not create output"))
    )
    for scheduler, error, match in [
        (Mock(side_effect=RuntimeError("narration probe")), RuntimeError, "narration probe"),
        (Mock(return_value=([None], [0])), ValidationError, "audio duration"),
    ]:
        kwargs: dict[str, Any] = {"audio_schedule": scheduler, "slide_audio": [None]}
        with pytest.raises(error, match=match):
            if surface == "file":
                video.write_animation(
                    [Canvas(4, 4)], [None], str(tmp_path / "file.webm"), "webm", **kwargs
                )
            else:
                video.export_animation_bytes([Canvas(4, 4)], [None], "webm", **kwargs)
        scheduler.assert_called_once_with(3.0)


def test_setup_consumes_and_does_not_retain_the_schedule_provider():
    class Schedule:
        def __call__(self, hold):
            return [None], [hold]

    schedule = Schedule()
    reference = weakref.ref(schedule)
    prepared, settings = video._setup_animation(
        [Canvas(4, 4)], [None], "webm", slide_audio=[None], audio_schedule=schedule
    )
    del schedule
    assert reference() is None
    assert settings.audio_durations == [3.0]
    assert prepared._slide_durations == [None]
    assert all(not callable(value) for value in vars(settings).values())


@pytest.mark.parametrize("surface", ["file", "bytes"])
def test_deck_gif_ignores_narration_and_explicit_durations(surface, monkeypatch, tmp_path):
    deck = Deck().slide(
        Canvas(4, 4), transition=tr.Cut(), duration=7, audio=str(tmp_path / "missing.wav")
    )
    scheduler = Mock(side_effect=AssertionError("GIF must not resolve narration"))
    monkeypatch.setattr(deck, "_animation_audio_schedule", scheduler)
    if surface == "file":
        path = tmp_path / "file.gif"
        result = deck.export(path, animation=GifOptions(hold=0.2))
        assert result.timing_metrics.duration == 0.2
        data = path.read_bytes()
    else:
        data = deck.to_gif(slide_duration=0.2)
    with Image.open(BytesIO(data)) as encoded:
        assert encoded.info["duration"] == 200
    scheduler.assert_not_called()


@pytest.mark.parametrize("surface", ["file", "bytes"])
@pytest.mark.parametrize("format", ["mp4", "webm", "mov"])
def test_deck_video_preserves_zero_hold_default_audio_bed_rejection(surface, format, tmp_path):
    deck = Deck().slide(Canvas(4, 4), transition=tr.Cut())
    with pytest.raises(ValidationError, match="Deck audio duration must be finite and > 0"):
        if surface == "file":
            deck.export(tmp_path / f"file.{format}", animation=VideoOptions(hold=0))
        else:
            method = "to_animated_mp4" if format == "mp4" else f"to_{format}"
            getattr(deck, method)(slide_duration=0)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "input_kind,explicit,expected",
    [
        ("string", None, True),
        ("string", False, False),
        ("track", None, False),
        ("track", True, True),
        ("dict", None, False),
        ("dict", True, True),
    ],
)
def test_soundtrack_loop_resolution_precedes_coercion_and_preserves_false(
    input_kind, explicit, expected, tmp_path
):
    path = tmp_path / "sound.wav"
    path.touch()
    soundtrack = (
        str(path)
        if input_kind == "string"
        else AudioTrack(path=str(path), loop=False)
        if input_kind == "track"
        else {"path": str(path), "loop": False}
    )
    _, settings = video._setup_animation(
        [Canvas(4, 4)], [None], "webm", soundtrack=soundtrack, loop_audio=explicit
    )
    assert settings.loop_audio is expected
    assert settings.soundtrack == AudioTrack(path=str(path), loop=False)
    _, configured = video._setup_animation(
        [Canvas(4, 4)],
        [None],
        "webm",
        loop_audio=True,
        animation=VideoOptions(soundtrack=AudioTrack(path=str(path), loop=True), loop_audio=False),
    )
    assert configured.loop_audio is False


def test_private_no_provider_preserves_precomputed_video_schedule_and_gif_distinction(tmp_path):
    prepared, settings = video._setup_animation(
        [Canvas(4, 4)],
        [None],
        "webm",
        slide_duration=0.2,
        slide_audio=[None],
        slide_durations=[0.4],
        audio_durations=[0.4],
        audio_offsets=[0.1],
        audio_timeline_duration=0.5,
    )
    assert prepared._slide_durations == [0.4]
    assert settings.audio_offsets == [0.1] and settings.audio_timeline_duration == 0.5
    path = tmp_path / "file.gif"
    facts = video.write_animation(
        [Canvas(4, 4)],
        [None],
        str(path),
        "gif",
        slide_duration=0.2,
        slide_audio=[None],
        slide_durations=[7],
        audio_durations=[7],
    )
    assert facts.duration == 0.2
    data = video.export_animation_bytes(
        [Canvas(4, 4)],
        [None],
        "gif",
        slide_duration=0.2,
        slide_audio=[None],
        slide_durations=[7],
        audio_durations=[7],
    )
    with Image.open(BytesIO(data)) as encoded:
        assert encoded.info["duration"] == 7000


@pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="requires FFmpeg"
)
@pytest.mark.parametrize("kind", ["canvas", "deck"])
@pytest.mark.parametrize("format", ["mp4", "webm", "mov"])
def test_video_file_and_byte_quality_workers_hold_and_alpha_match_actual_output(
    kind, format, tmp_path
):
    canvas = _scene()
    source = canvas if kind == "canvas" else Deck().slide(canvas, transition=tr.Cut())
    transparent = format != "mp4"
    options = VideoOptions(fps=10, hold=0.2, quality="high", workers=2, transparent=transparent)
    file_path = tmp_path / f"file.{format}"
    receipt = source.export(file_path, animation=options)
    kwargs = {
        ("hold" if kind == "canvas" else "slide_duration"): 0.2,
        "fps": 10,
        "quality": "high",
        "workers": 2,
    }
    if transparent:
        kwargs.update(transparent=True, matte="not-a-color")
    method = "to_animated_mp4" if kind == "deck" and format == "mp4" else f"to_{format}"
    byte_path = tmp_path / f"bytes.{format}"
    byte_path.write_bytes(getattr(source, method)(**kwargs))
    decoded = []
    for path in (file_path, byte_path):
        decoder = ["-c:v", "libvpx-vp9"] if format == "webm" else []
        decoded.append(
            subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    *decoder,
                    "-i",
                    str(path),
                    "-map",
                    "0:v",
                    "-f",
                    "rawvideo",
                    "-pix_fmt",
                    "rgba",
                    "-",
                ],
                check=True,
                capture_output=True,
                timeout=30,
            ).stdout
        )
        probe = json.loads(
            subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-count_frames",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=nb_read_frames",
                    "-of",
                    "json",
                    str(path),
                ],
                check=True,
                capture_output=True,
                timeout=30,
            ).stdout
        )
        assert int(probe["streams"][0]["nb_read_frames"]) == receipt.timing_metrics.frame_count
    assert decoded[0] == decoded[1]
    assert receipt.timing_metrics.duration == 0.4
    assert receipt.timing_metrics.frame_count == 4
    if transparent:
        assert min(decoded[0][3::4]) == 0
        assert 0 < max(decoded[0][3::4]) < 255


@pytest.mark.parametrize("surface", ["file", "bytes"])
def test_unknown_format_never_consumes_schedule(surface, tmp_path):
    scheduler = Mock(side_effect=AssertionError("must not probe"))
    with pytest.raises(ValidationError, match="Unsupported animation format"):
        if surface == "file":
            video.write_animation(
                [Canvas(4, 4)],
                [None],
                str(tmp_path / "file.unknown"),
                cast(Any, "unknown"),
                audio_schedule=scheduler,
            )
        else:
            video.export_animation_bytes(
                [Canvas(4, 4)], [None], cast(Any, "unknown"), audio_schedule=scheduler
            )
    scheduler.assert_not_called()


@pytest.mark.parametrize("surface", ["file", "bytes"])
def test_deck_keeps_narration_error_ahead_of_invalid_hold(surface, tmp_path):
    from quickthumb.errors import MissingAssetError

    deck = Deck().slide(Canvas(4, 4), audio=str(tmp_path / "missing.wav"))
    with pytest.raises(MissingAssetError, match="Audio file"):
        if surface == "file":
            deck.render(
                tmp_path / "file.webm", animation=VideoOptions.model_construct(hold="invalid")
            )
        else:
            deck.to_webm(slide_duration=cast(Any, "invalid"))


@pytest.mark.parametrize("surface", ["file", "bytes"])
def test_private_gif_callback_is_never_invoked(surface, tmp_path):
    scheduler = Mock(side_effect=AssertionError("GIF must not probe"))
    if surface == "file":
        facts = video.write_animation(
            [Canvas(4, 4)],
            [None],
            str(tmp_path / "file.gif"),
            "gif",
            slide_duration=0.2,
            audio_schedule=scheduler,
        )
        assert facts.duration == 0.2
    else:
        assert video.export_animation_bytes(
            [Canvas(4, 4)], [None], "gif", slide_duration=0.2, audio_schedule=scheduler
        ).startswith(b"GIF")
    scheduler.assert_not_called()


@pytest.mark.parametrize("options,format", [(GifOptions, "gif"), (VideoOptions, "mov")])
def test_valid_option_subclasses_with_extra_fields_are_preserved(options, format):
    class CustomOptions(options):
        tag: str = "subclass"

    prepared, settings = video._setup_animation(
        [Canvas(4, 4)], [None], format, animation=CustomOptions(fps=10, hold=0.2)
    )
    assert prepared.fps == 10 and prepared._slide_duration == 0.2
    assert settings.transparent is False


@pytest.mark.parametrize("format,fps", [("gif", 20), ("mp4", 30), ("webm", 30), ("mov", 30)])
def test_none_frame_rate_uses_format_default_without_hiding_zero(format, fps):
    prepared, settings = video._setup_animation(
        [Canvas(4, 4)], [None], format, fps=None, slide_duration=0, loop=0, loop_audio=False
    )
    assert prepared.fps == fps and prepared._slide_duration == 0
    assert settings.loop == 0 and settings.loop_audio is False
    with pytest.raises(ValidationError, match="fps must be > 0"):
        video._setup_animation([Canvas(4, 4)], [None], format, fps=0)


@pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="requires FFmpeg"
)
@pytest.mark.parametrize("hold", [0, 0.15])
def test_deck_video_nondefault_hold_keeps_inferred_and_explicit_narration_timing(hold, tmp_path):
    import wave

    narration = tmp_path / "narration.wav"
    with wave.open(str(narration), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b"\x01\x00" * 2400)
    deck = (
        Deck()
        .slide(Canvas(4, 4).background(color="#123456"), transition=tr.Cut(), audio=str(narration))
        .slide(
            Canvas(4, 4).background(color="#654321"),
            transition=tr.Cut(),
            audio=str(narration),
            duration=0.2,
        )
    )
    if hold:
        deck.slide(Canvas(4, 4).background(color="#456789"), transition=tr.Cut())
    file_path = tmp_path / "file.mp4"
    receipt = deck.export(file_path, animation=VideoOptions(fps=20, hold=hold))
    byte_path = tmp_path / "bytes.mp4"
    byte_path.write_bytes(deck.to_animated_mp4(fps=20, slide_duration=hold))
    assert receipt.timing_metrics.duration == pytest.approx(0.5 + hold)
    assert receipt.timing_metrics.frame_count == round((0.5 + hold) * 20)
    outputs = []
    for path in (file_path, byte_path):
        outputs.append(
            subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-i",
                    str(path),
                    "-map",
                    "0:v",
                    "-f",
                    "rawvideo",
                    "-pix_fmt",
                    "rgb24",
                    "-",
                ],
                check=True,
                capture_output=True,
                timeout=30,
            ).stdout
        )
        audio = subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                str(path),
                "-map",
                "0:a",
                "-f",
                "s16le",
                "-ar",
                "8000",
                "-ac",
                "1",
                "-",
            ],
            check=True,
            capture_output=True,
            timeout=30,
        ).stdout
        assert len(audio) >= round((0.5 + hold) * 8000) * 2
    assert outputs[0] == outputs[1]
    assert len(outputs[0]) == receipt.timing_metrics.frame_count * 4 * 4 * 3
