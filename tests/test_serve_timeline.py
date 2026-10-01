"""Canonical pixels and bounded proxy work across the live timeline HTTP boundary."""

import json
import math
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from io import BytesIO
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

import pytest
from PIL import Image
from quickthumb import (
    AnimationSpec,
    Canvas,
    ColorTrack,
    Deck,
    Fade,
    KeyframeSpec,
    PositionTrack,
    TimingSpec,
)
from quickthumb import _export_video as video
from quickthumb._serve import SlideSource, serve_slides, slide_request_handler
from quickthumb._serve_timeline import StaleTimelineError, TimelinePreview
from quickthumb.cli import app
from quickthumb.errors import ValidationError
from quickthumb.transitions import Push
from typer.testing import CliRunner


def moving_card(width=80, height=40):
    return (
        Canvas(width, height)
        .background(color="#112233")
        .shape(
            "rectangle",
            (width // 8, height // 4),
            width // 4,
            height // 4,
            "#FF5566",
            animation=AnimationSpec.timeline(
                PositionTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value=(0, 0)),
                        KeyframeSpec(time=1, value=(width // 3, height // 3)),
                    ]
                ),
                ColorTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value="#FF5566"),
                        KeyframeSpec(time=1, value="#33BBCC"),
                    ]
                ),
                timing=TimingSpec(duration=1),
                easing="linear",
            ),
        )
    )


def write_source(tmp_path, document):
    path = tmp_path / "slides.json"
    path.write_text(document.to_json(), encoding="utf-8")
    return SlideSource(path, {})


@contextmanager
def running(source):
    server = ThreadingHTTPServer(("127.0.0.1", 0), slide_request_handler(source))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        source.close()


def get_json(base):
    with urlopen(base + "/__quickthumb_timeline", timeout=10) as response:
        return json.load(response)


def get_frame(base, version, time, resolution="full"):
    query = urlencode({"version": version, "time": time, "resolution": resolution})
    with urlopen(base + "/__quickthumb_frame?" + query, timeout=10) as response:
        return Image.open(BytesIO(response.read())).convert("RGBA"), dict(response.headers)


@pytest.mark.parametrize("deck", [False, True])
def test_full_timeline_http_matches_canonical_sampling_in_reverse_order(tmp_path, deck):
    first = moving_card()
    document = (
        Deck()
        .slide(first, duration=1.25)
        .slide(
            Canvas(60, 60)
            .background(color="#FFAA22")
            .shape("ellipse", (10, 10), 25, 25, "#FFFFFF", animation=Fade(duration=0.75)),
            transition=Push(duration=0.5),
            duration=1.5,
        )
        if deck
        else first
    )
    source = write_source(tmp_path, document)
    times = [0, 0.25, 0.5, 1, 1.25, 1.5, 1.75, 2.75, 9]
    expected = document.sample(times)
    with running(source) as base:
        metadata = get_json(base)
        assert metadata["segments"] == [part.model_dump() for part in expected.timeline]
        assert metadata["duration"] == expected.duration
        for instant, reference in reversed(list(zip(times, expected.frames, strict=True))):
            image, headers = get_frame(base, metadata["version"], instant)
            assert image.tobytes() == reference.to_bytes()
            assert float(headers["X-Quickthumb-Time"]) == min(instant, metadata["duration"])
            assert int(headers["X-Quickthumb-Slide"]) == reference.slide
            assert headers["Cache-Control"] == "no-store"
            assert headers["X-Content-Type-Options"] == "nosniff"


