"""Render the Orbit Atlas thumbnails, four-slide deck, and 17-second video.

From the repository root:
    uv run --no-default-groups python examples/orbit_atlas.py --output-dir /tmp/orbit-atlas

Orbit Atlas is a fictional brand and its numbers are illustrative. The source images
in assets/images are AI-generated; type, shapes, and motion are all quickthumb layers.
Video needs FFmpeg; pass --stills to skip it, or --pptx with the pptx extra installed.
Files with the same names in the output directory are replaced.
"""

import argparse
import itertools
import math
import os
import random
import subprocess
import tempfile
from pathlib import Path

from quickthumb import (
    AnimationSpec,
    AudioTrack,
    Canvas,
    Deck,
    Fade,
    Glow,
    ImagePanTrack,
    ImageZoomTrack,
    KeyframeSpec,
    LayerMask,
    LinearGradient,
    OpacityTrack,
    PositionTrack,
    RadialGradient,
    RotationTrack,
    ScaleTrack,
    ScaleYTrack,
    Shadow,
    SpringEasing,
    TextFillImage,
    TextPart,
    TimingSpec,
    TrimEndTrack,
    VideoOptions,
    Wipe,
)
from quickthumb import transitions as tr

ROOT = Path(__file__).resolve().parents[1]
PHOTOS = ROOT / "assets/images/cleaner-future"
EARTH = str(PHOTOS / "earth.png")
MOUNTAINS = str(PHOTOS / "mountains.png")
CREATOR = str(PHOTOS / "creator.png")
GUEST = str(ROOT / "assets/images/podcast-guest-editorial.png")
SOUNDTRACK = str(ROOT / "assets/audio/hype_beat.wav")
REGULAR = str(ROOT / "assets/fonts/Roboto-Regular.ttf")
BOLD = str(ROOT / "assets/fonts/Roboto-Bold.ttf")
HEAVY = str(ROOT / "assets/fonts/Roboto-Black.ttf")
MONO = str(ROOT / "assets/fonts/NotoSans-Medium.ttf")

WIDTH, HEIGHT = 1280, 720
BLUE = "#155BD7"
SKY = "#62B7FF"
YELLOW = "#FFD400"
NAVY = "#06122B"
INK = "#101D32"
MUTED = "#5B6D83"
WHITE = "#FFFFFF"

# The soundtrack runs at 128 BPM, so every scene is cut on a beat.
BEAT = 60 / 128
ORBIT_END, TRAIL_END, NUMBER_END, CLOSE_END = 8 * BEAT, 8 * BEAT, 8 * BEAT, 12 * BEAT
# Earth's centre in the 1280x720 crop; the camera, ring, and disc all pivot here.
EARTH_CENTER = (869, 397)
EARTH_RADIUS = 372
EARTH_ANCHOR = (EARTH_CENTER[0] / WIDTH, EARTH_CENTER[1] / HEIGHT)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path.cwd())
    parser.add_argument("--stills", action="store_true", help="skip the MP4 (no FFmpeg needed)")
    parser.add_argument("--pptx", action="store_true", help="also render PPTX (needs pptx extra)")
    args = parser.parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    planet_thumbnail().render(str(out / "orbit-thumbnail-planet.webp"), quality=88)
    visuals_thumbnail().render(str(out / "orbit-thumbnail-visuals.webp"), quality=88)
    slides = deck()
    for index, canvas in enumerate(slides, 1):
        canvas.render(str(out / f"orbit-slide-{index}.webp"), quality=90)
    slides.render(str(out / "orbit-deck.html"))
    if args.pptx:
        slides.render(str(out / "orbit-deck.pptx"))
    poster = orbit_scene().render_frame(5 * BEAT).convert("RGB")
    poster.save(out / "orbit-film-poster.webp", quality=88)
    if not args.stills:
        render_film(out)


def render_film(out: Path) -> None:
    """Replace orbit-film.mp4 only on success; quickthumb's near-lossless master is temporary."""
    with tempfile.TemporaryDirectory(dir=out) as scratch:
        master = Path(scratch) / "master.mp4"
        compressed = Path(scratch) / "orbit-film.mp4"
        video(out).render(
            str(master),
            animation=VideoOptions(
                fps=24,
                soundtrack=AudioTrack(path=SOUNDTRACK, volume=0.5, loop=True, fade_out=1.5),
            ),
        )
        subprocess.run(
            [
                # quickthumb's own override, so both encoding steps use the same binary.
                os.environ.get("QUICKTHUMB_FFMPEG") or "ffmpeg",
                "-v",
                "error",
                "-i",
                str(master),
                "-c:v",
                "libx264",
                "-crf",
                "27",
                "-preset",
                "slow",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                "-c:a",
                "copy",
                str(compressed),
            ],
            check=True,
        )
        compressed.replace(out / "orbit-film.mp4")


