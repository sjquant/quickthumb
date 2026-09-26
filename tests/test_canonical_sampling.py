"""Black-box specifications for canonical still and timeline sampling."""

import copy
import shutil
import subprocess
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from quickthumb import (
    AnimationSpec,
    Canvas,
    Deck,
    Fade,
    FrameSequence,
    KeyframeSpec,
    ScaleTrack,
    TimingSpec,
)
from quickthumb import transitions as tr
from quickthumb.errors import RenderingError, ValidationError

HAS_FFMPEG = shutil.which("ffmpeg") is not None

WHITE = (255, 255, 255, 255)
BLACK = (0, 0, 0, 255)
RED = (255, 45, 85, 255)
TEAL = (0, 128, 128, 255)


def fading_card() -> Canvas:
    """A white 40x30 card whose red rectangle fades in over one second."""
    return (
        Canvas(40, 30)
        .background(color="#FFFFFF")
        .shape("rectangle", (5, 5), 20, 15, "#FF2D55", animation=Fade(duration=1.0))
    )


def gif_playback(data: bytes) -> tuple[list[float], list[bytes], float]:
    """Decode GIF frames as (start times, RGBA buffers, total playback length)."""
    starts: list[float] = []
    buffers: list[bytes] = []
    elapsed = 0.0
    with Image.open(BytesIO(data)) as image:
        for index in range(getattr(image, "n_frames", 1)):
            image.seek(index)
            starts.append(elapsed)
            buffers.append(image.convert("RGBA").tobytes())
            elapsed += image.info["duration"] / 1000
    return starts, buffers, elapsed


def test_still_sample_matches_raster_export_and_keeps_transparency(tmp_path: Path):
    """A still sample of a partly transparent canvas carries the exact RGBA pixels
    of its PNG export, including fully transparent pixels, with no timing."""
    # Given: a canvas whose left half is painted and right half is transparent
    canvas = Canvas(8, 4).shape("rectangle", (0, 0), 4, 4, "#008080")

    # When: a still sample is captured and the canvas is exported as PNG
    still = canvas.sample()
    result = canvas.export(tmp_path / "still.png")

    # Then: the sample describes one untimed straight-alpha RGBA page
    assert still.capture == "still"
    assert (still.duration, still.fps, still.matte, still.timeline) == (0.0, None, None, [])
    [frame] = still.frames
    assert (frame.index, frame.slide, frame.time) == (0, 0, None)
    assert (frame.width, frame.height, frame.mode) == (8, 4, "RGBA")
    image = frame.to_image()
    assert image.getpixel((1, 1)) == TEAL
    assert image.getpixel((6, 1))[3] == 0

    # Then: the pixels are exactly those of the raster export
    with Image.open(result.written_paths[0]) as exported:
        assert exported.convert("RGBA").tobytes() == frame.to_bytes()


def test_still_deck_sample_orders_one_page_per_slide_at_its_own_size():
    """A still sample of a mixed-size deck yields one settled frame per slide in
    slide order, each at that slide's own dimensions."""
    # Given: a deck whose second slide is larger than its first
    deck = Deck(
        slides=[
            Canvas(8, 4).background(color="#FFFFFF"),
            Canvas(12, 6).background(color="#000000"),
        ]
    )

    # When: a still sample is captured
    still = deck.sample()

    # Then: frames follow slide order and keep per-slide dimensions
    assert still.kind == "deck"
    assert [(f.index, f.slide, f.time) for f in still.frames] == [(0, 0, None), (1, 1, None)]
    assert [(f.width, f.height) for f in still.frames] == [(8, 4), (12, 6)]
    assert still.frames[0].to_image().getpixel((0, 0)) == WHITE
    assert still.frames[1].to_image().getpixel((0, 0)) == BLACK


def test_uniform_timeline_capture_covers_motion_and_settled_hold():
    """Sampling a fading canvas at 4 fps observes every quarter second from zero up
    to (not including) the timeline end, where the one-second fade is followed by
    the one-second settled hold."""
    # Given: a card whose rectangle fades in over one second
    canvas = fading_card()

    # When: the timeline is captured on a uniform 4 fps grid with a one-second hold
    capture = canvas.sample(fps=4, hold=1.0)

    # Then: timing metadata describes a two-second single-slide timeline
    assert capture.capture == "timeline"
    assert (capture.fps, capture.duration, capture.matte) == (4.0, 2.0, "#000000")
    [segment] = capture.timeline
    assert (segment.start, segment.transition_end, segment.animation_end, segment.end) == (
        0.0,
        0.0,
        1.0,
        2.0,
    )

    # Then: frames are ordered by ascending time on the grid
    assert [frame.time for frame in capture.frames] == [i / 4 for i in range(8)]
    assert [frame.index for frame in capture.frames] == list(range(8))

    # Then: the rectangle starts hidden, is partial mid-fade, and settles opaque
    pixels = [frame.to_image().getpixel((10, 10)) for frame in capture.frames]
    assert pixels[0] == WHITE
    assert WHITE != pixels[2] != RED
    assert pixels[4:] == [RED] * 4


