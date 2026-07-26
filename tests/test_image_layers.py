"""Tests for image layer functionality"""

import builtins
import json
import sys
from typing import cast
from unittest.mock import patch

import pytest
from inline_snapshot import snapshot
from PIL import Image
from quickthumb.errors import ValidationError
from quickthumb.models import (
    Align,
    AnimationSpec,
    BackgroundLayer,
    BlendMode,
    FaceRegion,
    FitMode,
    ImageLayer,
    TextLayer,
)

from tests._helpers import pixel_rgb


class TestImageLayers:
    """Test suite for image layer operations"""

    @pytest.mark.parametrize(
        "opacity,error_pattern",
        [
            (1.5, "opacity.*0.0.*1.0"),
            (-0.5, "opacity.*0.0.*1.0"),
            (2.0, "opacity.*0.0.*1.0"),
        ],
    )
    def test_should_reject_invalid_opacity(self, opacity, error_pattern):
        """Test that opacity outside 0-1 range raises ValidationError with proper message"""
        # Given: Canvas and invalid opacity value
        from quickthumb import Canvas

        canvas = Canvas(1920, 1080)

        # When/Then: Creating image with invalid opacity should fail with error message
        with pytest.raises(ValidationError, match=error_pattern):
            canvas.image(path="assets/logo.png", position=(0, 0), opacity=opacity)

    @pytest.mark.parametrize(
        "width,height,error_pattern",
        [
            (-100, None, "width.*greater than 0"),
            (None, -100, "height.*greater than 0"),
            (0, None, "width.*greater than 0"),
            (None, 0, "height.*greater than 0"),
        ],
    )
    def test_should_reject_invalid_dimensions(self, width, height, error_pattern):
        """Test that invalid width/height raise ValidationError with proper message"""
        # Given: Canvas and invalid dimensions
        from quickthumb import Canvas

        canvas = Canvas(1920, 1080)

        # When/Then: Creating image with invalid dimensions should fail with error message
        with pytest.raises(ValidationError, match=error_pattern):
            canvas.image(path="assets/logo.png", position=(0, 0), width=width, height=height)

    @pytest.mark.parametrize(
        "position,error_pattern",
        [
            ((100,), "position.*must.*tuple.*two"),
            ((100, 200, 300), "position.*must.*tuple.*two"),
            (("50", "50"), "invalid percentage"),
            (("ab10%", "cd20%"), "invalid percentage"),
        ],
    )
    def test_should_reject_invalid_position(self, position, error_pattern):
        """Test that invalid position format raises ValidationError with proper message"""
        # Given: Canvas and invalid position
        from quickthumb import Canvas

        canvas = Canvas(1920, 1080)

        # When/Then: Creating image with invalid position should fail with error message
        with pytest.raises(ValidationError, match=error_pattern):
            canvas.image(path="assets/logo.png", position=position)

    @pytest.mark.parametrize(
        "align,error_pattern",
        [
            (("invalid", "top"), "invalid.*align"),
            (("left", "invalid"), "invalid.*align"),
            (("left",), "align must be a tuple of two elements"),
            (("left", "top", "extra"), "align must be a tuple of two elements"),
            # Old VH order ("top", "left") is now rejected: "top" is not a valid horizontal
            (("top", "left"), "invalid.*align"),
        ],
    )
    def test_should_reject_invalid_align(self, align, error_pattern):
        """Test that invalid align values raise ValidationError with proper message"""
        # Given: Canvas and invalid align
        from quickthumb import Canvas

        canvas = Canvas(1920, 1080)

        # When/Then: Creating image with invalid align should fail with error message
        with pytest.raises(ValidationError, match=error_pattern):
            canvas.image(path="assets/logo.png", position=(0, 0), align=align)

    @pytest.mark.parametrize("fit", ["invalid", "crop", "scale"])
    def test_should_reject_invalid_fit_mode(self, fit):
        """Test that unsupported image fit mode raises ValidationError"""
        from quickthumb import Canvas

        canvas = Canvas(1920, 1080)

        with pytest.raises(ValidationError, match="fit.*cover.*contain.*fill"):
            canvas.image(path="assets/logo.png", position=(0, 0), width=300, height=200, fit=fit)

    def test_should_reject_invalid_focal_point(self):
        """Image focal points must be normalized source-image coordinates"""
        # Given: Canvas and an out-of-bounds focal point
        from quickthumb import Canvas

        canvas = Canvas(1920, 1080)

        # When/Then: Creating image with invalid focal point should fail validation
        with pytest.raises(ValidationError, match="focal_point"):
            canvas.image(
                path="assets/logo.png",
                position=(0, 0),
                width=300,
                height=200,
                fit="cover",
                focal_point=(1.2, 0.5),
            )

    def test_should_reject_face_region_outside_image_bounds(self):
        """Face regions must fit inside normalized source-image bounds"""
        # Given: Canvas and a face box extending beyond the image
        from quickthumb import Canvas

        canvas = Canvas(1920, 1080)

        # When/Then: Creating image with invalid face metadata should fail validation
        with pytest.raises(ValidationError, match="face region.*bounds"):
            canvas.image(
                path="assets/logo.png",
                position=(0, 0),
                width=300,
                height=200,
                fit="cover",
                faces=[{"x": 0.9, "y": 0.2, "width": 0.2, "height": 0.3}],
            )

    @pytest.mark.parametrize(
        "face",
        [
            {"x": 0.0, "y": 0.2, "width": 1.1, "height": 0.3},
            {"x": 0.2, "y": 0.0, "width": 0.3, "height": 1.1},
        ],
    )
    def test_should_reject_face_region_dimensions_larger_than_source(self, face):
        """Face region dimensions must be normalized to the source-image bounds"""
        # Given: A canvas and a face box wider or taller than the source image
        from quickthumb import Canvas

        canvas = Canvas(1920, 1080)

        # When: Creating an image layer with oversize face metadata
        # Then: Validation rejects the invalid normalized dimension
        with pytest.raises(ValidationError, match="less than or equal to 1"):
            canvas.image(
                path="assets/logo.png",
                position=(0, 0),
                width=300,
                height=200,
                fit="cover",
                faces=[face],
            )

    @pytest.mark.parametrize("blend_mode", ["invalid", "soft-light", "difference"])
    def test_should_reject_invalid_blend_mode(self, blend_mode):
        """Test that unsupported image blend mode raises ValidationError"""
        from quickthumb import Canvas

        canvas = Canvas(1920, 1080)

        with pytest.raises(
            ValidationError,
            match="blend_mode.*multiply.*overlay.*screen.*darken.*lighten.*normal",
        ):
            canvas.image(path="assets/logo.png", position=(0, 0), blend_mode=blend_mode)