def planet_thumbnail() -> Canvas:
    """A creator pointing at the planet, with the type set around the gesture."""
    canvas = Canvas(WIDTH, HEIGHT).image(CREATOR, (0, 0), WIDTH, HEIGHT, fit="cover")
    # The frame is shifted so the planet sits inside the mask in the lower right.
    canvas.image(
        EARTH,
        (276, 248),
        WIDTH,
        HEIGHT,
        fit="cover",
        mask=LayerMask(shape="ellipse", position=(790, 290), width=770, height=770, feather=2),
        effects=[Glow(color="#2F8CFF", radius=46, opacity=0.8)],
    )
    canvas.text(
        "I MAPPED\nTHE PLANET",
        position=(716, 58),
        font=HEAVY,
        size=86,
        color=WHITE,
        line_height=1.0,
        effects=[Shadow(offset_x=0, offset_y=6, color="#000000CC", blur_radius=18)],
    )
    canvas.shape(
        "rectangle",
        (722, 252),
        486,
        104,
        YELLOW,
        rotation=-3,
        effects=[Shadow(offset_x=0, offset_y=10, color="#00000099", blur_radius=20)],
    )
    canvas.text(
        "WITH PYTHON", position=(756, 270), font=HEAVY, size=62, color="#111923", rotation=-3
    )
    return canvas


def visuals_thumbnail() -> Canvas:
    """A dark editorial cover: gradient type beside a portrait on a lit backdrop."""
    canvas = Canvas(WIDTH, HEIGHT).image(GUEST, (0, 0), WIDTH, HEIGHT, fit="cover")
    canvas.shape(
        "ellipse",
        (-420, -420),
        1400,
        1400,
        BLUE,
        fill=_glow_fill("#155BD7", "B0"),
    )
    canvas.text("CODE YOUR", position=(70, 110), font=BOLD, size=46, color=SKY, letter_spacing=6)
    canvas.text(
        "BETTER\nVISUALS",
        position=(66, 170),
        font=HEAVY,
        size=138,
        line_height=0.98,
        color=WHITE,
        fill=LinearGradient(angle=90, stops=[("#FFFFFF", 0.35), ("#FFD400", 1.0)]),
    )
    canvas.path(
        "M0 26C90 2 210 2 300 16S470 34 560 8",
        (72, 462),
        560,
        40,
        None,
        view_box=(0, 0, 560, 40),
        stroke=YELLOW,
        stroke_width=9,
        line_cap="round",
    )
    canvas.text(
        "Thumbnails, slides, and video.\nOne script.",
        position=(72, 530),
        font=REGULAR,
        size=30,
        color="#D7E3F4",
    )
    return canvas


def deck() -> Deck:
    """A four-slide deck whose layers enter on arrival.

    HTML and PowerPoint simplify these entrances, and quickthumb lists each one in
    ExportResult.fallback_diagnostics; see the "Orbit Atlas" cookbook section.
    """
    return (
        Deck(WIDTH, HEIGHT)
        .slide(
            cover_slide(),
            transition=tr.Fade(duration=0.6),
            notes="Introduce Orbit Atlas, a fictional mapping studio.",
        )
        .slide(
            coverage_slide(),
            transition=tr.Push(direction="left", duration=0.6),
            notes="All coverage figures are illustrative.",
        )
        .slide(
            metrics_slide(),
            transition=tr.Wipe(direction="left", duration=0.6),
            notes="Three numbers, also illustrative.",
        )
        .slide(
            closing_slide(),
            transition=tr.Fade(duration=0.8),
            notes="Close on the image-filled headline.",
        )
    )


def cover_slide() -> Canvas:
    canvas = Canvas(WIDTH, HEIGHT).background(color=WHITE)
    canvas.shape("rectangle", (690, 0), 590, HEIGHT, BLUE)
    canvas.image(MOUNTAINS, (640, 70), 570, 500, fit="cover", border_radius=20)
    canvas.text("ORBIT ATLAS", position=(70, 66), font=BOLD, size=20, color=BLUE, letter_spacing=4)
    canvas.text(
        "See the\nplanet\nclearly.",
        position=(68, 160),
        font=HEAVY,
        size=98,
        color=INK,
        line_height=1.0,
        animation=_enter_block(),
    )
    canvas.text(
        "Field notes from mapping the world.",
        position=(72, 490),
        font=REGULAR,
        size=26,
        color=MUTED,
        max_width=480,
        animation=_enter_after(),
    )
    canvas.text("46.5° N  /  8.0° E", position=(710, 612), font=BOLD, size=22, color=WHITE)
    canvas.text(
        "VOL. 01", position=(1210, 612), align=("right", "top"), font=BOLD, size=22, color=WHITE
    )
    return canvas