def test_portrait_proxy_composites_on_reduced_surfaces_and_preserves_full_mode(
    tmp_path, monkeypatch
):
    source = write_source(tmp_path, moving_card(1080, 1920))
    sizes = []
    original = video._SlideAnimator._composite_frame

    def record(self, *args, **kwargs):
        frame = original(self, *args, **kwargs)
        sizes.append(frame.size)
        return frame

    monkeypatch.setattr(video._SlideAnimator, "_composite_frame", record)
    with running(source) as base:
        metadata = get_json(base)
        assert (metadata["width"], metadata["height"]) == (1080, 1920)
        assert (metadata["proxy_width"], metadata["proxy_height"]) == (360, 640)
        for instant in [0.8, 0.2, 1, 0, 0.5]:
            proxy, _ = get_frame(base, metadata["version"], instant, "proxy")
            assert proxy.size == (360, 640)
        assert sizes and set(sizes) == {(360, 640)}
        full, _ = get_frame(base, metadata["version"], 0.5)
        assert full.tobytes() == moving_card(1080, 1920).sample(0.5).frames[0].to_bytes()
        proxy, _ = get_frame(base, metadata["version"], 0.5, "proxy")
        assert proxy.size == (360, 640)


def test_proxy_bounds_larger_later_slides_and_keeps_letterboxing(tmp_path, monkeypatch):
    deck = Deck(
        slides=[
            Canvas(120, 240).background(color="#FF0000"),
            Canvas(1920, 1080).background(color="#00FF00"),
        ]
    )
    sizes = []
    original = video._SlideAnimator._composite_frame

    def record(self, *args, **kwargs):
        image = original(self, *args, **kwargs)
        sizes.append(image.size)
        return image

    monkeypatch.setattr(video._SlideAnimator, "_composite_frame", record)
    source = write_source(tmp_path, deck)
    try:
        metadata = source.timeline_metadata()
        pixels, slide, _ = source.timeline_frame(5, "proxy", metadata["version"])
        frame = Image.open(BytesIO(pixels))
        assert frame.size == (120, 240)
        assert slide == 1
        assert frame.getpixel((60, 120)) == (0, 255, 0)
        assert frame.getpixel((60, 0)) == (0, 0, 0)
        assert all(width <= 120 and height <= 240 for width, height in sizes)
    finally:
        source.close()


@pytest.mark.parametrize(
    "query",
    [
        "",
        "time=nan&resolution=proxy&version=x",
        "time=inf&resolution=proxy&version=x",
        "time=-1&resolution=proxy&version=x",
        "time=no&resolution=proxy&version=x",
        "time=0&resolution=giant&version=x",
        "time=0&time=1&resolution=proxy&version=x",
        "time=0&resolution=proxy&version=x&extra=1",
        "time=0&resolution=proxy",
    ],
)
def test_bad_frame_queries_fail_before_rendering(tmp_path, query, monkeypatch):
    source = write_source(tmp_path, moving_card())

    def forbidden(*args):
        raise AssertionError("Invalid requests must not render")

    monkeypatch.setattr(source, "timeline_frame", forbidden)
    with running(source) as base, pytest.raises(HTTPError) as error:
        urlopen(base + "/__quickthumb_frame?" + query, timeout=5)
    assert error.value.code == 400


def test_stale_version_and_save_during_render_never_return_mislabelled_pixels(
    tmp_path, monkeypatch
):
    source = write_source(tmp_path, moving_card())
    metadata = source.timeline_metadata()
    with pytest.raises(StaleTimelineError):
        source.timeline_frame(0, "proxy", "old")
    original = TimelinePreview.frame

    def change(preview, *args):
        result = original(preview, *args)
        source.invalidate()
        return result

    monkeypatch.setattr(TimelinePreview, "frame", change)
    with running(source) as base, pytest.raises(HTTPError) as error:
        get_frame(base, metadata["version"], 0.5)
    assert error.value.code == 409