class TestCanvasImageAPI:
    """Test suite for Canvas.image() method"""

    def test_should_add_image_layer_to_canvas(self):
        """Test that Canvas.image() adds an image layer and supports method chaining"""
        from quickthumb import Canvas

        # Given: A canvas
        canvas = Canvas(1920, 1080)

        # When: Adding an image layer with fit mode in a target box
        result = canvas.image(
            path="assets/logo.png",
            position=(50, 50),
            width=400,
            height=300,
            fit="cover",
            blend_mode="multiply",
        )

        # Then: Should return self for method chaining and add correct layer
        assert result is canvas
        expected_layer = ImageLayer(
            type="image",
            path="assets/logo.png",
            position=(50, 50),
            width=400,
            height=300,
            opacity=1.0,
            rotation=0.0,
            align=Align.TOP_LEFT,
            fit=FitMode.COVER,
            blend_mode=BlendMode.MULTIPLY,
        )
        assert len(canvas.layers) == 1
        assert canvas.layers[0] == expected_layer

    def test_should_add_image_layer_with_fit_intelligence_to_canvas(self):
        """Canvas.image() stores focal point and face regions on the public layer model"""
        from quickthumb import Canvas

        # Given: A canvas and normalized fit metadata
        canvas = Canvas(1920, 1080)
        face = FaceRegion(x=0.1, y=0.2, width=0.25, height=0.3)

        # When: Adding an image layer with focal and face-aware cover metadata
        result = canvas.image(
            path="assets/logo.png",
            position=(50, 50),
            width=400,
            height=300,
            fit="cover",
            focal_point=(0.75, 0.25),
            faces=[face],
        )

        # Then: The layer should retain normalized crop metadata
        assert result is canvas
        image_layer = cast(ImageLayer, canvas.layers[0])
        assert image_layer.focal_point == (0.75, 0.25)
        assert image_layer.faces == [face]