def coverage_slide() -> Canvas:
    canvas = _page("Coverage", "02")
    canvas.text(
        "Coverage\ndoubled in\nfour years.",
        position=(70, 130),
        font=HEAVY,
        size=66,
        color=INK,
        line_height=1.04,
        animation=_enter_block(),
    )
    canvas.text(
        "Mapped land area by year, in millions of square kilometres. Illustrative data.",
        position=(72, 390),
        font=REGULAR,
        size=24,
        color=MUTED,
        max_width=420,
        animation=_enter_after(),
    )
    values = {"2022": 34, "2023": 41, "2024": 49, "2025": 58, "2026": 70}
    baseline, unit = 580, 6
    for index, (year, value) in enumerate(values.items()):
        x, height = 600 + index * 124, value * unit
        delay = index * 0.08
        canvas.shape(
            "rectangle",
            (x, baseline - height),
            90,
            height,
            BLUE if year == "2026" else "#A9C9E8",
            border_radius=8,
            animation=Wipe(direction="up", duration=0.5, delay=delay, trigger="with_previous"),
        )
        canvas.text(
            str(value),
            position=(x + 45, baseline - height - 44),
            align=("center", "top"),
            font=BOLD,
            size=30,
            color=INK,
            animation=Fade(duration=0.5, delay=delay, trigger="with_previous"),
        )
        canvas.text(
            year,
            position=(x + 45, baseline + 14),
            align=("center", "top"),
            font=REGULAR,
            size=22,
            color=MUTED,
            animation=Fade(duration=0.5, delay=delay, trigger="with_previous"),
        )
    return canvas


def metrics_slide() -> Canvas:
    canvas = Canvas(WIDTH, HEIGHT).background(
        color=BLUE,
        gradient=RadialGradient(stops=[("#2C78F0", 0.0), (BLUE, 1.0)], center=(0.2, 0.1)),
    )
    canvas.text(
        "BY THE NUMBERS", position=(70, 66), font=BOLD, size=20, color="#CFE3FF", letter_spacing=4
    )
    canvas.text(
        "Fresher maps, less waiting.",
        position=(68, 110),
        font=HEAVY,
        size=66,
        color=WHITE,
        animation=_enter_block(),
    )
    metrics = (
        ("12×", "more imagery reviewed"),
        ("48h", "from capture to map"),
        ("70M", "km² mapped"),
    )
    for index, (value, label) in enumerate(metrics):
        x = 70 + index * 390
        canvas.shape("rectangle", (x, 250), 350, 300, WHITE, border_radius=18)
        canvas.text(value, position=(x + 32, 288), font=HEAVY, size=108, color=BLUE)
        canvas.text(label, position=(x + 34, 450), font=REGULAR, size=27, color=INK, max_width=280)
    canvas.text(
        "ILLUSTRATIVE DATA",
        position=(70, 612),
        font=BOLD,
        size=18,
        color="#CFE3FF",
        letter_spacing=2,
    )
    return canvas


