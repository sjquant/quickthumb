"""Pixel and real VP9-alpha regressions, independent of container metadata."""

import math
import shutil
import subprocess
from pathlib import Path
from typing import cast

import pytest
from PIL import Image, ImageChops, ImageDraw
from quickthumb import Canvas, Fade, VideoOptions
from quickthumb import _export_video as video
from quickthumb import transitions as tr
from quickthumb._render_workers import _CanvasSpec, _FrameRenderer

HAS_FFMPEG = shutil.which("ffmpeg") is not None
QUALITIES: tuple[video.AnimationQuality, ...] = ("standard", "high")
TRANSITIONS = [
    None,
    tr.Cut(),
    tr.Fade(),
    tr.Random(),
    tr.Morph(),
    tr.Push(),
    tr.Cover(),
    tr.Uncover(),
    tr.Zoom(),
    tr.Newsflash(),
    tr.Wipe(),
    tr.Split(),
    tr.Blinds(),
    tr.Checker(),
    tr.Comb(),
    tr.Circle(),
    tr.Diamond(),
    tr.Wheel(),
    tr.Wedge(),
    tr.Dissolve(),
]


def decode(path: Path, size: tuple[int, int]) -> list[Image.Image]:
    # FFmpeg's native VP9 decoder can discard alpha. libvpx decodes the
    # Matroska BlockAdditional alpha plane; alpha_mode/pix_fmt prove nothing.
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-c:v", "libvpx-vp9", "-i", str(path),
         "-map", "0:v", "-vsync", "0", "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
        check=True, capture_output=True, timeout=30,
    ).stdout  # fmt: skip
    stride = size[0] * size[1] * 4
    assert raw and len(raw) % stride == 0
    return [Image.frombytes("RGBA", size, raw[i : i + stride]) for i in range(0, len(raw), stride)]


def pixel(image, xy=(0, 0)) -> tuple[int, int, int, int]:
    return cast(tuple[int, int, int, int], image.getpixel(xy))


def blend_oracle(old, new, weight):
    alpha = old[3] * (1 - weight) + new[3] * weight
    colors = [
        round((old[i] * old[3] * (1 - weight) + new[i] * new[3] * weight) / alpha) if alpha else 0
        for i in range(3)
    ]
    return (*colors, round(alpha))


def over_oracle(back, front):
    alpha = front[3] + back[3] * (1 - front[3] / 255)
    return (
        *(
            round((front[i] * front[3] + back[i] * back[3] * (1 - front[3] / 255)) / alpha)
            for i in range(3)
        ),
        round(alpha),
    )


def assert_pixel(actual, expected, tolerance=1):
    assert all(abs(a - b) <= tolerance for a, b in zip(actual, expected, strict=True)), (
        actual,
        expected,
    )


@pytest.mark.parametrize(
    "old,new",
    [
        ((255, 0, 0, 128), (0, 0, 255, 64)),
        ((11, 201, 92, 1), (249, 62, 151, 3)),
        ((255, 0, 0, 0), (0, 0, 255, 128)),
        ((123, 201, 92, 0), (24, 62, 151, 0)),
    ],
)
@pytest.mark.parametrize("weight", [0.0, 0.25, 0.5, 0.75, 1.0])
def test_premultiplied_blend_uses_linear_alpha_without_hidden_color(old, new, weight):
    actual = video._blend_rgba(
        Image.new("RGBA", (1, 1), old), Image.new("RGBA", (1, 1), new), weight
    )
    assert_pixel(pixel(actual), blend_oracle(old, new, weight))


def test_fractional_mask_uses_same_premultiplied_oracle():
    old, new = (255, 0, 0, 128), (0, 0, 255, 64)
    mask = Image.frombytes("L", (4, 1), bytes([0, 64, 128, 255]))
    actual = video._blend_rgba(Image.new("RGBA", (4, 1), old), Image.new("RGBA", (4, 1), new), mask)
    for x, value in enumerate([0, 64, 128, 255]):
        assert_pixel(pixel(actual, (x, 0)), blend_oracle(old, new, value / 255))