class TestImageLayerBackgroundRemoval:
    """Test suite for image layer background removal"""

    def test_should_raise_import_error_when_rembg_not_installed(self, tmp_path):
        """Test that ImportError with helpful message is raised when rembg is missing"""
        from quickthumb import Canvas

        # Given: an image layer requesting background removal while rembg is not installed
        fixture = tmp_path / "subject.png"
        Image.new("RGBA", (100, 100), (255, 0, 0, 255)).save(fixture)
        canvas = Canvas(200, 200).image(path=str(fixture), position=(0, 0), remove_background=True)

        # When/Then: rendering should raise ImportError
        # Mock is justified here: impossible to test "library not installed" with real code
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "rembg":
                raise ImportError("No module named 'rembg'")
            return original_import(name, *args, **kwargs)

        saved = sys.modules.pop("rembg", None)
        try:
            with (
                patch.object(builtins, "__import__", side_effect=mock_import),
                pytest.raises(ImportError, match="rembg is required.*pip install quickthumb"),
            ):
                canvas.render(str(tmp_path / "out.png"))
        finally:
            if saved is not None:
                sys.modules["rembg"] = saved


class TestImageLayerComposition:
    """Test suite for image layer clipping and masking"""

    def test_should_clip_image_layer_pixels_to_rect(self, tmp_path):
        """Image clip removes pixels outside the configured canvas-space rectangle"""
        from quickthumb import Canvas

        # Given: a red image covering the canvas and a clip over its left half
        source = tmp_path / "red.png"
        output = tmp_path / "out.png"
        Image.new("RGBA", (80, 40), (255, 0, 0, 255)).save(source)
        canvas = (
            Canvas(80, 40)
            .background(color="#0000FF")
            .image(
                path=str(source),
                position=(0, 0),
                clip={"position": (0, 0), "width": 40, "height": 40},
            )
        )

        # When: rendering the clipped image
        canvas.render(str(output))

        # Then: pixels inside the clip show the image and pixels outside show the backdrop
        rendered = Image.open(output).convert("RGBA")
        assert rendered.getpixel((20, 20)) == (255, 0, 0, 255)
        assert rendered.getpixel((60, 20)) == (0, 0, 255, 255)

    def test_should_round_trip_image_layer_composition_through_json(self):
        """Image layer clip and mask primitives survive JSON round-trip"""
        from quickthumb import Canvas, LayerClip, LayerMask

        # Given: an image layer with both composition primitives
        canvas = Canvas(80, 40).image(
            path="logo.png",
            position=(0, 0),
            clip=LayerClip(position=(0, 0), width=40, height=40),
            mask=LayerMask(shape="ellipse", position=(20, 0), width=40, height=40),
        )

        # When: serializing and restoring the spec
        data = json.loads(canvas.to_json())
        restored = Canvas.from_json(canvas.to_json())

        # Then: unset specs stay concise and set composition fields are preserved
        assert data["layers"][0]["clip"]["position"] == [0, 0]
        assert data["layers"][0]["mask"]["shape"] == "ellipse"
        assert restored.layers[0] == canvas.layers[0]


