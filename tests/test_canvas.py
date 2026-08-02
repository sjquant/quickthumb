"""Tests for Canvas functionality"""

import json
import os
import tempfile
from typing import cast

import pytest
from inline_snapshot import snapshot
from quickthumb.models import BackgroundLayer, Stroke, TextLayer


class TestCanvas:
    """Test suite for Canvas operations"""

    def test_should_create_canvas_with_explicit_dimensions(self):
        """Test that Canvas can be created with explicit width and height dimensions"""
        # Given: User wants to create a canvas with specific pixel dimensions
        width = 1920
        height = 1080

        # When: User creates a Canvas with explicit dimensions
        from quickthumb import Canvas

        canvas = Canvas(width, height)

        # Then: Canvas should be created with correct dimensions
        assert canvas.width == 1920
        assert canvas.height == 1080

    def test_should_create_canvas_from_aspect_ratio(self):
        """Test that Canvas can be created from aspect ratio and calculates correct dimensions"""
        # Given: User wants to create a 16:9 canvas with base width 1920
        ratio = "16:9"
        base_width = 1920
        expected_height = 1080  # 1920 * 9 / 16

        # When: User creates Canvas from aspect ratio
        from quickthumb import Canvas

        canvas = Canvas.from_aspect_ratio(ratio, base_width=base_width)

        # Then: Canvas dimensions should be calculated correctly
        assert canvas.width == 1920
        assert canvas.height == expected_height

    def test_should_raise_error_for_invalid_dimensions(self):
        """Test that creating canvas with zero or negative dimensions raises ValueError"""
        # Given: User attempts to create canvas with invalid dimensions
        from quickthumb import Canvas, ValidationError

        # When: User calls Canvas with zero width
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match="width must be > 0"):
            Canvas(0, 1080)

        # When: User calls Canvas with negative height
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match="height must be > 0"):
            Canvas(1920, -100)

    def test_should_allow_replacing_the_layers_list(self):
        """canvas.layers can be assigned to replace or filter layers, as on a plain attribute"""
        from quickthumb import Canvas

        # given: a canvas with two layers
        canvas = Canvas(200, 200).background(color="#FFFFFF").text("hi", size=20)

        # when: the layer list is replaced with a filtered copy
        canvas.layers = [layer for layer in canvas.layers if isinstance(layer, BackgroundLayer)]

        # then
        assert len(canvas.layers) == 1
        assert cast(BackgroundLayer, canvas.layers[0]).type == "background"

    @pytest.mark.parametrize("attribute", ["width", "height"])
    def test_should_reject_non_positive_dimension_assignment(self, attribute):
        """Assigning a non-positive width/height raises like the constructor does"""
        from quickthumb import Canvas, ValidationError

        canvas = Canvas(200, 200)

        with pytest.raises(ValidationError, match=attribute):
            setattr(canvas, attribute, 0)

    def test_should_serialize_multiple_layers_in_order(self):
        """Test that multiple layers serialize in correct order"""
        # Given: Canvas with multiple background and text layers
        from quickthumb import Canvas, LinearGradient

        gradient = LinearGradient(angle=90, stops=[("#FF0000", 0.0), ("#0000FF", 1.0)])
        canvas = (
            Canvas(1920, 1080)
            .background(color="#2c3e50")
            .background(gradient=gradient, opacity=0.5)
            .text("Title", size=84, color="#FFFFFF")
            .text("Subtitle", size=48, color="#EEEEEE")
        )

        # When: User exports to JSON
        canvas_dict = json.loads(canvas.to_json())

        # Then: All layers should be serialized in correct order
        assert canvas_dict == snapshot(
            {
                "kind": "canvas",
                "width": 1920,
                "height": 1080,
                "layers": [
                    {
                        "type": "background",
                        "color": "#2c3e50",
                        "gradient": None,
                        "image": None,
                        "opacity": 1.0,
                        "blend_mode": None,
                        "fit": None,
                        "effects": [],
                    },
                    {
                        "type": "background",
                        "color": None,
                        "gradient": {
                            "type": "linear",
                            "angle": 90.0,
                            "stops": [["#FF0000", 0.0], ["#0000FF", 1.0]],
                        },
                        "image": None,
                        "opacity": 0.5,
                        "blend_mode": None,
                        "fit": None,
                        "effects": [],
                    },
                    {
                        "type": "text",
                        "content": "Title",
                        "value": None,
                        "font": None,
                        "font_source": "auto",
                        "font_variations": {},
                        "emoji_style": "monochrome",
                        "size": 84,
                        "color": "#FFFFFF",
                        "fill": None,
                        "position": None,
                        "align": None,
                        "bold": False,
                        "italic": False,
                        "weight": None,
                        "max_width": None,
                        "max_height": None,
                        "min_size": 1,
                        "balance_lines": False,
                        "effects": [],
                        "line_height": None,
                        "letter_spacing": None,
                        "auto_scale": False,
                        "rotation": 0.0,
                        "opacity": 1.0,
                        "animation": None,
                    },
                    {
                        "type": "text",
                        "content": "Subtitle",
                        "value": None,
                        "font": None,
                        "font_source": "auto",
                        "font_variations": {},
                        "emoji_style": "monochrome",
                        "size": 48,
                        "color": "#EEEEEE",
                        "fill": None,
                        "position": None,
                        "align": None,
                        "bold": False,
                        "italic": False,
                        "weight": None,
                        "max_width": None,
                        "max_height": None,
                        "min_size": 1,
                        "balance_lines": False,
                        "effects": [],
                        "line_height": None,
                        "letter_spacing": None,
                        "auto_scale": False,
                        "rotation": 0.0,
                        "opacity": 1.0,
                        "animation": None,
                    },
                ],
            }
        )

    def test_should_recreate_canvas_from_json(self):
        """Test that Canvas can be recreated from JSON"""
        # Given: Canvas with multiple background and text layers
        from quickthumb import Canvas, LinearGradient

        gradient = LinearGradient(angle=90, stops=[("#FF0000", 0.0), ("#0000FF", 1.0)])
        canvas = (
            Canvas(1920, 1080)
            .background(color="#2c3e50")
            .background(gradient=gradient, opacity=0.5)
            .text("Title", size=84, color="#FFFFFF")
            .text("Subtitle", size=48, color="#EEEEEE")
        )
        json_str = canvas.to_json()
        recreated = Canvas.from_json(json_str)
        assert recreated.to_json() == json_str

    @pytest.mark.parametrize(
        "json_str, match",
        [
            (
                '{"width": 1920, "height": 1080, "layers": "INVALID"}',
                "layers.*",
            ),
            (
                json.dumps(
                    {
                        "width": 100,
                        "height": 100,
                        "layers": [{"type": "custom", "name": "no_such_fn_xyz"}],
                    }
                ),
                "no_such_fn_xyz",
            ),
            ('{"kind": "canvas", "width": 100, "height": 100}', "layers"),
            (
                '{"kind": "canvas", "width": 100, "height": 100, "layerz": []}',
                "unknown field",
            ),
            (
                '{"kind": "canvas", "width": true, "height": 100, "layers": []}',
                "integer",
            ),
        ],
    )
    def test_should_raise_error_for_invalid_json(self, json_str, match):
        """Canvas.from_json raises ValidationError for malformed or unresolvable JSON"""
        from quickthumb import Canvas, ValidationError

        with pytest.raises(ValidationError, match=match):
            Canvas.from_json(json_str)

    def test_should_base64_match_rendered_file(self):
        """Test that to_base64 output is identical to base64-encoding the rendered file"""
        import base64

        from quickthumb import Canvas

        canvas = Canvas(100, 100).background(color="#FF0000")
        result = canvas.to_base64()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)
            with open(output_path, "rb") as f:
                assert result == base64.b64encode(f.read()).decode("utf-8")

    @pytest.mark.parametrize(
        "fmt, prefix",
        [
            ("PNG", "data:image/png;base64,"),
            ("JPEG", "data:image/jpeg;base64,"),
            ("WEBP", "data:image/webp;base64,"),
        ],
    )
    def test_should_prefix_data_url_with_correct_mime_type(self, fmt, prefix):
        """Test that to_data_url returns the correct MIME type prefix for each format"""
        from quickthumb import Canvas

        canvas = Canvas(100, 100).background(color="#FF0000")
        assert canvas.to_data_url(format=fmt).startswith(prefix)

    def test_should_raise_error_for_quality_with_png_in_to_base64(self):
        """Test that to_base64 raises error when quality is used with PNG format"""
        # Given: A simple canvas
        from quickthumb import Canvas
        from quickthumb.errors import RenderingError

        canvas = Canvas(100, 100).background(color="#FF0000")

        # When: User calls to_base64 with quality parameter for PNG
        # Then: Should raise RenderingError
        with pytest.raises(
            RenderingError, match="Quality parameter is only supported for JPEG and WEBP"
        ):
            canvas.to_base64(format="PNG", quality=80)

    def test_render_with_explicit_format_overrides_extension(self):
        """Test that render() format param overrides extension-based format detection"""

        from PIL import Image
        from quickthumb import Canvas

        canvas = Canvas(100, 100).background(color="#FF0000")

        with tempfile.TemporaryDirectory() as tmpdir:
            # .png extension but explicit JPEG format — JPEG should win
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path, format="JPEG")

            img = Image.open(output_path)
            assert img.format == "JPEG"

    def test_should_reject_serializing_unnamed_custom_layer(self):
        """to_json() raises ValidationError for unnamed custom layers"""
        from quickthumb import Canvas, ValidationError

        canvas = Canvas(100, 100).background(color="#FFFFFF").custom(lambda image: image)

        with pytest.raises(ValidationError, match="Custom layers cannot be serialized"):
            canvas.to_json()

    def test_should_reject_serializing_custom_layer_with_non_serializable_kwargs(self):
        """to_json() raises ValidationError when custom layer kwargs are not JSON-serializable"""
        from quickthumb import Canvas, ValidationError

        canvas = (
            Canvas(100, 100)
            .background(color="#FFFFFF")
            .custom(lambda image: image, name="fn", kwargs={"obj": object()})
        )

        with pytest.raises(ValidationError, match="kwargs.*not JSON-serializable"):
            canvas.to_json()

    def test_should_round_trip_named_custom_layer(self):
        """Named custom layers serialize to JSON and deserialize back via the registry"""

        from inline_snapshot import snapshot
        from PIL import Image
        from quickthumb import Canvas

        calls: list[dict] = []

        def draw_dot(image: Image.Image, *, color: str = "red", size: int = 10) -> None:
            calls.append({"color": color, "size": size})

        Canvas.register_layer_fn("draw_dot", draw_dot)
        try:
            canvas = (
                Canvas(100, 100)
                .background(color="#FFFFFF")
                .custom(draw_dot, name="draw_dot")
                .custom(draw_dot, name="draw_dot", kwargs={"color": "blue", "size": 20})
            )

            json_str = canvas.to_json()
            assert json.loads(json_str) == snapshot(
                {
                    "kind": "canvas",
                    "width": 100,
                    "height": 100,
                    "layers": [
                        {
                            "type": "background",
                            "color": "#FFFFFF",
                            "gradient": None,
                            "image": None,
                            "opacity": 1.0,
                            "blend_mode": None,
                            "fit": None,
                            "effects": [],
                        },
                        {"type": "custom", "name": "draw_dot", "kwargs": {}},
                        {
                            "type": "custom",
                            "name": "draw_dot",
                            "kwargs": {"color": "blue", "size": 20},
                        },
                    ],
                }
            )

            recreated = Canvas.from_json(json_str)
            with tempfile.TemporaryDirectory() as tmpdir:
                recreated.render(os.path.join(tmpdir, "out.png"))
            assert calls == [{"color": "red", "size": 10}, {"color": "blue", "size": 20}]
        finally:
            Canvas.unregister_layer_fn("draw_dot")

    def test_should_raise_error_deserializing_unregistered_custom_layer(self):
        """Deserializing a custom layer whose name is not in the registry raises ValidationError"""
        from quickthumb import Canvas, ValidationError

        json_str = json.dumps(
            {
                "width": 100,
                "height": 100,
                "layers": [{"type": "custom", "name": "no_such_fn_xyz"}],
            }
        )
        with pytest.raises(ValidationError, match="no_such_fn_xyz"):
            Canvas.from_json(json_str)

    def test_should_raise_rendering_error_when_custom_callback_fails(self):
        """Exceptions inside custom callback should be wrapped as RenderingError"""

        from quickthumb import Canvas
        from quickthumb.errors import RenderingError

        def bad_custom(_image):
            raise RuntimeError("boom")

        canvas = Canvas(100, 100).background(color="#FFFFFF").custom(bad_custom)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            with pytest.raises(RenderingError, match="Custom layer callback failed: boom"):
                canvas.render(output_path)

    def test_should_raise_error_when_custom_callback_returns_non_image(self):
        """custom callback should return PIL.Image.Image or None"""

        from quickthumb import Canvas
        from quickthumb.errors import RenderingError

        canvas = Canvas(100, 100).background(color="#FFFFFF").custom(lambda _image: "not-image")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            with pytest.raises(
                RenderingError, match="Custom layer callback must return PIL.Image.Image or None"
            ):
                canvas.render(output_path)

    def test_should_raise_error_when_custom_callback_returns_different_size(self):
        """custom callback should preserve canvas dimensions when returning an image"""

        from PIL import Image
        from quickthumb import Canvas
        from quickthumb.errors import RenderingError

        canvas = (
            Canvas(100, 100)
            .background(color="#FFFFFF")
            .custom(lambda _image: Image.new("RGBA", (10, 10), (0, 0, 0, 0)))
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            with pytest.raises(
                RenderingError,
                match="Custom layer callback returned an image with different size",
            ):
                canvas.render(output_path)


class TestCanvasTemplate:
    """Tests for Canvas.from_template(), register_template(), and unregister_template()"""

    SIMPLE_TEMPLATE = json.dumps(
        {
            "width": 100,
            "height": 100,
            "layers": [{"type": "background", "color": "$bg_color"}],
        }
    )

    @pytest.mark.parametrize(
        "placeholder, key",
        [("$bg_color", "bg_color"), ("${bg_color}", "bg_color")],
    )
    def test_should_substitute_var_placeholders(self, placeholder, key):
        """from_template substitutes both $var and ${var} placeholders in inline JSON strings"""
        # Given: A JSON string template with a placeholder and a matching variable
        from quickthumb import Canvas

        template = json.dumps(
            {
                "width": 100,
                "height": 100,
                "layers": [{"type": "background", "color": placeholder}],
            }
        )

        # When: User calls Canvas.from_template with variables
        canvas = Canvas.from_template(template, variables={key: "#FF0000"})

        # Then: The layer has the substituted color value in its JSON representation
        assert json.loads(canvas.to_json()) == snapshot(
            {
                "kind": "canvas",
                "width": 100,
                "height": 100,
                "layers": [
                    {
                        "type": "background",
                        "color": "#FF0000",
                        "gradient": None,
                        "image": None,
                        "opacity": 1.0,
                        "blend_mode": None,
                        "fit": None,
                        "effects": [],
                    }
                ],
            }
        )

    def test_should_load_template_from_file_path(self):
        """from_template accepts a file path to a .json template file"""
        # Given: A template file on disk
        from quickthumb import Canvas

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write(self.SIMPLE_TEMPLATE)
            template_path = f.name

        try:
            # When: User calls Canvas.from_template with the file path
            canvas = Canvas.from_template(template_path, variables={"bg_color": "#123456"})

            # Then: Canvas is created correctly
            assert canvas.width == 100
            assert canvas.height == 100
        finally:
            os.unlink(template_path)

    def test_should_load_builtin_template_by_name(self):
        """from_template loads a built-in template by its name (e.g. 'youtube-16x9')"""
        # Given: The built-in 'youtube-16x9' template name
        from quickthumb import Canvas

        # When: User calls Canvas.from_template with a built-in name and its required variables
        canvas = Canvas.from_template("youtube-16x9", variables={"title": "Hello World"})

        # Then: Canvas has the correct dimensions for that template (1280x720)
        assert canvas.width == 1280
        assert canvas.height == 720

    def test_should_allow_registering_and_using_custom_template(self):
        """register_template allows using a custom template by name"""
        # Given: A custom template registered under a unique name
        from quickthumb import Canvas

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write(self.SIMPLE_TEMPLATE)
            template_path = f.name

        try:
            Canvas.register_template("my-custom-tpl", template_path)

            # When: User calls Canvas.from_template with the registered name
            canvas = Canvas.from_template("my-custom-tpl", variables={"bg_color": "#ABCDEF"})

            # Then: Canvas is created from the registered template
            assert canvas.width == 100
            assert canvas.height == 100
        finally:
            Canvas.unregister_template("my-custom-tpl")
            os.unlink(template_path)

    def test_user_registered_template_overrides_builtin(self):
        """A user-registered template with the same name as a built-in takes precedence"""
        # Given: A custom template registered under the built-in name 'youtube-16x9'
        from quickthumb import Canvas

        custom_spec = json.dumps(
            {"width": 999, "height": 111, "layers": [{"type": "background", "color": "#000000"}]}
        )
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write(custom_spec)
            template_path = f.name

        try:
            Canvas.register_template("youtube-16x9", template_path)

            # When: User calls from_template with 'youtube-16x9'
            canvas = Canvas.from_template("youtube-16x9")

            # Then: The user-registered template is used (999x111), not the built-in (1280x720)
            assert canvas.width == 999
            assert canvas.height == 111
        finally:
            Canvas.unregister_template("youtube-16x9")
            os.unlink(template_path)

    def test_should_remove_template_on_unregister(self):
        """unregister_template removes a registered template so it can no longer be used"""
        # Given: A custom template is registered then unregistered
        from quickthumb import Canvas, ValidationError

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write(self.SIMPLE_TEMPLATE)
            template_path = f.name

        try:
            Canvas.register_template("ephemeral-tpl", template_path)
            Canvas.unregister_template("ephemeral-tpl")

            # When: User tries to use it
            # Then: ValidationError is raised
            with pytest.raises(ValidationError, match="ephemeral-tpl"):
                Canvas.from_template("ephemeral-tpl")
        finally:
            os.unlink(template_path)

    def test_should_substitute_multiple_placeholders(self):
        """from_template substitutes all placeholders when a template has more than one"""
        # Given: A template with multiple distinct placeholders
        from quickthumb import Canvas

        template = json.dumps(
            {
                "width": 100,
                "height": 100,
                "layers": [
                    {"type": "background", "color": "$bg_color"},
                    {"type": "text", "content": "$title", "size": 48, "color": "#FFFFFF"},
                ],
            }
        )

        # When: Both variables are provided
        canvas = Canvas.from_template(template, variables={"bg_color": "#112233", "title": "Hello"})

        # Then: Canvas round-trips with both substitutions applied
        canvas_dict = json.loads(canvas.to_json())
        assert canvas_dict["layers"][0]["color"] == "#112233"
        assert canvas_dict["layers"][1]["content"] == "Hello"

    def test_should_substitute_non_string_variable_values_verbatim(self):
        """Numeric variables fill unquoted placeholders without corruption"""
        from quickthumb import Canvas

        # given: a template using $w as a bare JSON number and $title inside a string
        template = '{"width": $w, "height": 300, "layers": [{"type": "text", "content": "$title"}]}'

        # when
        canvas = Canvas.from_template(template, variables={"w": 400, "title": 42})

        # then: the int survives as a number and stringifies inside the quoted field
        assert canvas.width == 400
        assert cast(TextLayer, canvas.layers[0]).content == "42"

    def test_variable_value_with_dollar_sign_is_not_resubstituted(self):
        """Variable values containing $ are inserted literally, not re-scanned for placeholders"""
        from quickthumb import Canvas

        template = json.dumps(
            {
                "width": 100,
                "height": 100,
                "layers": [{"type": "text", "content": "$title", "size": 48, "color": "#FFFFFF"}],
            }
        )
        canvas = Canvas.from_template(template, variables={"title": "$100 Deal"})
        assert json.loads(canvas.to_json())["layers"][0]["content"] == "$100 Deal"

    def test_variable_value_with_special_json_chars_is_json_escaped(self):
        """Variable values with quotes or backslashes are JSON-escaped, not passed raw"""
        from quickthumb import Canvas

        template = json.dumps(
            {
                "width": 100,
                "height": 100,
                "layers": [{"type": "text", "content": "$title", "size": 48, "color": "#FFFFFF"}],
            }
        )
        canvas = Canvas.from_template(template, variables={"title": 'My "awesome" video'})
        assert json.loads(canvas.to_json())["layers"][0]["content"] == 'My "awesome" video'

    @pytest.mark.parametrize(
        "spec_or_path, variables, match",
        [
            # Unresolved placeholder raises ValidationError
            (
                json.dumps(
                    {
                        "width": 100,
                        "height": 100,
                        "layers": [{"type": "background", "color": "$missing_var"}],
                    }
                ),
                {},
                "missing_var",
            ),
            # Unknown template name raises ValidationError
            (
                "no-such-template-xyz",
                {},
                "no-such-template-xyz",
            ),
        ],
    )
    def test_should_raise_validation_error_for_invalid_template(
        self, spec_or_path, variables, match
    ):
        """from_template raises ValidationError for unresolved placeholders or unknown names"""
        from quickthumb import Canvas, ValidationError

        with pytest.raises(ValidationError, match=match):
            Canvas.from_template(spec_or_path, variables=variables)


class TestCanvasTheme:
    """Test suite for theme token resolution in JSON specs"""

    def test_should_resolve_theme_tokens_with_native_types(self):
        """from_json replaces whole-string $theme.* references with token values, preserving type"""
        from quickthumb import Canvas

        # given: a theme referenced from top-level fields, a nested effect, and a list-typed field
        config = json.dumps(
            {
                "width": 320,
                "height": 200,
                "theme": {
                    "colors": {"primary": "#FF0000", "ink": "#111111"},
                    "sizes": {"title": 48},
                    "layout": {"title_pos": ["8%", "50%"]},
                },
                "layers": [
                    {"type": "background", "color": "$theme.colors.primary"},
                    {
                        "type": "text",
                        "content": "Hi",
                        "size": "$theme.sizes.title",
                        "color": "$theme.colors.primary",
                        "position": "$theme.layout.title_pos",
                        "effects": [{"type": "stroke", "width": 2, "color": "$theme.colors.ink"}],
                    },
                ],
            }
        )

        # when: the spec is deserialized
        canvas = Canvas.from_json(config)

        # then: tokens are resolved with their native JSON types, including nested structures
        background = cast(BackgroundLayer, canvas.layers[0])
        text = cast(TextLayer, canvas.layers[1])
        assert background.color == "#FF0000"
        assert text.size == 48
        assert text.color == "#FF0000"
        assert text.position == ("8%", "50%")
        assert cast(Stroke, text.effects[0]).color == "#111111"

    def test_should_substitute_theme_tokens_embedded_in_strings(self):
        """Scalar theme tokens referenced inside a longer string are substituted in place"""
        from quickthumb import Canvas

        # given: a text layer embedding a string token mid-sentence
        config = json.dumps(
            {
                "width": 320,
                "height": 200,
                "theme": {"brand": {"name": "quickthumb"}},
                "layers": [
                    {"type": "text", "content": "Made with $theme.brand.name today"},
                ],
            }
        )

        # when
        canvas = Canvas.from_json(config)

        # then: the token is replaced inside the surrounding text
        assert cast(TextLayer, canvas.layers[0]).content == "Made with quickthumb today"

    @pytest.mark.parametrize(
        "theme,match",
        [
            # token missing from an existing theme block
            ({"colors": {"primary": "#FF0000"}}, "colors.accent"),
            # no theme block in the spec at all
            (None, "colors.accent"),
        ],
    )
    def test_should_raise_validation_error_for_unknown_theme_token(self, theme, match):
        """Referencing an undefined token raises ValidationError, with or without a theme block"""
        from quickthumb import Canvas, ValidationError

        # given: a spec referencing a token that no theme defines
        spec = {
            "width": 320,
            "height": 200,
            "layers": [{"type": "background", "color": "$theme.colors.accent"}],
        }
        if theme is not None:
            spec["theme"] = theme

        # when / then: deserialization fails naming the unknown token
        with pytest.raises(ValidationError, match=match):
            Canvas.from_json(json.dumps(spec))

    def test_should_resolve_theme_tokens_that_alias_other_tokens(self):
        """A theme value may reference another theme token and resolves to the final value"""
        from quickthumb import Canvas

        # given: accent aliases primary
        config = json.dumps(
            {
                "width": 320,
                "height": 200,
                "theme": {"colors": {"primary": "#FF0000", "accent": "$theme.colors.primary"}},
                "layers": [{"type": "background", "color": "$theme.colors.accent"}],
            }
        )

        # when
        canvas = Canvas.from_json(config)

        # then
        assert cast(BackgroundLayer, canvas.layers[0]).color == "#FF0000"

    def test_should_raise_for_circular_theme_token_references(self):
        """Mutually referencing theme tokens fail with a circular-reference error"""
        from quickthumb import Canvas, ValidationError

        config = json.dumps(
            {
                "width": 320,
                "height": 200,
                "theme": {"colors": {"a": "$theme.colors.b", "b": "$theme.colors.a"}},
                "layers": [{"type": "background", "color": "$theme.colors.a"}],
            }
        )

        with pytest.raises(ValidationError, match="circular"):
            Canvas.from_json(config)

    def test_should_serialize_resolved_values_without_theme_references(self):
        """to_json emits resolved token values and no theme block"""
        from quickthumb import Canvas

        # given: a canvas built from a themed spec
        config = json.dumps(
            {
                "width": 320,
                "height": 200,
                "theme": {"colors": {"bg": "#112233"}},
                "layers": [{"type": "background", "color": "$theme.colors.bg"}],
            }
        )
        canvas = Canvas.from_json(config)

        # when: it is serialized back to JSON
        serialized = json.loads(canvas.to_json())

        # then: the layer carries the resolved value and the theme block is not re-emitted
        assert serialized["layers"][0]["color"] == "#112233"
        assert "theme" not in serialized

    def test_should_resolve_template_variables_and_theme_tokens_together(self):
        """from_template resolves $var placeholders while leaving $theme.* tokens to the theme"""
        from quickthumb import Canvas

        # given: a template mixing a $title variable and a $theme color token
        template = json.dumps(
            {
                "width": 320,
                "height": 200,
                "theme": {"colors": {"primary": "#00FF00"}},
                "layers": [
                    {
                        "type": "text",
                        "content": "$title",
                        "color": "$theme.colors.primary",
                    }
                ],
            }
        )

        # when: rendered through the template path with variables
        canvas = Canvas.from_template(template, variables={"title": "Hello"})

        # then: both substitution systems applied
        text = cast(TextLayer, canvas.layers[0])
        assert text.content == "Hello"
        assert text.color == "#00FF00"