def closing_slide() -> Canvas:
    canvas = Canvas(WIDTH, HEIGHT).background(color="#EDF4FF")
    canvas.text(
        "Go look.",
        position=(WIDTH // 2, 170),
        align=("center", "top"),
        font=HEAVY,
        size=250,
        color=INK,
        fill=TextFillImage(path=MOUNTAINS, fit="cover"),
        animation=AnimationSpec.rise(
            from_="bottom", distance=30, duration=0.7, trigger="after_previous"
        ),
    )
    canvas.text(
        "The planet keeps changing. Your maps can too.",
        position=(WIDTH // 2, 480),
        align=("center", "top"),
        font=REGULAR,
        size=30,
        color=INK,
        animation=_enter_after(),
    )
    return canvas


def _page(title: str, number: str) -> Canvas:
    canvas = Canvas(WIDTH, HEIGHT).background(color=WHITE)
    canvas.text(title.upper(), position=(70, 66), font=BOLD, size=20, color=BLUE, letter_spacing=4)
    canvas.text(
        number, position=(1210, 66), align=("right", "top"), font=BOLD, size=20, color=MUTED
    )
    return canvas


def _enter_block() -> AnimationSpec:
    return AnimationSpec.rise(
        from_="bottom",
        distance=24,
        duration=0.6,
        trigger="after_previous",
        easing="ease_out_cubic",
    )


def _enter_after() -> AnimationSpec:
    return AnimationSpec.fade(duration=0.5, trigger="after_previous")


def video(rendered: Path) -> Deck:
    """Four beat-cut scenes: orbit, dive to a trail, the data, and the code behind it."""
    return (
        Deck(WIDTH, HEIGHT)
        .slide(orbit_scene(), transition=tr.Cut(advance_after=ORBIT_END), duration=ORBIT_END)
        .slide(
            trail_scene(),
            transition=tr.Fade(duration=BEAT / 2, advance_after=TRAIL_END - BEAT / 2),
            duration=TRAIL_END,
        )
        .slide(
            number_scene(),
            transition=tr.Push(direction="left", duration=BEAT, advance_after=NUMBER_END - BEAT),
            duration=NUMBER_END,
        )
        .slide(
            close_scene(rendered),
            transition=tr.Circle(duration=BEAT, advance_after=CLOSE_END - BEAT),
            duration=CLOSE_END,
        )
    )


def orbit_scene() -> Canvas:
    """A turning planet, twinkling stars, an occluding ring, and a dive into the clouds."""
    dive = _dive_track()
    canvas = Canvas(WIDTH, HEIGHT).image(
        EARTH, (0, 0), WIDTH, HEIGHT, fit="cover", anchor=EARTH_ANCHOR, animation=_play(dive)
    )
    _add_stars(canvas)
    _add_ring_half(canvas, back=True)
    # Sliding the surface inside a fixed circle reads as the planet turning: the
    # rim and atmosphere stay on the backdrop, which never pans.
    canvas.image(
        EARTH,
        (0, 0),
        WIDTH,
        HEIGHT,
        fit="cover",
        anchor=EARTH_ANCHOR,
        mask=LayerMask(
            shape="ellipse",
            position=(EARTH_CENTER[0] - EARTH_RADIUS, EARTH_CENTER[1] - EARTH_RADIUS),
            width=EARTH_RADIUS * 2,
            height=EARTH_RADIUS * 2,
            feather=14,
        ),
        animation=_play(
            ImageZoomTrack(keyframes=_keys((0, 1.12), (ORBIT_END, 1.12))),
            ImagePanTrack(keyframes=_keys((0, (-0.04, 0.0)), (ORBIT_END, (0.04, 0.0)))),
            dive,
            easing="linear",
        ),
    )
    _add_ring_half(canvas, back=False)
    _add_satellite(canvas)
    canvas.text(
        "ORBIT ATLAS",
        position=(72, 200),
        font=BOLD,
        size=20,
        color=SKY,
        letter_spacing=5,
        animation=_play(_fade(BEAT / 2, BEAT, exit_at=6 * BEAT)),
    )
    _add_headline(canvas, ("One", "planet."), (68, 236), 118, BEAT, exit_at=6 * BEAT)
    # Cloud-white flash: the camera has reached the atmosphere and the cut is hidden.
    canvas.shape(
        "rectangle",
        (0, 0),
        WIDTH,
        HEIGHT,
        WHITE,
        animation=_play(_fade(ORBIT_END - BEAT, BEAT), easing="ease_in"),
    )
    return canvas


def _add_stars(canvas: Canvas) -> None:
    rng = random.Random(7)
    for _ in range(36):
        x, y = rng.randrange(0, 470), rng.randrange(0, HEIGHT)
        size = rng.choice((2, 2, 3, 4))
        phase = rng.uniform(0, 2 * BEAT)
        twinkle = [(t * BEAT + phase, 0.2 if t % 2 else 0.95) for t in range(5)]
        canvas.shape(
            "ellipse",
            (x, y),
            size,
            size,
            WHITE,
            animation=_play(
                OpacityTrack(keyframes=_keys((0, 0.95), *twinkle, (6.2 * BEAT, 0))),
                easing="ease_in_out",
            ),
        )


def _ring_points(back: bool, steps: int = 72) -> list[tuple[float, float]]:
    """One half of a tilted orbit; the front half runs left to right."""
    cx, cy = EARTH_CENTER
    rx, ry, tilt = 560, 132, math.radians(-16)
    start = math.pi if back else 0
    points = []
    for index in range(steps + 1):
        angle = start + math.pi * index / steps
        x, y = rx * math.cos(angle), ry * math.sin(angle)
        points.append(
            (
                cx + x * math.cos(tilt) - y * math.sin(tilt),
                cy + x * math.sin(tilt) + y * math.cos(tilt),
            )
        )
    return points if back else points[::-1]


def _polyline(points: list[tuple[float, float]]) -> str:
    return "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in points)


def _add_ring_half(canvas: Canvas, *, back: bool) -> None:
    start = BEAT * (1 if back else 3)
    canvas.path(
        _polyline(_ring_points(back)),
        (0, 0),
        WIDTH,
        HEIGHT,
        None,
        view_box=(0, 0, WIDTH, HEIGHT),
        stroke=SKY,
        stroke_width=2.5 if back else 4,
        line_cap="round",
        opacity=0.6 if back else 1.0,
        # Scaled paths are capped at 1 Mpx, so the ring leaves before the camera moves.
        animation=_play(
            _draw(start, 2 * BEAT),
            OpacityTrack(keyframes=_keys((0, 1), (5.5 * BEAT, 1), (6 * BEAT, 0))),
            # Linear keeps the line's tip ahead of the slower satellite that rides it.
            easing="linear",
        ),
    )


def _add_satellite(canvas: Canvas) -> None:
    """A dot that rides the visible front of the ring as a sampled motion path."""
    points = _ring_points(back=False)
    _add_rider(canvas, points, 3 * BEAT, 3 * BEAT, size=18, color=SKY, exit_at=5.7 * BEAT)


def _add_rider(
    canvas: Canvas,
    points: list[tuple[float, float]],
    start: float,
    duration: float,
    *,
    size: int,
    color: str,
    exit_at: float | None = None,
) -> None:
    """A glowing dot on a drawn line: keys sit on its points, timed by distance like trim."""
    x0, y0 = points[0]
    distances = list(itertools.accumulate(map(math.dist, points, points[1:]), initial=0.0))
    path = [
        (start + duration * distance / distances[-1], (x - x0, y - y0))
        for distance, (x, y) in zip(distances, points, strict=True)
    ]
    canvas.shape(
        "ellipse",
        (round(x0 - size / 2), round(y0 - size / 2)),
        size,
        size,
        WHITE,
        effects=[Glow(color=color, radius=12)],
        animation=_play(
            PositionTrack(keyframes=_keys((0, (0.0, 0.0)), *path)),
            _fade(start, BEAT / 4, exit_at=exit_at),
            easing="linear",
        ),
    )


def _dive_track() -> ScaleTrack:
    """Hold on Earth, then accelerate into it; shared so both images stay locked."""
    return ScaleTrack(
        keyframes=[
            KeyframeSpec(time=0, value=1.0),
            KeyframeSpec(time=6 * BEAT, value=1.0),
            KeyframeSpec(time=ORBIT_END, value=3.4, easing="ease_in_cubic"),
        ]
    )


def trail_scene() -> Canvas:
    """The camera settles over a lake while a route draws itself up to the summit."""
    route = _sample_route()
    canvas = Canvas(WIDTH, HEIGHT).image(
        MOUNTAINS,
        (0, 0),
        WIDTH,
        HEIGHT,
        fit="cover",
        animation=_play(
            ScaleTrack(
                keyframes=[
                    KeyframeSpec(time=0, value=1.3),
                    KeyframeSpec(time=1.5 * BEAT, value=1.03, easing="ease_out_cubic"),
                    KeyframeSpec(time=TRAIL_END, value=1.0),
                ]
            ),
            easing="linear",
        ),
    )
    canvas.shape(
        "rectangle",
        (0, 0),
        620,
        HEIGHT,
        "#000000",
        # Linear stops span the box diagonal, so the edges sit near 0.17 and 0.83 here.
        fill=LinearGradient(
            angle=0, stops=[("#031024E0", 0.17), ("#03102400", 0.8), ("#03102400", 1.0)]
        ),
    )
    start, duration = 1.5 * BEAT, 4.5 * BEAT
    canvas.path(
        _polyline(route),
        (0, 0),
        WIDTH,
        HEIGHT,
        None,
        view_box=(0, 0, WIDTH, HEIGHT),
        stroke=YELLOW,
        stroke_width=6,
        line_cap="round",
        line_join="round",
        animation=_play(_draw(start, duration), easing="linear"),
    )
    _add_rider(canvas, route, start, duration, size=22, color=YELLOW)
    _add_summit_pulse(canvas, route[-1], start + duration)
    _add_headline(canvas, ("Every", "trail."), (68, 236), 118, BEAT / 2)
    _add_elevation_card(canvas, start)
    return canvas


def _add_summit_pulse(canvas: Canvas, summit: tuple[float, float], at: float) -> None:
    canvas.shape(
        "ellipse",
        (round(summit[0]) - 60, round(summit[1]) - 60),
        120,
        120,
        YELLOW,
        animation=_play(
            ScaleTrack(keyframes=_keys((0, 0.1), (at, 0.1), (at + 1.5 * BEAT, 1.5))),
            OpacityTrack(
                keyframes=_keys((0, 0), (at, 0), (at + BEAT / 8, 0.7), (at + 1.5 * BEAT, 0))
            ),
        ),
    )


def _sample_route() -> list[tuple[float, float]]:
    """Sample cubic segments from the lakeshore to the summit into a dense polyline."""
    segments = (
        ((470, 716), (520, 640), (610, 620), (660, 545)),
        ((660, 545), (710, 470), (800, 450), (770, 345)),
        ((770, 345), (745, 260), (670, 230), (693, 124)),
    )
    points: list[tuple[float, float]] = []
    for p0, p1, p2, p3 in segments:
        for index in range(24):
            t = index / 24
            u = 1 - t
            points.append(
                (
                    u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0],
                    u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1],
                )
            )
    points.append(segments[-1][-1])
    return points