class TestImageFitIntelligence:
    """Test suite for focal-point and face-aware cover rendering"""

    def test_should_render_center_and_focal_point_cover_crops_for_background_and_image_layers(
        self, tmp_path
    ):
        """Backgrounds and image layers fall back to center and honor focal points"""
        from quickthumb import Canvas

        source_path = tmp_path / "bands.png"
        center_output = tmp_path / "center.png"
        focal_output = tmp_path / "focal.png"
        image_output = tmp_path / "image-layer.png"

        # Given: A wide source image with distinct left, center, and right regions
        source = Image.new("RGBA", (300, 100), "#DC2626")
        source.paste(Image.new("RGBA", (100, 100), "#16A34A"), (100, 0))
        source.paste(Image.new("RGBA", (100, 100), "#2563EB"), (200, 0))
        source.save(source_path)

        # When: Rendering default and right-focused backgrounds plus a right-focused image layer
        Canvas(100, 100).background(image=str(source_path), fit="cover").render(center_output)
        Canvas(100, 100).background(
            image=str(source_path),
            fit="cover",
            focal_point=(1.0, 0.5),
        ).render(focal_output)
        (
            Canvas(120, 100)
            .background(color="#000000")
            .image(
                path=str(source_path),
                position=(10, 0),
                width=100,
                height=100,
                fit="cover",
                focal_point=(1.0, 0.5),
            )
            .render(image_output)
        )

        # Then: The default crop is centered and both focal crops keep the right region
        center_render = Image.open(center_output).convert("RGBA")
        focal_render = Image.open(focal_output).convert("RGBA")
        image_render = Image.open(image_output).convert("RGBA")
        assert pixel_rgb(center_render, (50, 50)) == (22, 163, 74)
        assert pixel_rgb(focal_render, (50, 50)) == (37, 99, 235)
        assert pixel_rgb(image_render, (60, 50)) == (37, 99, 235)

    def test_should_render_face_aware_cover_crop_and_fallback_for_background_and_image_layers(
        self, tmp_path
    ):
        """Backgrounds and image layers use face regions and fall back without them"""
        from quickthumb import Canvas

        source_path = tmp_path / "vertical-bands.png"
        face_output = tmp_path / "face.png"
        fallback_output = tmp_path / "fallback.png"
        image_face_output = tmp_path / "image-face.png"
        image_fallback_output = tmp_path / "image-fallback.png"

        # Given: A tall source image with face metadata near the top and focal point at bottom
        source = Image.new("RGBA", (100, 300), "#F97316")
        source.paste(Image.new("RGBA", (100, 100), "#14B8A6"), (0, 100))
        source.paste(Image.new("RGBA", (100, 100), "#4F46E5"), (0, 200))
        source.save(source_path)

        # When: Rendering backgrounds and image layers with face metadata and without faces
        Canvas(100, 100).background(
            image=str(source_path),
            fit="cover",
            focal_point=(0.5, 1.0),
            faces=[{"x": 0.2, "y": 0.08, "width": 0.6, "height": 0.1}],
        ).render(face_output)
        Canvas(100, 100).background(
            image=str(source_path),
            fit="cover",
            focal_point=(0.5, 1.0),
            faces=[],
        ).render(fallback_output)
        Canvas(100, 100).image(
            path=str(source_path),
            position=(0, 0),
            width=100,
            height=100,
            fit="cover",
            focal_point=(0.5, 1.0),
            faces=[{"x": 0.2, "y": 0.08, "width": 0.6, "height": 0.1}],
        ).render(image_face_output)
        Canvas(100, 100).image(
            path=str(source_path),
            position=(0, 0),
            width=100,
            height=100,
            fit="cover",
            focal_point=(0.5, 1.0),
            faces=[],
        ).render(image_fallback_output)

        # Then: Face-aware crops keep the top band, while fallback uses the focal point
        face_render = Image.open(face_output).convert("RGBA")
        fallback_render = Image.open(fallback_output).convert("RGBA")
        image_face_render = Image.open(image_face_output).convert("RGBA")
        image_fallback_render = Image.open(image_fallback_output).convert("RGBA")
        assert pixel_rgb(face_render, (50, 50)) == (249, 115, 22)
        assert pixel_rgb(fallback_render, (50, 50)) == (79, 70, 229)
        assert pixel_rgb(image_face_render, (50, 50)) == (249, 115, 22)
        assert pixel_rgb(image_fallback_render, (50, 50)) == (79, 70, 229)

    def test_should_render_face_aware_text_fill_and_fallback(self, tmp_path):
        """Text image fills use face regions and fall back to focal-point cropping"""
        from quickthumb import Canvas, TextFillImage

        source_path = tmp_path / "vertical-bands.png"
        face_output = tmp_path / "text-face.png"
        fallback_output = tmp_path / "text-fallback.png"

        # Given: A tall source image with a face region near the top and a bottom focal point
        source = Image.new("RGBA", (100, 300), "#F97316")
        source.paste(Image.new("RGBA", (100, 100), "#14B8A6"), (0, 100))
        source.paste(Image.new("RGBA", (100, 100), "#4F46E5"), (0, 200))
        source.save(source_path)

        # When: Rendering text with face-aware and fallback image fills
        Canvas(160, 140).background(color="#000000").text(
            "H",
            size=120,
            fill=TextFillImage(
                path=str(source_path),
                fit=FitMode.COVER,
                focal_point=(0.5, 1.0),
                faces=[FaceRegion(x=0.2, y=0.08, width=0.6, height=0.1)],
            ),
            position=(15, 0),
        ).render(face_output)
        Canvas(160, 140).background(color="#000000").text(
            "H",
            size=120,
            fill=TextFillImage(
                path=str(source_path),
                fit=FitMode.COVER,
                focal_point=(0.5, 1.0),
                faces=[],
            ),
            position=(15, 0),
        ).render(fallback_output)

        # Then: The text fill follows face metadata and uses the focal point without faces
        face_render = Image.open(face_output).convert("RGBA")
        fallback_render = Image.open(fallback_output).convert("RGBA")
        face_color_counts = face_render.getcolors(maxcolors=face_render.width * face_render.height)
        fallback_color_counts = fallback_render.getcolors(
            maxcolors=fallback_render.width * fallback_render.height
        )
        assert face_color_counts is not None
        assert fallback_color_counts is not None
        face_colors = {color for _, color in face_color_counts}
        fallback_colors = {color for _, color in fallback_color_counts}
        assert (249, 115, 22, 255) in face_colors
        assert (79, 70, 229, 255) in fallback_colors