def test_source_reload_retires_both_samplers_and_recovers_after_broken_edit(tmp_path, monkeypatch):
    source = write_source(tmp_path, moving_card())
    closed = []
    original = TimelinePreview.close

    def record(preview):
        closed.append(preview)
        original(preview)

    monkeypatch.setattr(TimelinePreview, "close", record)
    with running(source) as base:
        old = get_json(base)
        get_frame(base, old["version"], 0.5, "proxy")
        get_frame(base, old["version"], 0.5, "full")
        first = source._timeline
        assert first is not None and len(first._samplers) == 2
        source.path.write_text("broken", encoding="utf-8")
        with pytest.raises(HTTPError) as failure:
            get_json(base)
        assert failure.value.code == 500
        assert closed == [first] and not first._samplers
        source.path.write_text(Canvas(8, 4).background(color="#00FF00").to_json(), encoding="utf-8")
        new = get_json(base)
        assert new["version"] != old["version"]
        image, _ = get_frame(base, new["version"], 0)
        assert image.size == (8, 4) and image.getpixel((0, 0)) == (0, 255, 0, 255)
    assert len(closed) == 2


def test_python_source_is_loaded_once_for_independent_html_and_timeline_outputs(
    tmp_path, monkeypatch
):
    path = tmp_path / "slides.py"
    counter = tmp_path / "loads.txt"
    path.write_text(
        "from pathlib import Path\nfrom quickthumb import Canvas\n"
        f"p = Path({str(counter)!r})\np.write_text(p.read_text() + 'x' if p.exists() else 'x')\n"
        "canvas = Canvas(8,4).background(color='#112233')\n",
        encoding="utf-8",
    )
    source = SlideSource(path, {})
    with running(source) as base:
        metadata = get_json(base)
        get_frame(base, metadata["version"], 0)
        with urlopen(base + "/", timeout=5) as response:
            assert response.status == 200
        with urlopen(base + "/timeline", timeout=5) as response:
            shell = response.read().decode()
        assert "qt-seek" in shell and "__quickthumb_version" in shell
        get_frame(base, metadata["version"], 0, "proxy")
        assert counter.read_text() == "x"


def test_timeline_does_not_depend_on_html_export_and_escapes_source_name(tmp_path, monkeypatch):
    source = write_source(tmp_path, moving_card())
    source.path = source.path.rename(tmp_path / "<script>.json")

    def no_html(*args, **kwargs):
        raise AssertionError("HTML export should not run")

    monkeypatch.setattr(Canvas, "to_html", no_html)
    with running(source) as base:
        with urlopen(base + "/timeline", timeout=5) as response:
            shell = response.read().decode()
        assert "&lt;script&gt;.json" in shell
        metadata = get_json(base)
        get_frame(base, metadata["version"], 0.5)


def test_standalone_html_has_an_actionable_timeline_error(tmp_path):
    path = tmp_path / "slides.html"
    path.write_text("<!doctype html><body>Slides</body>")
    source = SlideSource(path, {})
    with running(source) as base:
        with pytest.raises(HTTPError) as error:
            urlopen(base + "/timeline", timeout=5)
        assert b"Python or JSON Canvas/Deck" in error.value.read()
        with urlopen(base + "/", timeout=5) as response:
            assert b"Slides" in response.read()


def test_empty_deck_fails_actionably():
    with pytest.raises(ValidationError, match="no slides"):
        TimelinePreview(Deck())


@pytest.mark.parametrize("limit", [0, -1, True, 0.5, math.inf, math.nan])
def test_invalid_internal_proxy_bound_is_rejected(limit):
    with pytest.raises(ValidationError, match="positive integer"):
        video.TimelineSampler(
            [moving_card()],
            [None],
            slide_duration=3,
            slide_durations=None,
            matte="#000000",
            preview_max_edge=limit,
        )


def test_source_serializes_seeks_in_different_resolutions(tmp_path, monkeypatch):
    source = write_source(tmp_path, moving_card())
    metadata = source.timeline_metadata()
    active = 0
    original = TimelinePreview.frame

    def checked(preview, *args):
        nonlocal active
        active += 1
        assert active == 1
        try:
            return original(preview, *args)
        finally:
            active -= 1

    monkeypatch.setattr(TimelinePreview, "frame", checked)
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            frames = list(
                pool.map(
                    lambda n: source.timeline_frame(
                        n / 10, "proxy" if n % 2 else "full", metadata["version"]
                    ),
                    range(20),
                )
            )
        assert len(frames) == 20
    finally:
        source.close()


