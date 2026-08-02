"""Behavioral specifications for rendering canonical motion into pixels."""

import shutil

import pytest
from quickthumb import (
    AnimationSpec,
    BlurTrack,
    Canvas,
    Deck,
    KeyframeSpec,
    PositionTrack,
    RotationTrack,
    ScaleTrack,
    capabilities_for,
)
from quickthumb import transitions as tr

HAS_FFMPEG = shutil.which("ffmpeg") is not None


def timeline(track, duration=2.0):
    """Build a linear timeline that starts at the top of the slide."""
    from quickthumb import TimingSpec

    return AnimationSpec.timeline(
        track, timing=TimingSpec(start=0.0, duration=duration), easing="linear"
    )


def solid_pixels(image, threshold=400):
    """Count pixels bright enough to be the layer's solid core, not its halo."""
    rgb = image.convert("RGB")
    return sum(
        1
        for x in range(rgb.width)
        for y in range(rgb.height)
        if sum(rgb.getpixel((x, y))) > threshold
    )


def ink_bounds(image):
    """Return the bounding box of everything brighter than the background."""
    rgb = image.convert("RGB")
    lit = [
        (x, y)
        for x in range(rgb.width)
        for y in range(rgb.height)
        if sum(rgb.getpixel((x, y))) > 90
    ]
    if not lit:
        return None
    xs = [point[0] for point in lit]
    ys = [point[1] for point in lit]
    return min(xs), min(ys), max(xs), max(ys)


def marked_canvas(animation):
    """Place one bright square on a dark canvas under the given animation."""
    return (
        Canvas(240, 240)
        .background(color="#0A0E12")
        .shape(
            shape="rectangle",
            position=(100, 100),
            width=40,
            height=40,
            color="#E8A552",
            animation=animation,
        )
    )


class TestCanonicalMotionRendering:
    """Canonical motion has to reach the pixels, not just the timeline."""

    def test_should_move_a_layer_along_its_position_track(self):
        """Given a position track, when frames are sampled, then the layer travels."""
        # Given: a square that should slide 100px right over two seconds
        canvas = marked_canvas(
            timeline(
                PositionTrack(
                    keyframes=[
                        KeyframeSpec(time=0.0, value=(0.0, 0.0)),
                        KeyframeSpec(time=2.0, value=(100.0, 0.0)),
                    ]
                )
            )
        )

        # When: the composition is sampled across the track
        starts = [ink_bounds(canvas.render_frame(time))[0] for time in (0.0, 1.0, 2.0)]

        # Then: it is where the track says it is at every sample
        assert starts == [100, 150, 200]

    def test_should_scale_a_layer_about_its_own_centre(self):
        """Given a scale track, when it settles, then the layer grows around its centre."""
        # Given: a square that should double in size
        canvas = marked_canvas(
            timeline(
                ScaleTrack(
                    keyframes=[
                        KeyframeSpec(time=0.0, value=1.0),
                        KeyframeSpec(time=2.0, value=2.0),
                    ]
                )
            )
        )

        # When: the first and last frames are measured
        start = ink_bounds(canvas.render_frame(0.0))
        end = ink_bounds(canvas.render_frame(2.0))

        # Then: the box doubles while keeping the same centre
        assert start == (100, 100, 139, 139)
        assert end == (80, 80, 159, 159)

    def test_should_rotate_and_blur_a_layer_from_its_tracks(self):
        """Given rotation and blur tracks, when sampled, then both reach the frame."""
        # Given: one square that turns and one that softens
        rotating = marked_canvas(
            timeline(
                RotationTrack(
                    keyframes=[
                        KeyframeSpec(time=0.0, value=0.0),
                        KeyframeSpec(time=2.0, value=45.0),
                    ]
                )
            )
        )
        blurring = marked_canvas(
            timeline(
                BlurTrack(
                    keyframes=[
                        KeyframeSpec(time=0.0, value=0.0),
                        KeyframeSpec(time=2.0, value=6.0),
                    ]
                )
            )
        )

        # When: each is sampled before and after its track runs
        square = ink_bounds(rotating.render_frame(0.0))
        turned = ink_bounds(rotating.render_frame(2.0))

        # Then: a turned square occupies a wider footprint than an upright one
        assert turned[2] - turned[0] > square[2] - square[0]

        # Then: blur spreads the same ink over a larger, softer area
        assert solid_pixels(blurring.render_frame(2.0)) < solid_pixels(blurring.render_frame(0.0))
        assert ink_bounds(blurring.render_frame(2.0))[0] < square[0]

    def test_should_zoom_an_image_inside_its_frame_instead_of_scaling_the_layer(self):
        """Given ken burns, when it plays, then the frame holds while content zooms."""
        # Given: an image layer under the viewport-zoom preset
        canvas = Canvas(240, 240).image(
            path="tests/fixtures/sample_image.jpg",
            position=(40, 40),
            width=160,
            height=160,
            fit="cover",
            animation=AnimationSpec.ken_burns(direction="in", duration=2.0),
        )

        # When: the first and last frames are compared
        start = canvas.render_frame(0.0)
        end = canvas.render_frame(2.0)

        # Then: the layer keeps its frame to the pixel while its content moves
        assert all(abs(a - b) <= 1 for a, b in zip(ink_bounds(start), ink_bounds(end), strict=True))
        assert start.tobytes() != end.tobytes()

    @pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg is required")
    def test_should_render_identical_geometry_for_stills_and_video(self):
        """Given one composition, when both pipelines run, then they agree frame for frame."""
        # Given: a slide whose only motion is a canonical position track
        canvas = marked_canvas(
            timeline(
                PositionTrack(
                    keyframes=[
                        KeyframeSpec(time=0.0, value=(0.0, 0.0)),
                        KeyframeSpec(time=2.0, value=(100.0, 40.0)),
                    ]
                )
            )
        )
        deck = Deck(240, 240).slide(canvas, transition=tr.Cut(advance_after=2.0))

        # When: the still pipeline and the video pipeline sample the same instant
        from quickthumb._export_video import _SlideAnimator

        still = canvas.render_frame(1.0).convert("RGB")
        moving = _SlideAnimator(deck.slides[0], {}).frame_at(1.0).convert("RGB")

        # Then: neither pipeline is the odd one out
        assert ink_bounds(still) == ink_bounds(moving) == (150, 120, 189, 159)


