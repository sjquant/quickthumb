"""Byte-level compatibility and bounded retention for incremental Pillow GIFs."""

import gc
import random
import weakref
from io import BytesIO

import pytest
from PIL import GifImagePlugin, Image, ImageDraw, ImageSequence
from quickthumb import Canvas, Deck, ExportPolicy, Fade, GifOptions
from quickthumb import _export_video as video
from quickthumb import _gif as gif
from quickthumb.errors import RenderingError
from quickthumb.transitions import Fade as CrossFade


def legacy_encode(shots, loop=0, *, max_size=None, colors=None):
    """Frozen pre-#153 implementation, without its memory-budget rejection."""
    frames, durations = [], []
    clock = 0.0
    emitted_cs = 0
    target_size = None
    for shot in shots:
        if target_size is None:
            target_size = video._gif_target_size(shot.frame.size, max_size)
        frame = shot.frame
        if frame.size != target_size:
            frame = frame.resize(target_size, Image.Resampling.LANCZOS)
        clock += shot.duration
        duration_cs = max(1, round(clock * 100) - emitted_cs)
        emitted_cs += duration_cs
        frames.append(frame.quantize(colors=colors or 256))
        durations.append(duration_cs * 10)
    output = BytesIO()
    frames[0].save(
        output,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=durations if len(durations) > 1 else durations[0],
        loop=loop,
        optimize=True,
    )
    return output.getvalue()


def patterned_frame(index, size=(37, 29)):
    image = Image.new("RGB", size, (22, 30, 45))
    draw = ImageDraw.Draw(image)
    draw.rectangle((index % 11, 3, index % 11 + 9, 18), fill=(230, index * 29 % 256, 50))
    return image


@pytest.mark.parametrize("indices", [[0], [0, 0, 0], [0, 1], [0, 0, 1, 1, 2, 2], [0, 1, 0]])
@pytest.mark.parametrize("size", [(15, 14), (37, 29), (512, 512)])
def test_single_and_duplicate_frames_match_legacy_bytes(indices, size):
    shots = [video._Shot(patterned_frame(i, size), 1 / 12) for i in indices]
    assert video._encode_gif(iter(shots), 3) == legacy_encode(shots, 3)


@pytest.mark.parametrize("colors", [None, 2, 3, 16, 64, 255, 256])
@pytest.mark.parametrize("max_size", [None, (17, 19), (100, 100)])
def test_palette_resize_and_loop_options_match_legacy_bytes(colors, max_size):
    randomizer = random.Random(2026)
    images = [Image.frombytes("RGB", (31, 23), randomizer.randbytes(31 * 23 * 3)) for _ in range(3)]
    images.append(patterned_frame(3, (43, 19)))
    shots = [video._Shot(image, 0.037) for image in images]
    kwargs = {"max_size": max_size, "colors": colors}
    actual = video._encode_gif(iter(shots), 65535, **kwargs)
    assert actual == legacy_encode(shots, 65535, **kwargs)
    with Image.open(BytesIO(actual)) as image:
        assert image.info["loop"] == 65535
        assert image.size == video._gif_target_size((31, 23), max_size)


def _palette_image(indices, palette):
    image = Image.new("P", (len(indices), 20))
    image.putpalette(palette)
    image.putdata(indices * 20)
    return image


@pytest.mark.parametrize("scenario", ["same", "different", "equivalent", "full", "sparse"])
def test_palette_delta_branches_match_pillow(scenario):
    palette = [channel for i in range(256) for channel in (i, (i * 7) % 256, (i * 13) % 256)]
    first = _palette_image(list(range(256)), palette)
    if scenario == "same":
        first = _palette_image([0, 1, 2, 3] * 16, palette)
        second = first.copy()
        second.putpixel((17, 8), 2)
    elif scenario == "different":
        second = first.copy()
        second.putpalette(list(reversed(palette)))
    elif scenario == "equivalent":
        second = _palette_image(
            list(reversed(range(256))),
            [c for i in reversed(range(256)) for c in palette[3 * i : 3 * i + 3]],
        )
    elif scenario == "full":
        second = _palette_image(list(reversed(range(256))), palette)
    else:
        first = _palette_image([0, 40, 90, 150] * 16, palette)
        second = first.copy()
        second.putpixel((17, 8), 90)
    frames = [first, second, second.copy(), first.copy()]
    expected = BytesIO()
    frames[0].save(
        expected,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=[30, 40, 30, 40],
        loop=0,
        optimize=True,
    )
    actual = BytesIO()
    gif.write_gif_frames(zip(frames, [30, 40, 30, 40], strict=True), actual, 0)
    assert actual.getvalue() == expected.getvalue()