class TestImageLayerBorderRadius:
    """Test suite for image layer border_radius (rounded corners)"""

    def test_should_accept_border_radius_on_image_layer(self):
        """Test that Canvas.image() accepts border_radius and stores it in the layer"""
        from quickthumb import Canvas

        canvas = Canvas(400, 300)
        result = canvas.image(path="assets/logo.png", position=(0, 0), width=200, border_radius=20)

        assert result is canvas
        assert canvas.layers[0] == snapshot(
            ImageLayer(
                type="image",
                path="assets/logo.png",
                position=(0, 0),
                width=200,
                border_radius=20,
            )
        )

    def test_should_reject_negative_border_radius(self):
        """Test that negative border_radius raises ValidationError"""
        from quickthumb import Canvas

        canvas = Canvas(400, 300)

        with pytest.raises(ValidationError, match="border_radius.*greater than or equal to 0"):
            canvas.image(path="assets/logo.png", position=(0, 0), border_radius=-1)


class TestImageLayerSerialization:
    """Test suite for JSON serialization/deserialization"""

    def test_should_round_trip_remove_background_through_json(self):
        """Test that remove_background survives JSON round-trip"""
        from quickthumb import Canvas

        # Given: Canvas with remove_background=True
        original = Canvas(1920, 1080)
        original.image(path="logo.png", position=(0, 0), remove_background=True)

        # When: Round-tripping through JSON
        restored = Canvas.from_json(original.to_json())

        # Then: remove_background should be preserved
        assert restored.layers[0] == original.layers[0]

    def test_should_serialize_image_layer_to_json(self):
        """Test that canvas with image layer can be serialized to JSON"""
        # Given: Canvas with image layer with all parameters
        from quickthumb import Canvas

        canvas = Canvas(1920, 1080)
        canvas.image(
            path="assets/logo.png",
            position=(50, 50),
            width=200,
            height=150,
            opacity=0.8,
            rotation=45,
            align=("center", "middle"),
            fit="cover",
            blend_mode="screen",
        )

        # When: User serializes canvas to JSON

        json_str = canvas.to_json()
        data = json.loads(json_str)

        # Then: JSON should contain image layer with correct structure
        assert data["width"] == 1920
        assert data["height"] == 1080
        assert len(data["layers"]) == 1
        assert data["layers"][0] == {
            "type": "image",
            "path": "assets/logo.png",
            "position": [50, 50],
            "width": 200,
            "height": 150,
            "opacity": 0.8,
            "rotation": 45.0,
            "remove_background": False,
            "align": "center",
            "border_radius": 0,
            "fit": "cover",
            "blend_mode": "screen",
            "effects": [],
            "animation": None,
        }

    def test_should_deserialize_image_layer_from_json(self):
        """Test that canvas with image layer can be deserialized from JSON"""
        # Given: JSON string with image layer

        json_data = {
            "width": 1920,
            "height": 1080,
            "layers": [
                {
                    "type": "image",
                    "path": "assets/logo.png",
                    "position": [50, 50],
                    "width": 200,
                    "height": 150,
                    "opacity": 0.8,
                    "rotation": 45,
                    "align": ["center", "middle"],
                    "fit": "contain",
                    "blend_mode": "lighten",
                }
            ],
        }
        json_str = json.dumps(json_data)

        # When: User deserializes canvas from JSON
        from quickthumb import Canvas

        canvas = Canvas.from_json(json_str)

        # Then: Canvas should have image layer with correct properties
        assert canvas.width == 1920
        assert canvas.height == 1080
        assert len(canvas.layers) == 1
        assert canvas.layers[0] == ImageLayer(
            type="image",
            path="assets/logo.png",
            position=(50, 50),
            width=200,
            height=150,
            opacity=0.8,
            rotation=45,
            align=Align.CENTER,
            fit=FitMode.CONTAIN,
            blend_mode=BlendMode.LIGHTEN,
        )
        assert json.loads(canvas.to_json())["layers"][0]["fit"] == "contain"
        assert json.loads(canvas.to_json())["layers"][0]["blend_mode"] == "lighten"

    def test_should_round_trip_fit_intelligence_through_json(self):
        """Focal point and face metadata round-trip through Canvas JSON"""
        from quickthumb import Canvas, TextFillImage

        # Given: Canvas layers using cover fit intelligence across image fit paths
        canvas = (
            Canvas(400, 240)
            .background(
                image="background.jpg",
                fit="cover",
                focal_point=(0.8, 0.25),
                faces=[{"x": 0.65, "y": 0.1, "width": 0.2, "height": 0.3}],
            )
            .image(
                path="portrait.jpg",
                position=(10, 20),
                width=120,
                height=90,
                fit="cover",
                focal_point=(0.4, 0.35),
                faces=[FaceRegion(x=0.3, y=0.15, width=0.25, height=0.4)],
            )
            .text(
                "FIT",
                size=48,
                fill=TextFillImage(
                    path="texture.jpg",
                    fit=FitMode.COVER,
                    focal_point=(0.2, 0.5),
                    faces=[FaceRegion(x=0.1, y=0.2, width=0.2, height=0.2)],
                ),
                position=(0, 0),
            )
        )

        # When: Serializing and deserializing the canvas
        data = json.loads(canvas.to_json())
        restored = Canvas.from_json(json.dumps(data))

        # Then: The public crop metadata should survive on every image-fit path
        background = data["layers"][0]
        image = data["layers"][1]
        text_fill = data["layers"][2]["fill"]
        assert background["focal_point"] == [0.8, 0.25]
        assert background["faces"] == [{"x": 0.65, "y": 0.1, "width": 0.2, "height": 0.3}]
        assert image["focal_point"] == [0.4, 0.35]
        assert image["faces"] == [{"x": 0.3, "y": 0.15, "width": 0.25, "height": 0.4}]
        assert text_fill["focal_point"] == [0.2, 0.5]
        assert text_fill["faces"] == [{"x": 0.1, "y": 0.2, "width": 0.2, "height": 0.2}]
        background_layer = cast(BackgroundLayer, restored.layers[0])
        image_layer = cast(ImageLayer, restored.layers[1])
        text_layer = cast(TextLayer, restored.layers[2])
        assert background_layer.focal_point == (0.8, 0.25)
        assert image_layer.faces == [FaceRegion(x=0.3, y=0.15, width=0.25, height=0.4)]
        assert isinstance(text_layer.fill, TextFillImage)
        assert text_layer.fill.focal_point == (0.2, 0.5)

    def test_should_round_trip_image_layer_through_json(self):
        """Test that canvas with image layer can be serialized and deserialized"""
        from quickthumb import Canvas

        # Given: Canvas with image layer
        original = Canvas(1920, 1080)
        original.image(
            path="assets/logo.png",
            position=(50, 50),
            width=200,
            opacity=0.8,
            rotation=45,
            align=("center", "middle"),
        )

        # When: Round-tripping through JSON
        json_str = original.to_json()
        restored = Canvas.from_json(json_str)

        # Then: Restored canvas should match original
        assert restored.width == original.width
        assert restored.height == original.height
        assert len(restored.layers) == len(original.layers)
        assert restored.layers[0] == original.layers[0]

    def test_should_round_trip_image_motion_through_json(self):
        """Given an animated image, JSON restoration preserves its motion contract."""
        from quickthumb import Canvas

        # Given: an image using the semantic Ken Burns preset
        original = Canvas(160, 100).image(
            path="tests/fixtures/sample_image.jpg",
            position=(0, 0),
            width=160,
            height=100,
            fit="cover",
            focal_point=(0.8, 0.3),
            animation=AnimationSpec.ken_burns(direction="in", duration=2),
        )

        # When: the canvas is serialized and restored
        restored = Canvas.from_json(original.to_json())

        # Then: the public layer contract is unchanged
        assert restored.layers[0] == original.layers[0]

    def test_should_keep_image_motion_inside_the_fitted_composition_boundary(self):
        """Given viewport motion, frames change while masks and box dimensions stay fixed."""
        from quickthumb import Canvas, LayerMask

        # Given: a cover-fitted image with a rectangular composition mask
        canvas = Canvas(160, 100).image(
            path="tests/fixtures/sample_image.jpg",
            position=(0, 0),
            width=120,
            height=80,
            fit="cover",
            focal_point=(0.8, 0.5),
            mask=LayerMask(shape="ellipse", position=(0, 0), width=120, height=80),
            animation=AnimationSpec.ken_burns(duration=1),
        )

        # When: deterministic frames are sampled before and after the motion
        first = canvas.render_frame(0)
        last = canvas.render_frame(1)

        # Then: viewport motion changes pixels without changing the layer boundary
        assert first.size == last.size == (160, 100)
        assert first.tobytes() != last.tobytes()
        assert first.getpixel((0, 0))[3] == 0
        assert last.getpixel((0, 0))[3] == 0

    def test_should_serialize_percentage_position_to_json(self):
        """Test that percentage positions are serialized correctly"""
        # Given: Canvas with image using percentage position
        from quickthumb import Canvas

        canvas = Canvas(1920, 1080)
        canvas.image(path="assets/logo.png", position=("50%", "25%"), width=100)

        # When: Serializing to JSON

        json_str = canvas.to_json()
        data = json.loads(json_str)

        # Then
        assert data == snapshot(
            {
                "kind": "canvas",
                "width": 1920,
                "height": 1080,
                "layers": [
                    {
                        "type": "image",
                        "path": "assets/logo.png",
                        "position": ["50%", "25%"],
                        "width": 100,
                        "height": None,
                        "opacity": 1.0,
                        "rotation": 0.0,
                        "remove_background": False,
                        "align": "top-left",
                        "border_radius": 0,
                        "fit": None,
                        "blend_mode": None,
                        "effects": [],
                        "animation": None,
                    }
                ],
            }
        )

    def test_should_serialize_image_with_effects_to_json(self):
        """Test that image layer with effects serializes the effects field correctly"""
        import json

        from quickthumb import Canvas, Shadow

        canvas = Canvas(400, 300)
        canvas.image(
            path="assets/logo.png",
            position=(50, 50),
            width=200,
            effects=[Shadow(offset_x=5, offset_y=5, color="#000000", blur_radius=10)],
        )

        data = json.loads(canvas.to_json())

        assert data == snapshot(
            {
                "kind": "canvas",
                "width": 400,
                "height": 300,
                "layers": [
                    {
                        "type": "image",
                        "path": "assets/logo.png",
                        "position": [50, 50],
                        "width": 200,
                        "height": None,
                        "opacity": 1.0,
                        "rotation": 0.0,
                        "remove_background": False,
                        "align": "top-left",
                        "border_radius": 0,
                        "fit": None,
                        "blend_mode": None,
                        "effects": [
                            {
                                "type": "shadow",
                                "offset_x": 5,
                                "offset_y": 5,
                                "color": "#000000",
                                "blur_radius": 10,
                            }
                        ],
                        "animation": None,
                    }
                ],
            }
        )

    def test_should_deserialize_image_with_effects_from_json(self):
        """Test that image layer with effects deserializes correctly"""
        import json

        from quickthumb import Canvas, Shadow
        from quickthumb.models import ImageLayer

        json_data = {
            "width": 400,
            "height": 300,
            "layers": [
                {
                    "type": "image",
                    "path": "assets/logo.png",
                    "position": [50, 50],
                    "width": 200,
                    "effects": [
                        {
                            "type": "shadow",
                            "offset_x": 5,
                            "offset_y": 5,
                            "color": "#000000",
                            "blur_radius": 10,
                        }
                    ],
                }
            ],
        }

        canvas = Canvas.from_json(json.dumps(json_data))

        assert canvas.layers[0] == snapshot(
            ImageLayer(
                type="image",
                path="assets/logo.png",
                position=(50, 50),
                width=200,
                effects=[Shadow(offset_x=5, offset_y=5, color="#000000", blur_radius=10)],
            )
        )

    def test_should_deserialize_percentage_position_from_json(self):
        """Test that percentage positions are deserialized correctly"""
        # Given: JSON with percentage position

        json_data = {
            "width": 1920,
            "height": 1080,
            "layers": [
                {
                    "type": "image",
                    "path": "assets/logo.png",
                    "position": ["50%", "25%"],
                    "width": 100,
                }
            ],
        }

        # When: Deserializing from JSON
        from quickthumb import Canvas

        canvas = Canvas.from_json(json.dumps(json_data))

        # Then
        assert canvas.layers[0] == snapshot(
            ImageLayer(type="image", path="assets/logo.png", position=("50%", "25%"), width=100)
        )

    def test_should_serialize_image_with_filter_effect_to_json(self):
        """Test that image layer with Filter effect serializes correctly (T014)"""
        from quickthumb import Canvas, Filter

        canvas = Canvas(400, 300)
        canvas.image(
            path="assets/logo.png",
            position=(0, 0),
            width=200,
            effects=[Filter(blur=4, brightness=0.7, contrast=1.2, saturation=0.5)],
        )

        data = json.loads(canvas.to_json())

        assert data == snapshot(
            {
                "kind": "canvas",
                "width": 400,
                "height": 300,
                "layers": [
                    {
                        "type": "image",
                        "path": "assets/logo.png",
                        "position": [0, 0],
                        "width": 200,
                        "height": None,
                        "opacity": 1.0,
                        "rotation": 0.0,
                        "remove_background": False,
                        "align": "top-left",
                        "border_radius": 0,
                        "fit": None,
                        "blend_mode": None,
                        "effects": [
                            {
                                "type": "filter",
                                "blur": 4,
                                "brightness": 0.7,
                                "contrast": 1.2,
                                "saturation": 0.5,
                            }
                        ],
                        "animation": None,
                    }
                ],
            }
        )