def test_cli_forwards_timeline_launch_option(monkeypatch):
    import quickthumb._serve as module

    calls = []
    monkeypatch.setattr(module, "serve_slides", lambda **options: calls.append(options))
    result = CliRunner().invoke(app, ["serve", "slides.py", "--timeline", "--no-open"])
    assert result.exit_code == 0
    assert calls[0]["timeline"] is True and calls[0]["open_browser"] is False


def test_timeline_startup_failure_closes_loaded_source(tmp_path, monkeypatch):
    source = write_source(tmp_path, moving_card())
    closed = []
    monkeypatch.setattr(SlideSource, "close", lambda self: closed.append(self.path))
    monkeypatch.setattr(
        SlideSource,
        "timeline_metadata",
        lambda self: (_ for _ in ()).throw(ValidationError("invalid timeline")),
    )
    with pytest.raises(ValidationError, match="invalid timeline"):
        serve_slides(source.path, "127.0.0.1", 0, False, timeline=True)
    assert closed == [source.path]


def test_admitted_request_cannot_recreate_resources_after_source_close(tmp_path, monkeypatch):
    source = write_source(tmp_path, moving_card())
    metadata = source.timeline_metadata()
    admitted = threading.Event()
    resume = threading.Event()
    original = source.timeline_frame

    def delayed(*args):
        admitted.set()
        assert resume.wait(timeout=5)
        return original(*args)

    monkeypatch.setattr(source, "timeline_frame", delayed)
    with running(source) as base, ThreadPoolExecutor(max_workers=1) as pool:
        request = pool.submit(get_frame, base, metadata["version"], 0.5)
        assert admitted.wait(timeout=5)
        source.close()
        resume.set()
        with pytest.raises(HTTPError) as error:
            request.result(timeout=5)
        assert error.value.code == 500
        assert b"Slide source is closed" in error.value.read()
        assert source._timeline is None and source._cached_source is None
        with pytest.raises(RuntimeError, match="closed"):
            source.render()


def proxy_strip():
    preview = TimelinePreview(moving_card(1080, 1920))
    try:
        strip = Image.new("RGB", (1080, 640))
        for index, instant in enumerate((0, 0.5, 1)):
            data, _, _ = preview.frame(instant, "proxy")
            strip.paste(Image.open(BytesIO(data)), (index * 360, 0))
        return strip
    finally:
        preview.close()


def test_proxy_visual_snapshot():
    from pathlib import Path

    expected = Image.open(Path(__file__).parent / "snapshots" / "timeline_proxy.png").convert("RGB")
    actual = proxy_strip()
    assert actual.size == expected.size and actual.tobytes() == expected.tobytes()


def test_full_http_frames_match_lossless_gif_playback(tmp_path):
    from quickthumb import GifOptions

    canvas = (
        Canvas(20, 12)
        .background(color="#000000")
        .shape("rectangle", (2, 2), 10, 6, "#FF0000", animation=Fade(duration=1))
    )
    output = tmp_path / "animation.gif"
    canvas.render(str(output), animation=GifOptions(fps=4))
    source = write_source(tmp_path, canvas)
    with running(source) as base, Image.open(output) as exported:
        metadata = get_json(base)
        instant = 0.0
        for index in range(getattr(exported, "n_frames", 1)):
            exported.seek(index)
            image, _ = get_frame(base, metadata["version"], instant)
            assert image.tobytes() == exported.convert("RGBA").tobytes()
            instant += exported.info["duration"] / 1000