@pytest.mark.parametrize("fps", [12, 29.97, 30, 100])
def test_centisecond_clock_and_fractional_holds_match_legacy(fps):
    durations = [1 / fps] * 61 + [0.004, 0.011, 1.234]
    shots = [video._Shot(patterned_frame(i), duration) for i, duration in enumerate(durations)]
    actual = video._encode_gif(iter(shots), 0)
    assert actual == legacy_encode(shots)
    with Image.open(BytesIO(actual)) as image:
        encoded_ms = sum(frame.info["duration"] for frame in ImageSequence.Iterator(image))
    assert encoded_ms == round(sum(durations) * 100) * 10


def test_output_is_written_before_input_is_exhausted(monkeypatch):
    produced = 0
    writes = []
    original = GifImagePlugin._write_frame_data

    def record(output, frame, offset, info):
        writes.append(produced)
        return original(output, frame, offset, info)

    def shots():
        nonlocal produced
        for i in range(100):
            produced += 1
            yield video._Shot(patterned_frame(i), 0.03)

    monkeypatch.setattr(GifImagePlugin, "_write_frame_data", record)
    video._encode_gif(shots(), 0)
    assert writes == list(range(2, 101)) + [100]


def test_uncompressed_frame_retention_is_bounded(monkeypatch):
    references = []
    counts = []
    original = Image.Image._new

    def track(self, core):
        image = original(self, core)
        references.append(weakref.ref(image))
        return image

    def shots():
        for i in range(600):
            if i % 100 == 0:
                gc.collect()
                references[:] = [reference for reference in references if reference() is not None]
                counts.append(len(references))
            yield video._Shot(patterned_frame(i), 0.01)

    monkeypatch.setattr(Image.Image, "_new", track)
    result = video._encode_gif(shots(), 0)
    assert result.startswith(b"GIF89a")
    assert max(counts) < 16
    assert max(counts[1:]) - min(counts[1:]) < 4


def test_empty_input_has_actionable_error():
    with pytest.raises(RenderingError, match="no frames"):
        video._encode_gif([], 0)


@pytest.mark.parametrize("reduced_motion", [False, True])
def test_public_deck_bytes_match_legacy(monkeypatch, reduced_motion):
    deck = (
        Deck(93, 51)
        .slide(
            Canvas(93, 51)
            .background(color="#123456")
            .shape("rectangle", (5, 7), 30, 20, "#FF2345", animation=Fade(duration=0.3))
        )
        .slide(Canvas(71, 39).background(color="#89ABCD"), transition=CrossFade(duration=0.4))
    )
    policy = ExportPolicy(reduced_motion=reduced_motion)
    actual = deck.to_gif(fps=12, slide_duration=0.15, loop=2, policy=policy)
    monkeypatch.setattr(video, "_encode_gif", legacy_encode)
    assert actual == deck.to_gif(fps=12, slide_duration=0.15, loop=2, policy=policy)


def test_file_output_matches_bytes_without_ffmpeg(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path))
    canvas = Canvas(45, 23).background(color="#AABBCC")
    options = GifOptions(fps=12, loop=2)
    path = tmp_path / "stream.gif"
    canvas.render(str(path), animation=options)
    assert path.read_bytes() == canvas.to_gif(fps=12, loop=2)


def test_failed_producer_preserves_destination_and_closes_decoders(monkeypatch, tmp_path):
    closed = []

    def fail(*args, **kwargs):
        yield video._Shot(patterned_frame(0), 0.1)
        yield video._Shot(patterned_frame(1), 0.1)
        raise RuntimeError("producer failed")

    monkeypatch.setattr(video, "_deck_shots", fail)
    monkeypatch.setattr(video, "_close_video_decoders", lambda canvases: closed.extend(canvases))
    output = tmp_path / "result.gif"
    output.write_bytes(b"previous gif")
    canvas = Canvas(37, 29)
    with pytest.raises(RuntimeError, match="producer failed"):
        video.write_animation([canvas], [None], str(output), "gif")
    assert output.read_bytes() == b"previous gif"
    assert closed == [canvas]
    assert list(tmp_path.iterdir()) == [output]