def test_timeline_frames_are_opaque_on_the_requested_matte():
    """Timeline frames composite transparent canvas regions onto the matte color,
    as animated exports do, and report that matte in canonical #RRGGBB form."""
    # Given: a canvas with a transparent right half
    canvas = Canvas(8, 4).shape("rectangle", (0, 0), 4, 4, "#008080")

    # When: one timeline instant is captured on a matte named "white"
    capture = canvas.sample(0.0, matte="white")

    # Then: the transparent region shows the matte and every pixel is opaque
    image = capture.frames[0].to_image()
    assert capture.matte == "#FFFFFF"
    assert image.getpixel((6, 1)) == WHITE
    assert image.getchannel("A").getextrema() == (255, 255)


def test_equivalent_canvas_and_single_slide_deck_capture_identical_observations():
    """A canvas and a deck containing only that canvas report identical frame
    digests, timing, and environment for the same timeline capture, and
    repeated captures serialize to identical JSON."""
    # Given: a canvas with a scale animation and a deck wrapping it
    canvas = (
        Canvas(40, 30)
        .background(color="#FFFFFF")
        .shape(
            "rectangle",
            (10, 10),
            20,
            10,
            "#FF2D55",
            animation=AnimationSpec(
                tracks=[
                    ScaleTrack(
                        keyframes=[KeyframeSpec(time=0, value=0.2), KeyframeSpec(time=1, value=1)]
                    )
                ],
                timing=TimingSpec(duration=1.0),
            ),
        )
    )
    deck = Deck(slides=[canvas])

    # When: both documents are captured at 5 fps with a half-second hold
    canvas_capture = canvas.sample(fps=5, hold=0.5)
    deck_capture = deck.sample(fps=5, hold=0.5)

    # Then: pixels and timing agree apart from the document kind
    assert canvas_capture.model_dump(exclude={"kind"}) == deck_capture.model_dump(exclude={"kind"})
    assert len({frame.sha256 for frame in canvas_capture.frames}) > 1

    # Then: a repeated capture is byte-for-byte the same JSON document
    assert canvas.sample(fps=5, hold=0.5).model_dump_json() == canvas_capture.model_dump_json()
    assert FrameSequence.model_validate_json(canvas_capture.model_dump_json()) == canvas_capture


def test_deck_timeline_places_transitions_and_slide_durations():
    """A deck timeline starts each slide at the previous slide's end, plays its
    incoming transition from that point, honors an explicit slide duration, and
    shows the last settled frame at or after the timeline end."""
    # Given: a white slide held for an explicit 1.5s, then a black slide that
    # pushes in over 1s and holds for the default hold
    deck = (
        Deck()
        .slide(Canvas(40, 30).background(color="#FFFFFF"), duration=1.5)
        .slide(
            Canvas(40, 30).background(color="#000000"),
            transition=tr.Push(duration=1.0, direction="left"),
        )
    )

    # When: instants around the slide boundary and past the end are sampled
    capture = deck.sample([0.0, 1.4, 1.5, 2.0, 2.6, 9.0], hold=0.5)

    # Then: segments describe absolute slide windows on one timeline
    assert [(s.slide, s.start, s.transition_end, s.end) for s in capture.timeline] == [
        (0, 0.0, 0.0, 1.5),
        (1, 1.5, 2.5, 3.0),
    ]
    assert capture.duration == 3.0

    # Then: frames report their slide, with the boundary instant owned by slide 1
    assert [frame.slide for frame in capture.frames] == [0, 0, 1, 1, 1, 1]
    mid_push = capture.frames[3].to_image()
    assert mid_push.getpixel((39, 15)) == BLACK and mid_push.getpixel((0, 15)) == WHITE

    # Then: the transition start still shows slide 0 and the settled tail shows slide 1
    pixels = [frame.to_image().getpixel((20, 15)) for frame in capture.frames]
    assert pixels[:3] == [WHITE] * 3
    assert pixels[4:] == [BLACK] * 2


def crossfade_deck() -> Deck:
    """The fading card followed by a blue slide that cross-fades in by default."""
    return Deck(
        slides=[
            fading_card(),
            Canvas(40, 30)
            .background(color="#1131AA")
            .shape("rectangle", (10, 10), 10, 10, "#00FF00", animation=Fade(duration=0.5)),
        ]
    )