@pytest.mark.parametrize("quality", QUALITIES)
def test_conform_skips_only_export_matte_and_preserves_letterboxing(quality):
    canvas = Canvas(32, 32).background(color="#FF000080")
    raw = video._SlideAnimator(canvas, {}, quality=quality).final_export_frame()
    fitted = video._conform(raw, (64, 32), None)
    assert fitted.mode == "RGBA"
    assert pixel(fitted, (4, 16))[3] == 0
    assert pixel(fitted, (32, 16)) == (255, 0, 0, 128)
    assert pixel(video._conform(raw, (32, 32), None)) == (255, 0, 0, 128)
    opaque = video._conform(raw, (32, 32), (20, 40, 60))
    assert opaque.mode == "RGB" and opaque.getpixel((0, 0)) == (138, 20, 30)


@pytest.mark.parametrize("transition", TRANSITIONS, ids=lambda t: t.effect if t else "default")
def test_each_transition_preserves_alpha_and_independent_center_composition(transition):
    old, new = (255, 0, 0, 128), (0, 0, 255, 64)
    previous, incoming = Image.new("RGBA", (64, 48), old), Image.new("RGBA", (64, 48), new)
    frame = video._transition_frame(transition, previous, incoming, 0.5)
    effect = transition.effect if transition else "fade"
    assert frame.mode == "RGBA"
    assert (
        video._transition_frame(transition, previous, incoming, 1).tobytes() == incoming.tobytes()
    )
    start = incoming if effect == "cut" else previous
    assert video._transition_frame(transition, previous, incoming, 0).tobytes() == start.tobytes()
    if effect in {"fade", "random", "morph"}:
        assert_pixel(pixel(frame, (32, 24)), blend_oracle(old, new, 0.5))
    elif effect == "cover":
        assert_pixel(pixel(frame, (32, 12)), over_oracle(old, new))
    elif effect == "uncover":
        assert_pixel(pixel(frame, (32, 36)), over_oracle(new, old))
    elif effect in {"zoom", "newsflash"}:
        assert_pixel(pixel(frame, (32, 24)), over_oracle(old, (*new[:3], 32)))
    else:
        assert set(frame.getchannel("A").get_flattened_data()) <= {64, 128}


@pytest.mark.parametrize("direction", ["left", "right", "up", "down"])
@pytest.mark.parametrize("kind", [tr.Push, tr.Cover, tr.Uncover])
def test_moving_transitions_clip_negative_offsets_without_squaring_alpha(kind, direction):
    previous = Image.new("RGBA", (20, 20), (255, 0, 0, 128))
    incoming = Image.new("RGBA", (20, 20), (0, 0, 255, 64))
    frame = video._transition_frame(kind(direction=direction), previous, incoming, 0.5)
    values = set(frame.getchannel("A").get_flattened_data())
    assert values == (
        {64, 128} if kind is tr.Push else {128, 160} if kind is tr.Cover else {64, 160}
    )


def test_transparent_morph_interpolates_extents_opacity_and_color_at_nonzero_positions():
    source = Canvas(64, 48).shape("rectangle", (4, 8), 16, 16, "#FF000080", motion_key="box")
    target = Canvas(64, 48).shape("rectangle", (28, 8), 16, 16, "#0000FF40", motion_key="box")
    frame = video._morph_frame(source, target, 0.5, 1, output_size=(64, 48))
    assert frame.getbbox() == (16, 8, 32, 24)
    assert_pixel(pixel(frame, (24, 16)), (170, 0, 85, 96))
    assert pixel(frame, (4, 16))[3] == 0


def test_transparent_morph_conforms_mixed_size_keyed_layers_and_authored_backgrounds():
    source = Canvas(64, 48).background(color="#00FF0040")
    source.shape("rectangle", (8, 8), 16, 16, "#FF000080", motion_key="box")
    target = Canvas(32, 48).background(color="#00FF0040")
    target.shape("rectangle", (8, 8), 16, 16, "#FF000080", motion_key="box")
    frame = video._morph_frame(source, target, 0.5, 1, output_size=(64, 48))
    # Target is centered with 16px bars: the keyed rectangle moves from x8 to x24.
    assert pixel(frame, (20, 16))[3] == 160
    assert pixel(frame, (12, 16))[3] == 32
    assert pixel(frame, (40, 32))[3] == 64
    assert pixel(frame, (4, 32))[3] == 32