def _add_elevation_card(canvas: Canvas, start: float) -> None:
    x, y, width, height = 870, 500, 340, 160
    enter = (_slide((60, 0), start - BEAT, BEAT), _fade(start - BEAT, BEAT))
    canvas.shape(
        "rectangle",
        (x, y),
        width,
        height,
        NAVY,
        opacity=0.82,
        border_radius=16,
        animation=_play(*enter),
    )
    canvas.text(
        "ELEVATION  ·  ILLUSTRATIVE",
        position=(x + 24, y + 20),
        font=BOLD,
        size=18,
        color=SKY,
        letter_spacing=1,
        animation=_play(_fade(start, BEAT / 2)),
    )
    canvas.counter(
        1120,
        3412,
        4.5 * BEAT,
        delay=start,
        suffix=" m",
        style="plain",
        easing="linear",
        position=(x + 24, y + 46),
        size=46,
        font=HEAVY,
        color=WHITE,
        animation=_play(*enter),
    )
    profile = [(0, 34), (40, 30), (80, 34), (120, 22), (160, 26), (200, 14), (250, 16), (292, 0)]
    canvas.path(
        _polyline(profile),
        (x + 24, y + 108),
        292,
        36,
        None,
        view_box=(0, -1, 292, 36),
        stroke=YELLOW,
        stroke_width=3,
        line_join="round",
        line_cap="round",
        animation=_play(_draw(start, 4.5 * BEAT), easing="linear"),
    )