def morph_deck() -> Deck:
    """Two white slides whose keyed red box moves and grows through a one-second Morph."""
    return (
        Deck()
        .slide(
            Canvas(40, 30)
            .background(color="#FFFFFF")
            .shape("rectangle", (2, 2), 10, 10, "#FF2D55", motion_key="box")
        )
        .slide(
            Canvas(40, 30)
            .background(color="#FFFFFF")
            .shape("rectangle", (24, 14), 14, 14, "#FF2D55", motion_key="box"),
            transition=tr.Morph(duration=1.0),
        )
    )


@pytest.mark.parametrize(
    ("build", "encode"),
    [
        pytest.param(fading_card, lambda doc: doc.to_gif(fps=4, hold=1.0), id="canvas-motion"),
        pytest.param(
            crossfade_deck,
            lambda doc: doc.to_gif(fps=4, slide_duration=1.0),
            id="deck-crossfade",
        ),
        pytest.param(
            morph_deck, lambda doc: doc.to_gif(fps=4, slide_duration=1.0), id="deck-morph"
        ),
    ],
)
def test_timeline_capture_reproduces_gif_playback(build, encode):
    """Sampling the canonical timeline at each GIF frame's start time yields the
    exact pixels the GIF shows, and the timeline duration equals the GIF's total
    playback length."""
    # Given: the document's 4 fps GIF export with a one-second hold
    document = build()
    starts, buffers, playback = gif_playback(encode(document))

    # When: the canonical timeline is sampled at the GIF frame start times
    capture = document.sample(starts, hold=1.0)

    # Then: every displayed GIF frame matches its canonical observation
    assert capture.duration == pytest.approx(playback)
    assert [frame.to_bytes() for frame in capture.frames] == buffers


def test_timeline_duration_does_not_depend_on_the_sampling_request():
    """The timeline a document plays has one duration and one set of slide
    windows whether it is observed at explicit instants or on any fps grid, and
    a zero-length timeline is observed by exactly one frame at time zero."""
    # Given: a fading card and a static card with no settled hold
    fading = fading_card()
    instant = Canvas(40, 30).background(color="#FFFFFF")

    # When: each is captured at explicit instants and on different grids
    explicit = fading.sample([0.5], hold=0.25)
    coarse = fading.sample(fps=1, hold=0.25)
    fine = fading.sample(fps=120, hold=0.25)
    zero_explicit = instant.sample(0.0, hold=0)
    zero_grid = instant.sample(fps=4, hold=0)

    # Then: duration and slide windows are identical across requests
    assert explicit.duration == coarse.duration == fine.duration == 1.25
    assert explicit.timeline == coarse.timeline == fine.timeline
    assert zero_explicit.duration == zero_grid.duration == 0.0
    assert [frame.time for frame in zero_grid.frames] == [0.0]


def test_slide_boundaries_survive_float_accumulation():
    """Slide windows built from float sums such as 0.1 + 0.2 are published as
    exact decimal instants, the boundary instant belongs to the incoming slide,
    and a uniform grid ends before the timeline end."""
    # Given: three cut slides lasting 0.1s, 0.2s, and 0.2s
    deck = (
        Deck()
        .slide(Canvas(8, 8).background(color="#FFFFFF"), duration=0.1)
        .slide(Canvas(8, 8).background(color="#000000"), transition=tr.Cut(), duration=0.2)
        .slide(Canvas(8, 8).background(color="#008080"), transition=tr.Cut(), duration=0.2)
    )

    # When: the deck timeline is captured at 10 fps
    capture = deck.sample(fps=10)

    # Then: slide windows are exact and each frame reports the slide on screen
    assert [(s.start, s.end) for s in capture.timeline] == [(0.0, 0.1), (0.1, 0.3), (0.3, 0.5)]
    assert [(frame.time, frame.slide) for frame in capture.frames] == [
        (0.0, 0),
        (0.1, 1),
        (0.2, 1),
        (0.3, 2),
        (0.4, 2),
    ]
    assert capture.frames[3].to_image().getpixel((0, 0)) == TEAL


@pytest.mark.parametrize(
    "request_sample",
    [
        pytest.param(lambda document: document.sample(), id="still"),
        pytest.param(lambda document: document.sample(fps=1), id="timeline"),
    ],
)
def test_oversized_capture_is_rejected_before_rendering(request_sample):
    """Sampling a document whose single frame exceeds the 768 MiB capture budget
    fails validation up front, for still and timeline captures, rather than
    allocating pixels it cannot hold."""
    # Given: an empty 20000x20000 canvas, whose one RGBA frame needs about 1.5 GiB
    canvas = Canvas(20000, 20000)

    # When / Then: the capture is refused with the budget explained
    with pytest.raises(ValidationError, match="capture budget"):
        request_sample(canvas)


