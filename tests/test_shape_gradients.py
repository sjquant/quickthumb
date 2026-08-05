"""Behavioral specifications for gradient fills and their stop coverage."""

import json

from quickthumb import Canvas, LinearGradient, RadialGradient

from tests._helpers import pixel_channel


def column(image, x):
    """Return the red channel down one column of a rendered frame."""
    rgb = image.convert("RGB")
    return [rgb.getpixel((x, y))[0] for y in range(rgb.height)]


class TestShapeGradientFills:
    """A shape should be able to carry a gradient, not only a flat colour."""

    def test_should_fill_a_shape_with_a_linear_gradient(self):
        """Given a gradient fill, when rendered, then the shape ramps across itself."""
        # Given: a black-to-white gradient filling the whole canvas
        canvas = Canvas(200, 200).shape(
            shape="rectangle",
            position=(0, 0),
            width=200,
            height=200,
            color="#FF0000",
            fill=LinearGradient(angle=90, stops=[("#000000", 0.0), ("#FFFFFF", 1.0)]),
        )

        # When: the shape is rendered
        values = column(canvas.render_frame(0.0), 100)

        # Then: it ramps from the first stop to the last, and the flat colour is unused
        assert values[0] <= 1
        assert values[-1] >= 254
        assert values == sorted(values)

    def test_should_fade_a_shape_out_through_a_transparent_stop(self):
        """Given a stop with alpha, when rendered, then the layer beneath shows through."""
        # Given: an ink panel over white that fades to nothing at its top edge
        canvas = (
            Canvas(200, 200)
            .background(color="#FFFFFF")
            .shape(
                shape="rectangle",
                position=(0, 0),
                width=200,
                height=200,
                color="#000000",
                fill=LinearGradient(angle=90, stops=[("#00000000", 0.0), ("#000000FF", 1.0)]),
            )
        )

        # When: the frame is sampled top to bottom
        values = column(canvas.render_frame(0.0), 100)

        # Then: the top is untouched white and the bottom is solid ink
        assert values[0] >= 254
        assert values[-1] <= 1

    def test_should_keep_the_flat_colour_as_the_declared_document_fallback(self):
        """Given a gradient fill, when serialized, then both it and the colour survive."""
        # Given: a shape carrying a gradient and a flat colour
        canvas = Canvas(100, 100).shape(
            shape="rectangle",
            position=(0, 0),
            width=100,
            height=100,
            color="#E8A552",
            fill=RadialGradient(stops=[("#000000", 0.0), ("#FFFFFF", 1.0)]),
        )

        # When: the composition round-trips through JSON
        payload = json.loads(canvas.to_json())["layers"][0]
        restored = json.loads(Canvas.from_json(canvas.to_json()).to_json())["layers"][0]

        # Then: the gradient is public and the flat colour is retained beside it
        assert payload["fill"]["type"] == "radial"
        assert payload["color"] == "#E8A552"
        assert restored == payload


class TestGradientStopCoverage:
    """A gradient's first and last stop have to reach the edges of its layer."""

    def test_should_span_the_whole_layer_whatever_its_aspect_ratio(self):
        """Given non-square layers, when filled, then both end stops still land."""
        # Given: the same vertical gradient on three different shapes
        sizes = ((400, 200), (200, 200), (1280, 720))

        for width, height in sizes:
            canvas = Canvas(width, height).background(
                gradient=LinearGradient(angle=90, stops=[("#000000", 0.0), ("#FFFFFF", 1.0)])
            )

            # When: the top and bottom rows are sampled
            values = column(canvas.render_frame(0.0), width // 2)

            # Then: neither end of the ramp is clipped away by the layer's shape
            assert values[0] <= 1, f"{width}x{height} starts at {values[0]}"
            assert values[-1] >= 254, f"{width}x{height} ends at {values[-1]}"

    def test_should_reach_the_last_stop_at_the_farthest_corner_of_a_radial_fill(self):
        """Given a radial gradient, when rendered, then its outer stop reaches the corner."""
        # Given: a centred black-to-white radial gradient
        canvas = Canvas(300, 300).background(
            gradient=RadialGradient(stops=[("#000000", 0.0), ("#FFFFFF", 1.0)])
        )

        # When: the centre and the farthest corner are sampled
        frame = canvas.render_frame(0.0).convert("RGB")

        # Then: the ramp covers the full distance rather than stopping short
        assert pixel_channel(frame, (150, 150), 0) <= 1
        assert pixel_channel(frame, (0, 0), 0) >= 254