def test_timeline_reuses_json_variables_and_zero_duration_metadata(tmp_path):
    path = tmp_path / "slides.json"
    path.write_text(
        json.dumps(
            {
                "kind": "deck",
                "width": 8,
                "height": 4,
                "slides": [
                    {
                        "kind": "canvas",
                        "transition": {"effect": "cut", "advance_after": 0},
                        "layers": [{"type": "background", "color": "$COLOR"}],
                    }
                ],
            }
        )
    )
    source = SlideSource(path, {"COLOR": "#112233"})
    try:
        metadata = source.timeline_metadata()
        assert metadata["duration"] == 0
        assert metadata["segments"] == [
            {"slide": 0, "start": 0, "transition_end": 0, "animation_end": 0, "end": 0}
        ]
        data, slide, instant = source.timeline_frame(100, "full", metadata["version"])
        assert (slide, instant) == (0, 0)
        assert Image.open(BytesIO(data)).getpixel((0, 0)) == (17, 34, 51)
    finally:
        source.close()


def test_captioned_video_reverse_seeks_keep_native_pixels_and_proxy_layout(tmp_path):
    import shutil
    import subprocess

    from quickthumb.models import VideoCaption

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg and ffprobe render the real video timeline")
    clip = tmp_path / "clip.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=24x18:rate=10:duration=0.6",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(clip),
        ],
        check=True,
        timeout=20,
    )
    canvas = (
        Canvas(1080, 1920)
        .background(color="#112233")
        .video(
            str(clip),
            position=(100, 100),
            width=480,
            height=360,
            captions=[
                VideoCaption(
                    text="A timed caption",
                    font="assets/fonts/Roboto-Medium.ttf",
                    size=48,
                    start=0,
                    end=0.6,
                    position=(540, 1700),
                )
            ],
        )
    )
    source = write_source(tmp_path, canvas)
    try:
        metadata = source.timeline_metadata()
        assert any("video captions" in warning for warning in metadata["warnings"])
        for instant in (0.4, 0.1, 0.6, 0):
            expected = canvas.sample(instant).frames[0].to_image()
            data, _, _ = source.timeline_frame(instant, "full", metadata["version"])
            assert Image.open(BytesIO(data)).convert("RGBA").tobytes() == expected.tobytes()
            source.render()  # HTML clears shared Canvas contexts; seeking must still work.
            data, _, _ = source.timeline_frame(instant, "proxy", metadata["version"])
            assert (
                Image.open(BytesIO(data)).convert("RGBA").tobytes()
                == expected.resize((360, 640), Image.Resampling.LANCZOS).tobytes()
            )
        canvases = source._timeline._canvases
    finally:
        source.close()
    assert all(not canvas._ctx.video_decoder_cache for canvas in canvases)


def test_timeline_launch_opens_its_route_without_html_and_closes_source(
    tmp_path, monkeypatch, capsys
):
    import quickthumb._serve as module

    source = write_source(tmp_path, moving_card())
    opened = []
    monkeypatch.setattr(module, "SlideSource", lambda path, variables: source)

    def forbidden(*args, **kwargs):
        raise AssertionError("Timeline launch must not render an HTML slideshow")

    monkeypatch.setattr(source, "render", forbidden)

    class Server:
        server_address = ("127.0.0.1", 43161)

        def __init__(self, *args):
            pass

        def serve_forever(self):
            raise KeyboardInterrupt

        def server_close(self):
            pass

    class Timer:
        def __init__(self, interval, callback, args):
            self.callback, self.args = callback, args

        def start(self):
            self.callback(*self.args)

    monkeypatch.setattr(module, "ThreadingHTTPServer", Server)
    monkeypatch.setattr(module.threading, "Timer", Timer)
    monkeypatch.setattr(module.webbrowser, "open", opened.append)
    serve_slides(source.path, "127.0.0.1", 0, True, timeline=True)
    assert opened == ["http://localhost:43161/timeline"]
    assert "Timeline preview: http://localhost:43161/timeline" in capsys.readouterr().out
    assert source._closed and source._timeline is None