@pytest.mark.parametrize(
    "request_sample",
    [
        pytest.param(lambda document: document.sample([0.0] * 100_001), id="explicit-times"),
        pytest.param(lambda document: document.sample(fps=120, hold=1000.0), id="fps-grid"),
    ],
)
def test_captures_beyond_the_observation_limit_are_rejected(request_sample):
    """A capture may observe at most 100000 instants: more explicit times than
    that, or an fps grid over a timeline long enough to exceed it (120 fps over
    a 1000-second hold), fails validation instead of rendering any frame."""
    # Given: a small static card, cheap enough that only the request size matters
    canvas = Canvas(8, 8).background(color="#FFFFFF")

    # When / Then: the oversized request is refused with the limit explained
    with pytest.raises(ValidationError, match="at most 100000"):
        request_sample(canvas)


@pytest.fixture()
def short_clip(tmp_path: Path) -> Path:
    """A half-second 16x16 solid red H.264 clip without audio."""
    output = tmp_path / "clip.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=16x16:r=10:d=0.5",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ],
        check=True,
    )
    return output


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg is required")
def test_video_documents_record_the_ffmpeg_that_decodes_them(short_clip: Path):
    """A document containing a video layer reports the FFmpeg version in its
    sampling environment, while a document without video reports none."""
    # Given: a canvas with a video layer and one without
    with_video = Canvas(16, 16).video(str(short_clip), (0, 0), 16, 16)
    without_video = Canvas(16, 16).background(color="#FFFFFF")

    # When: both are sampled
    video_environment = with_video.sample(0.1).environment
    plain_environment = without_video.sample(0.1).environment

    # Then: only the video document names the decoder that produced its pixels
    assert video_environment.ffmpeg_version
    assert plain_environment.ffmpeg_version is None


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg is required")
def test_video_sampling_fails_before_rendering_without_ffmpeg(
    short_clip: Path, monkeypatch: pytest.MonkeyPatch
):
    """Sampling a video document with an unusable FFmpeg fails with a rendering
    error instead of returning pixels from an undescribed environment."""
    # Given: a video canvas, then QUICKTHUMB_FFMPEG pointing at a missing binary
    canvas = Canvas(16, 16).video(str(short_clip), (0, 0), 16, 16)
    monkeypatch.setenv("QUICKTHUMB_FFMPEG", str(short_clip.parent / "missing-ffmpeg"))

    # When / Then: both still and timeline captures are refused
    with pytest.raises(RenderingError, match="FFmpeg"):
        canvas.sample()
    with pytest.raises(RenderingError, match="FFmpeg"):
        canvas.sample(0.1)


def test_frames_whose_digest_does_not_match_their_pixels_are_rejected():
    """A serialized frame is accepted back only when its sha256 and dimensions
    describe its decoded pixel data."""
    # Given: a serialized still capture
    payload = Canvas(4, 4).background(color="#FFFFFF").sample().model_dump(mode="json")
    tampered_digest = copy.deepcopy(payload)
    tampered_digest["frames"][0]["sha256"] = "0" * 64
    tampered_size = copy.deepcopy(payload)
    tampered_size["frames"][0]["width"] = 5

    # When / Then: the untouched payload round-trips and tampered ones are refused
    assert FrameSequence.model_validate(payload).frames[0].sha256 == payload["frames"][0]["sha256"]
    for tampered in (tampered_digest, tampered_size):
        with pytest.raises(ValidationError, match="sha256|width"):
            FrameSequence.model_validate(tampered)


@pytest.mark.parametrize(
    ("args", "kwargs"),
    [
        pytest.param((0.5,), {"fps": 10}, id="time-and-fps"),
        pytest.param(([1.0, 0.5],), {}, id="descending-times"),
        pytest.param(([],), {}, id="no-times"),
        pytest.param((-0.1,), {}, id="negative-time"),
        pytest.param(((float("nan"),),), {}, id="nan-time"),
        pytest.param((), {"fps": 0}, id="zero-fps"),
        pytest.param((), {"fps": 121}, id="fps-above-export-limit"),
        pytest.param((), {"fps": True}, id="boolean-fps"),
        pytest.param((0.0,), {"hold": -1}, id="negative-hold"),
        pytest.param((), {"hold": float("inf")}, id="infinite-hold-on-still"),
        pytest.param((), {"matte": "not-a-color"}, id="unknown-matte-on-still"),
    ],
)
def test_sampling_rejects_invalid_requests(args: tuple, kwargs: dict):
    """Sampling rejects ambiguous, unordered, non-finite, or out-of-range requests
    and unknown matte colors, for still and timeline captures alike, instead of
    guessing or silently ignoring an argument."""
    # Given: a sampleable canvas
    canvas = fading_card()

    # When / Then: the invalid request fails validation
    with pytest.raises(ValidationError):
        canvas.sample(*args, **kwargs)
