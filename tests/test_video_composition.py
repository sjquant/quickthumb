"""Behavioral specifications for composing video layers like any other layer."""

import json
import shutil

import pytest
from quickthumb import (
    AnimationSpec,
    Canvas,
    Fade,
    KeyframeSpec,
    LayerMask,
    PositionTrack,
    TimingSpec,
)
from quickthumb.models import Filter

HAS_FFMPEG = shutil.which("ffmpeg") is not None
SOURCE = "assets/video/ordinary-coffee.mp4"


def lit_span(image, row):
    """Return the horizontal extent of visible pixels along one row."""
    rgb = image.convert("RGB")
    lit = [x for x in range(rgb.width) if sum(rgb.getpixel((x, row))) > 60]
    return (min(lit), max(lit)) if lit else None


def clip_canvas(**video_options):
    """Place one clip on a dark canvas with the given layer options."""
    return (
        Canvas(640, 360)
        .background(color="#0A0E12")
        .video(
            SOURCE,
            position=(40, 20),
            width=560,
            height=315,
            fit="cover",
            trim_start=1.0,
            trim_end=4.0,
            duration=3.0,
            **video_options,
        )
    )


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg is required")
class TestVideoLayerComposition:
    """Footage should grade, round, fade, and animate like an image layer."""

    def test_should_grade_footage_through_layer_effects(self):
        """Given a filter effect, when a frame renders, then the footage is graded."""
        # Given: the same clip with and without a fully desaturating filter
        plain = clip_canvas()
        graded = clip_canvas(effects=[Filter(saturation=0.0)])

        # When: both are sampled at the same instant
        plain_pixel = plain.render_frame(1.0).convert("RGB").getpixel((320, 180))
        graded_pixel = graded.render_frame(1.0).convert("RGB").getpixel((320, 180))

        # Then: the graded clip is neutral while the original keeps its colour
        assert len(set(graded_pixel)) == 1
        assert plain_pixel != graded_pixel

    def test_should_round_a_clips_corners_and_carry_its_opacity(self):
        """Given radius and opacity, when rendered, then the clip is shaped and blended."""
        # Given: a clip with rounded corners over a known background
        canvas = clip_canvas(border_radius=40, opacity=0.5)

        # When: a corner and the centre are sampled
        frame = canvas.render_frame(1.0).convert("RGB")
        corner = frame.getpixel((42, 22))
        centre = frame.getpixel((320, 180))

        # Then: the corner is cut away to the background and the body is blended
        assert corner == (10, 14, 18)
        assert centre != (10, 14, 18)

    def test_should_mask_a_clip_into_a_shape(self):
        """Given a mask, when rendered, then footage only shows inside the mask."""
        # Given: a clip masked to an ellipse inside its own box
        canvas = clip_canvas(
            mask=LayerMask(shape="ellipse", position=(160, 20), width=320, height=315)
        )

        # When: the frame is sampled inside and outside the ellipse
        frame = canvas.render_frame(1.0).convert("RGB")

        # Then: only the masked region carries picture
        assert frame.getpixel((320, 180)) != (10, 14, 18)
        assert frame.getpixel((60, 30)) == (10, 14, 18)

    def test_should_play_an_entrance_reveal_over_a_running_clip(self):
        """Given a fade, when the slide plays, then the clip fades while it runs."""
        # Given: a clip carrying a one-second fade
        canvas = clip_canvas(animation=Fade(duration=1.0))

        # When: the exporter samples the slide before and after the fade
        from quickthumb._export_video import _SlideAnimator

        animator = _SlideAnimator(canvas, {})
        early = animator.frame_at(0.1).convert("RGB").getpixel((320, 180))
        settled = animator.frame_at(2.0).convert("RGB").getpixel((320, 180))

        # Then: the clip starts nearly invisible and ends fully composited
        assert sum(early) < sum(settled)

    def test_should_move_a_clip_while_it_plays(self):
        """Given a position track, when the clip plays, then the clip itself travels."""
        # Given: a small clip that should slide across the frame as it plays
        canvas = (
            Canvas(640, 360)
            .background(color="#0A0E12")
            .video(
                SOURCE,
                position=(0, 20),
                width=300,
                height=169,
                fit="cover",
                trim_start=1.0,
                trim_end=4.0,
                duration=3.0,
                animation=AnimationSpec.timeline(
                    PositionTrack(
                        keyframes=[
                            KeyframeSpec(time=0.0, value=(0.0, 0.0)),
                            KeyframeSpec(time=3.0, value=(300.0, 0.0)),
                        ]
                    ),
                    timing=TimingSpec(start=0.0, duration=3.0),
                    easing="linear",
                ),
            )
        )

        # When: the exporter samples the start and the end of the track
        from quickthumb._export_video import _SlideAnimator

        animator = _SlideAnimator(canvas, {})

        # Then: the clip has moved its own width across the frame
        assert lit_span(animator.frame_at(0.0), 100) == (0, 299)
        assert lit_span(animator.frame_at(3.0), 100) == (300, 599)

    def test_should_round_trip_the_new_clip_options_through_json(self):
        """Given a composed clip, when serialized, then every option survives."""
        # Given: a clip using the shared layer vocabulary
        canvas = clip_canvas(border_radius=12, opacity=0.8, effects=[Filter(saturation=0.5)])

        # When: the composition round-trips through public JSON
        payload = json.loads(canvas.to_json())
        restored = json.loads(Canvas.from_json(canvas.to_json()).to_json())

        # Then: nothing is dropped on the way out or back in
        layer = payload["layers"][1]
        assert layer["border_radius"] == 12
        assert layer["opacity"] == 0.8
        assert layer["effects"][0]["saturation"] == 0.5
        assert restored == payload