def number_scene() -> Canvas:
    """Bars spring up on the beat, a line draws across them, and glows drift behind."""
    canvas = Canvas(WIDTH, HEIGHT).background(color=NAVY)
    _add_drifting_glow(canvas, (30, 40), "#155BD7", (130, 50))
    _add_drifting_glow(canvas, (660, 90), "#0E7BC4", (-60, -60))
    _add_headline(canvas, ("Every", "number."), (68, 96), 118, BEAT / 2)
    number_start = 1.5 * BEAT
    canvas.counter(
        12,
        84,
        4 * BEAT,
        delay=number_start,
        suffix="%",
        style="plain",
        position=(68, 370),
        size=150,
        font=HEAVY,
        color=SKY,
        animation=_play(_slide((0, 30), number_start, BEAT), _fade(number_start, BEAT / 2)),
    )
    for text, y, font, size, color in (
        ("of the map refreshed this year", 545, REGULAR, 27, "#CFE3FF"),
        ("ILLUSTRATIVE DATA", 620, BOLD, 18, "#9DB6D8"),
    ):
        canvas.text(
            text,
            position=(74, y),
            font=font,
            size=size,
            color=color,
            animation=_play(_fade(2 * BEAT, BEAT)),
        )
    _add_bars_and_line(canvas)
    return canvas


def _add_drifting_glow(
    canvas: Canvas, position: tuple[int, int], color: str, drift: tuple[int, int]
) -> None:
    # Motion moves pixels rendered inside the canvas, so a glow must stay fully on it.
    canvas.shape(
        "ellipse",
        position,
        560,
        560,
        color,
        fill=_glow_fill(color, "90"),
        animation=_play(
            PositionTrack(keyframes=_keys((0, (0, 0)), (NUMBER_END, drift))),
            easing="ease_in_out",
        ),
    )


