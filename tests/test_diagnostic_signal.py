"""Behavioral specifications for what diagnose() should stay quiet about."""

from quickthumb import Background, Canvas, Fade, Wipe

FONT = "assets/fonts/Roboto-Medium.ttf"


def codes(canvas, code):
    """Return every finding of one code raised by a canvas."""
    return [finding for finding in canvas.diagnose() if finding.code == code]


class TestBleedingLayersAreNotCrowding:
    """Content stopping short of an edge is the problem, not content covering it."""

    def test_should_not_call_a_full_bleed_layer_crowded(self):
        """Given a layer covering the canvas, when diagnosed, then no edge is crowded."""
        # Given: a background panel filling the whole frame
        canvas = Canvas(1280, 720).shape(
            shape="rectangle", position=(0, 0), width=1280, height=720, color="#0A0E12"
        )

        # When: the composition is diagnosed
        findings = codes(canvas, "edge-crowding")

        # Then: a layer that cannot be moved off an edge is not asked to move
        assert findings == []

    def test_should_not_call_a_full_width_band_crowded_on_the_edges_it_spans(self):
        """Given a full-width band, when diagnosed, then its spanned edges are quiet."""
        # Given: a scrim running the width of the frame and bleeding off the bottom
        canvas = Canvas(1280, 720).shape(
            shape="rectangle", position=(0, 400), width=1280, height=320, color="#0A0E12"
        )

        # When: the composition is diagnosed
        findings = codes(canvas, "edge-crowding")

        # Then: nothing is reported for the edges the band deliberately covers
        assert findings == []

    def test_should_still_report_content_that_stops_short_of_an_edge(self):
        """Given a layer near an edge, when diagnosed, then crowding is still reported."""
        # Given: a small block sitting just inside the left edge
        canvas = Canvas(1280, 720).shape(
            shape="rectangle", position=(4, 300), width=120, height=60, color="#E8A552"
        )

        # When: the composition is diagnosed
        findings = codes(canvas, "edge-crowding")

        # Then: the rule still earns its keep
        assert len(findings) == 1
        assert "left" in findings[0].message


class TestAnimatedLayersAreNotRedundant:
    """A settled frame is not the whole slide when layers animate into it."""

    def test_should_not_call_a_layer_hidden_by_something_that_animates_in(self):
        """Given an animated cover, when diagnosed, then the layer beneath is not hidden."""
        # Given: a dim placeholder with a bright bar that wipes across it
        canvas = (
            Canvas(400, 200)
            .background(color="#0A0E12")
            .shape(
                shape="rectangle",
                position=(40, 80),
                width=320,
                height=40,
                color="#E8A552",
                opacity=0.25,
            )
            .shape(
                shape="rectangle",
                position=(40, 80),
                width=320,
                height=40,
                color="#E8A552",
                animation=Wipe(direction="right", duration=1.0),
            )
        )

        # When: the composition is diagnosed
        # Then: the pre-roll state is not mistaken for a redundant layer
        assert codes(canvas, "layer-hidden") == []

    def test_should_not_call_an_animated_cover_an_overlap_collision(self):
        """Given an animated cover, when diagnosed, then the pair is not a collision."""
        # Given: the same reveal pair
        canvas = (
            Canvas(400, 200)
            .background(color="#0A0E12")
            .shape(
                shape="rectangle",
                position=(40, 80),
                width=320,
                height=40,
                color="#E8A552",
                opacity=0.25,
            )
            .shape(
                shape="rectangle",
                position=(40, 80),
                width=320,
                height=40,
                color="#E8A552",
                animation=Fade(duration=1.0),
            )
        )

        # When: the composition is diagnosed
        # Then: a before-and-after pair is read as one, not as two things clashing
        assert codes(canvas, "layer-overlap") == []

    def test_should_still_report_two_static_layers_stacked_on_each_other(self):
        """Given no animation, when diagnosed, then a covered layer is still reported."""
        # Given: the same geometry with nothing animating
        canvas = (
            Canvas(400, 200)
            .background(color="#0A0E12")
            .shape(shape="rectangle", position=(40, 80), width=320, height=40, color="#8A949C")
            .shape(shape="rectangle", position=(40, 80), width=320, height=40, color="#E8A552")
        )

        # When: the composition is diagnosed
        # Then: a genuinely redundant layer is still called out
        assert codes(canvas, "layer-hidden") != []


class TestTextMeasuresItsOwnBacking:
    """Contrast should judge text against what it is actually drawn on."""

    def test_should_measure_a_chip_against_its_own_background_effect(self):
        """Given text on its own chip, when diagnosed, then contrast is not misread."""
        # Given: ink text on an amber chip over an ink canvas
        canvas = (
            Canvas(400, 160)
            .background(color="#0A0E12")
            .text(
                content="RUN 01 = RUN 02",
                font=FONT,
                size=20,
                color="#0A0E12",
                position=(40, 60),
                effects=[Background(color="#E8A552", padding=(14, 9), border_radius=2)],
            )
        )

        # When: the composition is diagnosed
        # Then: the chip is what the glyphs sit on, so contrast is fine
        assert codes(canvas, "low-contrast") == []

    def test_should_still_report_text_lost_against_the_layers_below_it(self):
        """Given text with no backing, when diagnosed, then low contrast is reported."""
        # Given: ink text directly on an ink canvas
        canvas = (
            Canvas(400, 160)
            .background(color="#0A0E12")
            .text(content="INVISIBLE", font=FONT, size=20, color="#0A0E12", position=(40, 60))
        )

        # When: the composition is diagnosed
        # Then: the rule still catches unreadable copy
        assert codes(canvas, "low-contrast") != []
