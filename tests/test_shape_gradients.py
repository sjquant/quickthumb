"""Behavioral specifications for gradient fills and their stop coverage."""

import json

from quickthumb import Canvas, LinearGradient, RadialGradient


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

        # Then: it ramps dark to light across the shape, and the flat colour is unused
        assert values == sorted(values)
        assert values[0] < 60
        assert values[-1] > 195
        assert max(values) - min(values) > 150

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

        # Then: the transparent end lets the white through and the opaque end inks over it
        assert values == sorted(values, reverse=True)
        assert values[0] > 195
        assert values[-1] < 60

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