def _glow_fill(color: str, alpha: str) -> RadialGradient:
    """Fade out before the circle's edge, which sits near the middle of the stop range."""
    return RadialGradient(
        stops=[(f"{color}{alpha}", 0.0), (f"{color}00", 0.5), (f"{color}00", 1.0)]
    )


def _add_bars_and_line(canvas: Canvas) -> None:
    left, baseline, pitch, bar_width, peak = 560, 620, 56, 36, 470
    ratios = (0.22, 0.28, 0.25, 0.38, 0.44, 0.41, 0.55, 0.62, 0.6, 0.74, 0.86, 1.0)
    for row in range(5):
        canvas.shape(
            "rectangle",
            (left, baseline - row * peak // 4),
            pitch * len(ratios),
            1,
            "#2A4470",
            animation=_play(_fade(row * BEAT / 4, BEAT)),
        )
    tops = []
    for index, ratio in enumerate(ratios):
        height = round(peak * ratio)
        x = left + index * pitch
        tops.append((x + bar_width / 2, baseline - height - 22.0))
        at = BEAT / 2 + index * BEAT / 4
        canvas.shape(
            "rectangle",
            (x, baseline - height),
            bar_width,
            height,
            SKY if index == len(ratios) - 1 else BLUE,
            border_radius=6,
            anchor=(0.5, 1.0),
            animation=_play(
                ScaleYTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value=0.0),
                        KeyframeSpec(time=at, value=0.0),
                        KeyframeSpec(
                            time=at + 2 * BEAT,
                            value=1.0,
                            easing=SpringEasing(stiffness=180, damping=14),
                        ),
                    ]
                ),
                easing="linear",
            ),
        )
    start, duration = 2 * BEAT, 4 * BEAT
    canvas.path(
        _polyline(tops),
        (0, 0),
        WIDTH,
        HEIGHT,
        None,
        view_box=(0, 0, WIDTH, HEIGHT),
        stroke=WHITE,
        stroke_width=4,
        line_join="round",
        line_cap="round",
        animation=_play(_draw(start, duration), easing="linear"),
    )
    _add_rider(canvas, tops, start, duration, size=22, color=SKY)


def close_scene(rendered: Path) -> Canvas:
    """The script types itself while the files it just rendered spring into place."""
    canvas = Canvas(WIDTH, HEIGHT).background(
        color=BLUE,
        gradient=RadialGradient(stops=[("#2C78F0", 0.0), (BLUE, 1.0)], center=(0.2, 0.15)),
    )
    _add_headline(canvas, ("Make visuals", "with code."), (64, 56), 84, BEAT / 2)
    _add_code_window(canvas, (68, 262))
    enter = (_slide((0, 30), 7 * BEAT, BEAT), _fade(7 * BEAT, BEAT / 2))
    canvas.shape("rectangle", (68, 610), 314, 58, WHITE, border_radius=12, animation=_play(*enter))
    canvas.text(
        "pip install quickthumb",
        position=(92, 623),
        font=BOLD,
        size=27,
        color=BLUE,
        animation=_play(*enter),
    )
    tiles = (
        (rendered / "orbit-thumbnail-visuals.webp", (840, 36), 4.0, (900, -60), 2 * BEAT),
        (rendered / "orbit-slide-1.webp", (664, 244), -3.0, (-300, 520), 3 * BEAT),
        (rendered / "orbit-thumbnail-planet.webp", (850, 452), 3.0, (620, 420), 4 * BEAT),
    )
    for path, position, rotation, offset, start in tiles:
        _add_tile(canvas, str(path), position, rotation, offset, start)
    return canvas