def _scenes():
    canvases = []
    transitions = []
    for index, transition in enumerate(TRANSITIONS):
        canvas = Canvas(64 if index % 2 == 0 else 32, 48)
        canvas.shape("rectangle", (4, 4), 20, 24, "#FF000080", motion_key="box")
        canvas.shape("rectangle", (16, 16), 12, 12, "#0000FF40", animation=Fade(duration=0.2))
        canvases.append(canvas)
        transitions.append(
            transition.model_copy(update={"duration": 0.2}) if transition else tr.Fade(duration=0.2)
        )
    return canvases, transitions


@pytest.mark.parametrize("quality", QUALITIES)
def test_all_transition_families_serial_spawn_parity_and_reverse_sampling(quality):
    canvases, transitions = _scenes()
    plan = video._deck_plan(canvases, transitions, 0.1, 0.1, None, quality=quality)
    results = []
    for workers in (1, 2):
        with video._PreparedAnimation(
            canvases,
            transitions,
            fps=10,
            slide_duration=0.1,
            matte=None,
            workers=workers,
            quality=quality,
        ) as prepared:
            results.append([(s.duration, s.frame.tobytes()) for s in prepared.shots()])
    serial, parallel = results
    assert serial == parallel
    assert set(serial[0][1][3::4]) == {0}  # Slide zero starts in transparency.
    renderer = _FrameRenderer(
        [_CanvasSpec.capture(c) for c in canvases], plan.timings, (64, 48), None, False, quality
    )
    try:
        forward = {
            (i, time): renderer.render(i, time)
            for i in range(len(canvases))
            for time in [0.0, 0.1, 0.2]
        }
        reverse = {
            (i, time): renderer.render(i, time)
            for i in reversed(range(len(canvases)))
            for time in [0.2, 0.1, 0.0]
        }
        assert forward == reverse
    finally:
        renderer.close()
        video._close_video_decoders(canvases)


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg required")
def test_every_transition_decodes_alpha_and_color_planes(tmp_path):
    previous = Image.new("RGBA", (64, 48), (255, 0, 0, 128))
    incoming = Image.new("RGBA", (64, 48), (0, 0, 255, 64))
    frames = [video._transition_frame(t, previous, incoming, 0.5) for t in TRANSITIONS]
    path = tmp_path / "transitions.webm"
    video._encode_video_file(
        video._counted_video_shots((video._Shot(f, 0.1) for f in frames), 10),
        10,
        "webm",
        str(path),
        transparent=True,
    )
    decoded = decode(path, (64, 48))
    assert len(decoded) == len(frames)
    # Lossless VP9 protects alpha; RGB still passes through YUV 4:2:0.
    for actual, expected in zip(decoded, frames, strict=True):
        alpha_error = ImageChops.difference(actual.getchannel("A"), expected.getchannel("A"))
        assert cast(int, alpha_error.getextrema()[1]) <= 1
        # Avoid chroma transition boundaries. Some narrow masks have no broad
        # flat interior; their color composition has exact raw-RGBA tests above.
        for y in range(4, 45, 4):
            for x in range(4, 61, 4):
                if len(expected.crop((x - 3, y - 3, x + 4, y + 4)).getcolors() or []) == 1:
                    assert_pixel(pixel(actual, (x, y)), pixel(expected, (x, y)), tolerance=4)


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg required")
@pytest.mark.parametrize("quality", QUALITIES)
@pytest.mark.parametrize("workers", [1, 2])
def test_public_render_decodes_transparent_half_alpha_and_opaque_regions(
    tmp_path, quality, workers
):
    canvas = Canvas(96, 48)
    canvas.shape("rectangle", (0, 0), 32, 48, "#FF000080", animation=Fade(duration=0.2))
    canvas.shape("rectangle", (32, 0), 32, 48, "#00FF00")
    path = tmp_path / "regions.webm"
    canvas.render(
        str(path),
        animation=VideoOptions(transparent=True, fps=10, quality=quality, workers=workers),
    )
    frames = decode(path, (96, 48))
    assert len(frames) == 32
    for point, expected in [((16, 24), (255, 0, 0, 128)), ((48, 24), (0, 255, 0, 255))]:
        assert_pixel(pixel(frames[-1], point), expected, tolerance=6)
    assert pixel(frames[0], (16, 24))[3] <= 2
    assert pixel(frames[-1], (80, 24))[3] <= 2


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg required")
def test_alpha_survives_real_64_shot_batch_boundary_with_cumulative_counts(tmp_path):
    frames = []
    durations = [0.05, 0.1, 0.03, 0.07, 0.1] * 20
    expected = []
    clock = 0.0
    emitted = 0
    for index, duration in enumerate(durations):
        frame = Image.new("RGBA", (128, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(frame)
        for bit in range(8):
            alpha = 255 if index & (1 << bit) else 64
            draw.rectangle((16 * bit, 0, 16 * bit + 15, 31), fill=(255, 255, 255, alpha))
        frames.append(video._Shot(frame, duration))
        clock += duration
        end = math.floor(clock * 10 + 0.5)
        expected.extend([index] * (end - emitted))
        emitted = end
    path = tmp_path / "boundaries.webm"
    # More than 64 emitted distinct shots forces real segment concatenation.
    assert len(list(video._counted_video_shots(frames, 10))) > 64
    video._encode_video_file(
        video._counted_video_shots(iter(frames), 10), 10, "webm", str(path), transparent=True
    )
    decoded = decode(path, (128, 32))
    actual = [
        sum((pixel(frame, (16 * bit + 8, 16))[3] > 160) << bit for bit in range(8))
        for frame in decoded
    ]
    assert actual == expected


def test_lower_third_alpha_snapshot():
    from examples.transparent_lower_third import build_scene

    animator = video._SlideAnimator(build_scene(), {})
    strip = Image.new("RGBA", (960, 180))
    strip.paste(animator.frame_at(0.4), (0, 0))
    strip.paste(animator.final_export_frame(), (480, 0))
    expected = Image.open(Path(__file__).parent / "snapshots" / "transparent_lower_third.png")
    assert (strip.mode, strip.size, strip.tobytes()) == (
        expected.mode,
        expected.size,
        expected.tobytes(),
    )


def test_morph_incompatible_layers_crossfade_premultiplied_pixels(tmp_path):
    source = Canvas(48, 32).shape("rectangle", (8, 8), 16, 16, "#FF000080", motion_key="box")
    asset = tmp_path / "blue.png"
    Image.new("RGBA", (16, 16), (0, 0, 255, 64)).save(asset)
    target = Canvas(48, 32).image(
        str(asset), position=(8, 8), width=16, height=16, motion_key="box"
    )
    frame = video._morph_frame(source, target, 0.5, 1, output_size=(48, 32))
    assert_pixel(pixel(frame, (16, 16)), (170, 0, 85, 96))


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg required")
def test_lossless_alpha_ramp_decodes_every_8_bit_level(tmp_path):
    frame = Image.new("RGBA", (256, 16), (190, 80, 30, 255))
    frame.putalpha(Image.frombytes("L", frame.size, bytes(range(256)) * 16))
    path = tmp_path / "alpha-ramp.webm"
    video._encode_video_file(
        video._counted_video_shots([video._Shot(frame, 0.1)], 10),
        10,
        "webm",
        str(path),
        transparent=True,
    )
    actual = decode(path, frame.size)[0]
    difference = ImageChops.difference(actual.getchannel("A"), frame.getchannel("A"))
    assert cast(int, difference.getextrema()[1]) <= 1
    assert pixel(actual, (0, 8))[3] == 0
    assert pixel(actual, (255, 8))[3] == 255
