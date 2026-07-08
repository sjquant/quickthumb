import json

from PIL import Image


class TestLayerEffects:
    def test_should_publish_effect_models_in_json_schema(self):
        """Canvas JSON Schema exposes the layer effect discriminators"""
        from quickthumb import canvas_json_schema

        # given: the published schema generated from public Pydantic models
        schema = canvas_json_schema()

        # when: clients inspect the schema for effect model discriminators
        encoded = json.dumps(schema)

        # then: every layer effect is available for constrained JSON generation
        assert '"duotone"' in encoded
        assert '"inner_shadow"' in encoded
        assert '"backdrop_blur"' in encoded

    def test_should_round_trip_effect_models_through_json(self):
        """Duotone, inner shadow, and backdrop blur effects serialize through Canvas JSON"""
        from quickthumb import BackdropBlur, Canvas, Duotone, InnerShadow

        # given: public effect model instances attached to JSON-backed layers
        canvas = (
            Canvas(80, 60)
            .shape(
                shape="rectangle",
                position=(10, 10),
                width=40,
                height=30,
                color="#FFFFFF80",
                effects=[
                    InnerShadow(offset_x=3, offset_y=2, color="#00000099", blur_radius=4),
                    BackdropBlur(radius=5, opacity=0.75),
                ],
            )
            .image(
                path="fixture.png",
                position=(0, 0),
                width=20,
                height=20,
                effects=[Duotone(shadows="#111827", highlights="#FDE68A", opacity=0.5)],
            )
        )

        # when: the canvas is serialized and parsed back through the public JSON API
        serialized = canvas.to_json()
        restored = Canvas.from_json(serialized)

        # then: effect discriminators and validated fields survive unchanged
        assert json.loads(restored.to_json()) == json.loads(serialized)
        assert json.loads(serialized)["layers"] == [
            {
                "type": "shape",
                "shape": "rectangle",
                "position": [10, 10],
                "width": 40,
                "height": 30,
                "color": "#FFFFFF80",
                "border_radius": 0,
                "opacity": 1.0,
                "rotation": 0.0,
                "align": None,
                "points": None,
                "star_points": 5,
                "inner_radius": 0.5,
                "effects": [
                    {
                        "type": "inner_shadow",
                        "offset_x": 3,
                        "offset_y": 2,
                        "color": "#00000099",
                        "blur_radius": 4,
                        "opacity": 1.0,
                    },
                    {"type": "backdrop_blur", "radius": 5, "opacity": 0.75},
                ],
                "animation": None,
            },
            {
                "type": "image",
                "path": "fixture.png",
                "position": [0, 0],
                "width": 20,
                "height": 20,
                "opacity": 1.0,
                "rotation": 0.0,
                "remove_background": False,
                "align": "top-left",
                "border_radius": 0,
                "fit": None,
                "blend_mode": None,
                "effects": [
                    {
                        "type": "duotone",
                        "shadows": "#111827",
                        "highlights": "#FDE68A",
                        "opacity": 0.5,
                    }
                ],
                "animation": None,
            },
        ]

    def test_should_apply_duotone_to_image_pixels(self, tmp_path):
        """Duotone maps image luminance between shadow and highlight colors"""
        from quickthumb import Canvas, Duotone

        # given: a black-to-white image layer using red shadows and blue highlights
        source = tmp_path / "tone.png"
        Image.new("RGBA", (3, 1), (0, 0, 0, 0)).save(source)
        pixels = Image.open(source).convert("RGBA")
        pixels.putpixel((0, 0), (0, 0, 0, 255))
        pixels.putpixel((1, 0), (128, 128, 128, 255))
        pixels.putpixel((2, 0), (255, 255, 255, 255))
        pixels.save(source)
        output = tmp_path / "output.png"
        canvas = Canvas(3, 1).image(
            path=str(source),
            position=(0, 0),
            effects=[Duotone(shadows="#FF0000", highlights="#0000FF")],
        )

        # when: rendering the image
        canvas.render(str(output))

        # then: dark pixels use the shadow color and light pixels use the highlight color
        rendered = Image.open(output).convert("RGBA")
        assert rendered.getpixel((0, 0)) == (255, 0, 0, 255)
        assert rendered.getpixel((1, 0))[0] in range(126, 129)
        assert rendered.getpixel((1, 0))[2] in range(127, 130)
        assert rendered.getpixel((2, 0)) == (0, 0, 255, 255)

    def test_should_respect_duotone_opacity(self, tmp_path):
        """Duotone opacity controls whether and how strongly the mapping is applied"""
        from quickthumb import Canvas, Duotone

        # given: identical gray image layers with disabled, partial, and full duotone effects
        source = tmp_path / "gray.png"
        Image.new("RGBA", (1, 1), (128, 128, 128, 255)).save(source)
        outputs = {name: tmp_path / f"{name}.png" for name in ("disabled", "partial", "full")}

        # when: rendering each opacity variant
        Canvas(1, 1).image(
            path=str(source),
            position=(0, 0),
            effects=[Duotone(shadows="#FF0000", highlights="#0000FF", opacity=0.0)],
        ).render(str(outputs["disabled"]))
        Canvas(1, 1).image(
            path=str(source),
            position=(0, 0),
            effects=[Duotone(shadows="#FF0000", highlights="#0000FF", opacity=0.5)],
        ).render(str(outputs["partial"]))
        Canvas(1, 1).image(
            path=str(source),
            position=(0, 0),
            effects=[Duotone(shadows="#FF0000", highlights="#0000FF")],
        ).render(str(outputs["full"]))

        # then: disabled is original, partial is between original and full duotone
        disabled = Image.open(outputs["disabled"]).convert("RGBA").getpixel((0, 0))
        partial = Image.open(outputs["partial"]).convert("RGBA").getpixel((0, 0))
        full = Image.open(outputs["full"]).convert("RGBA").getpixel((0, 0))
        assert disabled == (128, 128, 128, 255)
        assert full != disabled
        assert min(disabled[1], full[1]) <= partial[1] <= max(disabled[1], full[1])
        assert min(disabled[2], full[2]) <= partial[2] <= max(disabled[2], full[2])

    def test_should_apply_duotone_before_drop_shadow(self, tmp_path):
        """Duotone recolors image content without tinting external shadows"""
        from quickthumb import Canvas, Duotone, Shadow

        # given: a white image with duotone and an offset black shadow
        source = tmp_path / "white.png"
        Image.new("RGBA", (5, 5), (255, 255, 255, 255)).save(source)
        output = tmp_path / "output.png"
        canvas = (
            Canvas(20, 10)
            .background(color="#FFFFFF")
            .image(
                path=str(source),
                position=(5, 2),
                effects=[
                    Duotone(shadows="#FF0000", highlights="#0000FF"),
                    Shadow(offset_x=6, offset_y=0, color="#000000", blur_radius=0),
                ],
            )
        )

        # when: rendering combined duotone and shadow effects
        canvas.render(str(output))

        # then: image pixels are duotoned while shadow-only pixels stay black
        rendered = Image.open(output).convert("RGBA")
        assert rendered.getpixel((7, 4))[:3] == (0, 0, 255)
        assert rendered.getpixel((12, 4))[:3] == (0, 0, 0)

    def test_should_apply_inner_shadow_inside_shape_alpha(self, tmp_path):
        """Inner shadow darkens the interior edge without expanding the layer bounds"""
        from quickthumb import Canvas, InnerShadow

        # given: a white rectangle with a hard inset shadow
        output = tmp_path / "output.png"
        canvas = (
            Canvas(60, 60)
            .background(color="#FFFFFF")
            .shape(
                shape="rectangle",
                position=(10, 10),
                width=40,
                height=40,
                color="#FFFFFF",
                effects=[InnerShadow(offset_x=6, offset_y=6, color="#000000", blur_radius=0)],
            )
        )

        # when: rendering the shape
        canvas.render(str(output))

        # then: the shadow is inside the shape and the measured bbox stays unchanged
        rendered = Image.open(output).convert("RGBA")
        assert rendered.getpixel((12, 12))[:3] == (0, 0, 0)
        assert rendered.getpixel((35, 35))[:3] == (255, 255, 255)
        inspection = canvas.inspect()
        assert inspection.layers[1].bbox is not None
        assert inspection.layers[1].bbox.model_dump() == {
            "x": 10,
            "y": 10,
            "width": 40,
            "height": 40,
        }

    def test_should_respect_inner_shadow_opacity(self, tmp_path):
        """Inner shadow opacity controls the inset darkening strength"""
        from quickthumb import Canvas, InnerShadow

        # given: three identical rectangles with disabled, partial, and full inner shadows
        outputs = {name: tmp_path / f"{name}.png" for name in ("disabled", "partial", "full")}

        # when: rendering each opacity variant
        for name, opacity in (("disabled", 0.0), ("partial", 0.5), ("full", 1.0)):
            (
                Canvas(20, 20)
                .background(color="#FFFFFF")
                .shape(
                    shape="rectangle",
                    position=(5, 5),
                    width=10,
                    height=10,
                    color="#FFFFFF",
                    effects=[
                        InnerShadow(
                            offset_x=3,
                            offset_y=3,
                            color="#000000",
                            blur_radius=0,
                            opacity=opacity,
                        )
                    ],
                )
            ).render(str(outputs[name]))

        # then: disabled remains white and partial darkening sits between disabled and full
        disabled = Image.open(outputs["disabled"]).convert("RGBA").getpixel((6, 6))[0]
        partial = Image.open(outputs["partial"]).convert("RGBA").getpixel((6, 6))[0]
        full = Image.open(outputs["full"]).convert("RGBA").getpixel((6, 6))[0]
        assert disabled == 255
        assert full < partial < disabled

    def test_should_blur_existing_backdrop_inside_shape_alpha(self, tmp_path):
        """Backdrop blur samples prior canvas pixels through the layer alpha"""
        from quickthumb import BackdropBlur, Canvas

        # given: equivalent frosted rectangles with and without backdrop blur
        control_output = tmp_path / "control.png"
        blur_output = tmp_path / "blur.png"
        base_canvas = (
            Canvas(80, 50)
            .shape(shape="rectangle", position=(0, 0), width=40, height=50, color="#FF0000")
            .shape(shape="rectangle", position=(40, 0), width=40, height=50, color="#0000FF")
        )
        no_blur = base_canvas.shape(
            shape="rectangle",
            position=(30, 5),
            width=20,
            height=40,
            color="#FFFFFF40",
        )
        with_blur = (
            Canvas(80, 50)
            .shape(shape="rectangle", position=(0, 0), width=40, height=50, color="#FF0000")
            .shape(shape="rectangle", position=(40, 0), width=40, height=50, color="#0000FF")
            .shape(
                shape="rectangle",
                position=(30, 5),
                width=20,
                height=40,
                color="#FFFFFF40",
                effects=[BackdropBlur(radius=5)],
            )
        )

        # when: rendering the boundary-crossing blur layer and its no-blur control
        no_blur.render(str(control_output))
        with_blur.render(str(blur_output))

        # then: blur materially increases blue from the neighboring backdrop
        control = Image.open(control_output).convert("RGBA").getpixel((36, 25))
        blurred = Image.open(blur_output).convert("RGBA").getpixel((36, 25))
        assert blurred[2] - control[2] >= 10
        assert control[0] - blurred[0] >= 10

    def test_should_respect_backdrop_blur_opacity(self, tmp_path):
        """Backdrop blur opacity controls how much blurred backdrop is composited"""
        from quickthumb import BackdropBlur, Canvas

        # given: disabled, partial, and full backdrop blur variants over a color boundary
        outputs = {name: tmp_path / f"{name}.png" for name in ("disabled", "partial", "full")}

        # when: rendering each opacity variant
        for name, opacity in (("disabled", 0.0), ("partial", 0.5), ("full", 1.0)):
            (
                Canvas(80, 50)
                .shape(shape="rectangle", position=(0, 0), width=40, height=50, color="#FF0000")
                .shape(shape="rectangle", position=(40, 0), width=40, height=50, color="#0000FF")
                .shape(
                    shape="rectangle",
                    position=(30, 5),
                    width=20,
                    height=40,
                    color="#FFFFFF40",
                    effects=[BackdropBlur(radius=5, opacity=opacity)],
                )
            ).render(str(outputs[name]))

        # then: partial blur sits between disabled and full blur at the boundary sample
        disabled = Image.open(outputs["disabled"]).convert("RGBA").getpixel((36, 25))[2]
        partial = Image.open(outputs["partial"]).convert("RGBA").getpixel((36, 25))[2]
        full = Image.open(outputs["full"]).convert("RGBA").getpixel((36, 25))[2]
        assert disabled < partial < full