def _add_code_window(canvas: Canvas, position: tuple[int, int]) -> None:
    x, y = position
    canvas.shape(
        "rectangle",
        (x, y),
        560,
        326,
        "#0B1730",
        border_radius=16,
        effects=[Shadow(offset_x=0, offset_y=14, color="#00143A80", blur_radius=30)],
        animation=_play(_slide((-40, 0), BEAT / 2, BEAT), _fade(BEAT / 2, BEAT / 2)),
    )
    keyword, name, string, plain = "#7FB8FF", "#FFD400", "#9EE6C3", "#E8F0FB"
    lines = (
        [("from ", keyword), ("quickthumb ", plain), ("import ", keyword), ("Canvas, Deck", plain)],
        [],
        [("thumb ", plain), ("= ", keyword), ("Canvas", name), ("(1280, 720)", plain)],
        [
            ("thumb.", plain),
            ("image", name),
            ("(", plain),
            ('"earth.png"', string),
            (", (0, 0))", plain),
        ],
        [
            ("thumb.", plain),
            ("text", name),
            ("(", plain),
            ('"One planet."', string),
            (", size=118)", plain),
        ],
        [],
        [
            ("film ", plain),
            ("= ", keyword),
            ("Deck", name),
            ("(1280, 720).", plain),
            ("slide", name),
            ("(thumb)", plain),
        ],
        [
            ("film.", plain),
            ("render", name),
            ("(", plain),
            ('"orbit-film.mp4"', string),
            (")", plain),
        ],
    )
    for index, line in enumerate(lines):
        if not line:
            continue
        at = BEAT + index * BEAT / 2
        canvas.text(
            [TextPart(text=part, color=color) for part, color in line],
            position=(x + 26, y + 26 + index * 35),
            font=MONO,
            size=21,
            color=plain,
            animation=_play(_slide((-14, 0), at, BEAT / 2), _fade(at, BEAT / 4)),
        )


def _add_tile(
    canvas: Canvas,
    path: str,
    position: tuple[int, int],
    rotation: float,
    offset: tuple[int, int],
    start: float,
) -> None:
    """An output image springs in from off-canvas, then floats until the end."""
    settled = start + 2 * BEAT
    bob = 8 if rotation > 0 else -8
    canvas.image(
        path,
        position,
        400,
        225,
        fit="cover",
        border_radius=12,
        effects=[Shadow(offset_x=0, offset_y=16, color="#00143A99", blur_radius=28)],
        animation=_play(
            PositionTrack(
                keyframes=[
                    KeyframeSpec(time=0, value=offset),
                    KeyframeSpec(time=start, value=offset),
                    KeyframeSpec(
                        time=settled,
                        value=(0, 0),
                        easing=SpringEasing(stiffness=120, damping=13),
                    ),
                    KeyframeSpec(time=CLOSE_END, value=(0, bob), easing="ease_in_out"),
                ]
            ),
            RotationTrack(
                keyframes=[
                    KeyframeSpec(time=0, value=rotation * 5),
                    KeyframeSpec(time=start, value=rotation * 5),
                    KeyframeSpec(time=settled, value=rotation, easing="ease_out_cubic"),
                ]
            ),
            easing="linear",
        ),
    )


def _add_headline(
    canvas: Canvas,
    lines: tuple[str, ...],
    position: tuple[int, int],
    size: int,
    start: float,
    *,
    exit_at: float | None = None,
) -> None:
    """Rise one text layer per line on the beat, so each line can land on its own."""
    x, y = position
    for index, line in enumerate(lines):
        begin = start + index * BEAT / 2
        canvas.text(
            line,
            position=(x, y + round(index * size * 0.98)),
            font=HEAVY,
            size=size,
            color=WHITE,
            animation=_play(
                _slide((0, 56), begin, BEAT),
                _fade(begin, BEAT / 2, exit_at=exit_at),
            ),
        )


def _play(*tracks, easing: str = "ease_out_cubic") -> AnimationSpec:
    """One timeline on the scene clock: a layer before its first move holds its first key."""
    duration = max(track.keyframes[-1].time for track in tracks)
    return AnimationSpec.timeline(
        *tracks, timing=TimingSpec(start=0, duration=duration), easing=easing
    )


def _keys(*pairs: tuple) -> list[KeyframeSpec]:
    """Build keyframes; a move starting at zero repeats the opening time, so keep the later key."""
    return [KeyframeSpec(time=time, value=value) for time, value in dict(pairs).items()]


def _fade(start: float, duration: float, *, exit_at: float | None = None) -> OpacityTrack:
    pairs = [(0, 0), (start, 0), (start + duration, 1)]
    if exit_at is not None:
        pairs += [(exit_at, 1), (exit_at + BEAT / 2, 0)]
    return OpacityTrack(keyframes=_keys(*pairs))


def _slide(offset: tuple[int, int], start: float, duration: float) -> PositionTrack:
    return PositionTrack(keyframes=_keys((0, offset), (start, offset), (start + duration, (0, 0))))


def _draw(start: float, duration: float) -> TrimEndTrack:
    return TrimEndTrack(keyframes=_keys((0, 0), (start, 0), (start + duration, 1)))


if __name__ == "__main__":
    main()