class TestCanonicalMotionDeclarations:
    """What the capability registry promises has to match what validation says."""

    def test_should_declare_rendered_motion_as_supported_rather_than_static(self):
        """Given canonical geometry, when validated, then support agrees with the registry."""
        # Given: a layer carrying position, scale, and blur tracks
        canvas = marked_canvas(
            timeline(
                PositionTrack(
                    keyframes=[
                        KeyframeSpec(time=0.0, value=(0.0, 0.0)),
                        KeyframeSpec(time=2.0, value=(100.0, 0.0)),
                    ]
                )
            )
        )

        # When: the registry and the validator are both consulted for video
        declared = capabilities_for("video")["position"].support
        reported = [item for item in canvas.validate_export("video") if item.feature == "position"]

        # Then: both say the motion is rendered, and nothing claims a static fallback
        assert declared == "full"
        assert [(item.support, item.fallback) for item in reported] == [("full", None)]

    def test_should_still_declare_a_fallback_for_motion_it_cannot_render(self):
        """Given a colour track, when validated, then the unrendered feature is declared."""
        # Given: a colour track, which no pixel pipeline consumes
        from quickthumb import ColorTrack

        canvas = marked_canvas(
            timeline(
                ColorTrack(
                    keyframes=[
                        KeyframeSpec(time=0.0, value="#E8A552"),
                        KeyframeSpec(time=2.0, value="#F2EFE9"),
                    ]
                )
            )
        )

        # When: the registry and the validator are both consulted
        declared = capabilities_for("video")["color"]
        reported = [item for item in canvas.validate_export("video") if item.feature == "color"]

        # Then: the honest answer is the same from both
        assert (declared.support, declared.fallback) == ("unsupported", "static")
        assert [(item.support, item.fallback) for item in reported] == [("fallback", "static")]
