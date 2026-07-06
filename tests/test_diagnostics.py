"""Tests for canvas diagnostics (canvas.diagnose())"""

import json
from pathlib import Path

import pytest
from PIL import Image

FIXTURE_SVG = str(Path(__file__).parent / "fixtures" / "sample.svg")


class TestDiagnoseCleanCanvas:
    """Test suite for canvases that should produce no findings"""

    def test_should_return_no_diagnostics_for_a_clean_canvas(self):
        """A well-formed canvas with readable, in-bounds layers produces no findings"""
        from quickthumb import Canvas

        # given: black 40px text on a white background, fully inside the canvas
        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .text("Hello world", size=40, color="#000000", position=(10, 10))
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert diagnostics == []


class TestDiagnoseOffCanvas:
    """Test suite for off-canvas detection"""

    @pytest.mark.parametrize("position", [(300, 300), (-100, -100)])
    def test_should_report_error_for_layer_fully_outside_canvas(self, position):
        """A layer entirely outside the canvas, on either side, is an off-canvas error"""
        from quickthumb import Canvas

        # given: a shape placed entirely past a canvas corner
        canvas = (
            Canvas(200, 200)
            .background(color="#FFFFFF")
            .shape(shape="rectangle", position=position, width=50, height=50, color="#FF0000")
        )

        # when
        diagnostics = canvas.diagnose()

        # then: a single off-canvas error pointing at the shape layer
        assert len(diagnostics) == 1
        finding = diagnostics[0]
        assert finding.code == "off-canvas"
        assert finding.severity == "error"
        assert finding.layer_index == 1

    def test_should_report_warning_for_layer_partially_outside_canvas(self):
        """A layer extending past a canvas edge is an off-canvas warning"""
        from quickthumb import Canvas

        # given: a shape that crosses the bottom-right edge
        canvas = (
            Canvas(200, 200)
            .background(color="#FFFFFF")
            .shape(shape="rectangle", position=(180, 180), width=50, height=50, color="#FF0000")
        )

        # when
        diagnostics = canvas.diagnose()

        # then: the full finding (including its message) is pinned
        assert [finding.model_dump(mode="json", exclude_none=True) for finding in diagnostics] == [
            {
                "code": "off-canvas",
                "severity": "warning",
                "layer_index": 1,
                "message": (
                    "shape layer at (180, 180) size 50x50 extends past the edge "
                    "of the 200x200 canvas"
                ),
                "layer_id": "layer:1",
                "bbox": {"x": 180, "y": 180, "width": 50, "height": 50},
                "related_layers": ["layer:1"],
                "measured": {
                    "layer_type": "shape",
                    "canvas_width": 200,
                    "canvas_height": 200,
                    "outside": "partially",
                },
                "suggestion": "move layer to x=150, y=150 to fit within the canvas",
            }
        ]

    def test_should_include_structured_fields_for_off_canvas_layer(self):
        """Off-canvas diagnostics expose bbox, related layer ids, measurements, and suggestion"""
        from quickthumb import Canvas

        # given: a shape that crosses the canvas edge
        canvas = (
            Canvas(100, 100)
            .background(color="#FFFFFF")
            .shape(
                shape="rectangle",
                position=(80, 90),
                width=40,
                height=30,
                color="#FF0000",
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        finding = diagnostics[0]
        assert finding.code == "off-canvas"
        assert finding.layer_id == "layer:1"
        assert finding.layer_name is None
        assert finding.bbox is not None
        assert finding.bbox.model_dump() == {"x": 80, "y": 90, "width": 40, "height": 30}
        assert finding.related_layers == ["layer:1"]
        assert finding.measured == {
            "layer_type": "shape",
            "canvas_width": 100,
            "canvas_height": 100,
            "outside": "partially",
        }
        assert finding.suggestion == "move layer to x=60, y=70 to fit within the canvas"

    def test_should_suggest_resizing_for_oversized_off_canvas_layer(self):
        """A layer larger than the canvas gets a resize suggestion, not an impossible move"""
        from quickthumb import Canvas

        # given: a layer that cannot fit in the canvas at any position
        canvas = Canvas(100, 100).shape(
            shape="rectangle",
            position=(10, 10),
            width=150,
            height=80,
            color="#FF0000",
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        finding = diagnostics[0]
        assert finding.code == "off-canvas"
        assert (
            finding.suggestion == "resize layer to fit within the 100x100 canvas before moving it"
        )

    def test_should_suggest_declared_position_for_aligned_off_canvas_layer(self):
        """Aligned layer suggestions use editable position coordinates, not bbox top-left"""
        from quickthumb import Canvas

        # given: a bottom-right aligned layer whose measured bbox starts off-canvas
        canvas = Canvas(100, 100).shape(
            shape="rectangle",
            position=(10, 10),
            width=20,
            height=20,
            color="#FF0000",
            align=("right", "bottom"),
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        finding = diagnostics[0]
        assert finding.code == "off-canvas"
        assert finding.bbox is not None
        assert finding.bbox.model_dump() == {"x": -10, "y": -10, "width": 20, "height": 20}
        assert finding.suggestion == "move layer to x=20, y=20 to fit within the canvas"

    def test_should_use_current_canvas_size_for_off_canvas_suggestions(self):
        """Off-canvas suggestions use canvas dimensions current at diagnose time"""
        from quickthumb import Canvas

        # given: a canvas resized after its diagnostics engine was constructed
        canvas = Canvas(100, 100).shape(
            shape="rectangle",
            position=(180, 20),
            width=50,
            height=50,
            color="#FF0000",
        )
        canvas.width = 200

        # when
        diagnostics = canvas.diagnose()

        # then
        finding = diagnostics[0]
        assert finding.code == "off-canvas"
        assert finding.measured["canvas_width"] == 200
        assert finding.suggestion == "move layer to x=150, y=20 to fit within the canvas"

    def test_should_report_group_extending_past_canvas(self):
        """Group boxes are measured as a unit for off-canvas detection"""
        from quickthumb import Canvas

        # given: a group anchored near the corner whose content overflows the canvas
        canvas = (
            Canvas(200, 200)
            .background(color="#FFFFFF")
            .group(
                children=[
                    {
                        "type": "shape",
                        "shape": "rectangle",
                        "width": 100,
                        "height": 100,
                        "color": "#FF0000",
                    }
                ],
                position=(150, 150),
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [d.code for d in diagnostics] == ["off-canvas"]
        assert diagnostics[0].severity == "warning"


class TestDiagnoseText:
    """Test suite for text legibility findings"""

    def test_should_warn_for_tiny_text(self):
        """Text smaller than 2.5% of canvas height is flagged as illegible"""
        from quickthumb import Canvas

        # given: 14px text on a 720p canvas (threshold is 18px)
        canvas = (
            Canvas(1280, 720)
            .background(color="#FFFFFF")
            .text("fine print", size=14, color="#000000", position=(10, 10))
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [d.code for d in diagnostics] == ["tiny-text"]
        assert diagnostics[0].severity == "warning"

    def test_should_include_structured_values_for_tiny_text(self):
        """Tiny-text diagnostics expose text size, threshold, bbox, and suggestion"""
        from quickthumb import Canvas

        # given: 14px text on a 720p canvas (threshold is 18px)
        canvas = (
            Canvas(1280, 720)
            .background(color="#FFFFFF")
            .text("fine print", size=14, color="#000000", position=(10, 10))
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        finding = diagnostics[0]
        assert finding.code == "tiny-text"
        assert finding.layer_id == "layer:1"
        assert finding.bbox is not None
        assert finding.bbox.x == 10
        assert finding.bbox.y == 10
        assert finding.related_layers == ["layer:1"]
        assert finding.measured == {
            "font_size": 14,
            "threshold": 18.0,
            "threshold_ratio": 0.025,
            "canvas_height": 720,
        }
        assert finding.suggestion == "increase text size to at least 18px"

    def test_should_not_warn_for_text_at_the_size_threshold(self):
        """Text exactly at 2.5% of canvas height is not flagged (strict less-than)"""
        from quickthumb import Canvas

        # given: 18px text on a 720p canvas, exactly at the threshold
        canvas = (
            Canvas(1280, 720)
            .background(color="#FFFFFF")
            .text("threshold", size=18, color="#000000", position=(10, 10))
        )

        # when / then
        assert canvas.diagnose() == []

    def test_should_warn_for_tiny_rich_text_parts(self):
        """Rich text is flagged when any part's effective size falls below the threshold"""
        from quickthumb import Canvas

        # given: a 40px rich-text layer where one part overrides down to 14px (threshold 18px)
        canvas = (
            Canvas(1280, 720)
            .background(color="#FFFFFF")
            .text(
                [
                    {"text": "headline ", "color": "#000000"},
                    {"text": "fine print", "size": 14, "color": "#000000"},
                ],
                size=40,
                position=(10, 10),
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [d.code for d in diagnostics] == ["tiny-text"]
        assert diagnostics[0].severity == "warning"

    def test_should_not_warn_for_rich_text_parts_inheriting_a_readable_layer_size(self):
        """Size-less parts inherit the layer size, so a 40px layer is not flagged"""
        from quickthumb import Canvas

        # given: rich text whose parts set no size of their own (effective size is 40px)
        canvas = (
            Canvas(1280, 720)
            .background(color="#FFFFFF")
            .text(
                [
                    {"text": "headline ", "color": "#000000"},
                    {"text": "subhead", "color": "#333333"},
                ],
                size=40,
                position=(10, 10),
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert diagnostics == []

    def test_should_warn_when_a_rich_text_word_exceeds_max_width(self):
        """An unbreakable word inside a rich-text part is flagged like plain-text overflow"""
        from quickthumb import Canvas

        # given: a rich-text part containing an unbreakable long word in a 60px column
        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .text(
                [
                    {"text": "try ", "color": "#000000"},
                    {"text": "Supercalifragilisticexpialidocious", "color": "#000000"},
                ],
                size=40,
                position=(10, 10),
                max_width=60,
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then: one overflow finding naming the word, plus the off-canvas warning it causes
        assert [d.code for d in diagnostics] == ["text-overflow", "off-canvas"]
        assert diagnostics[0].severity == "warning"
        assert diagnostics[0].layer_index == 1
        assert "Supercalifragilisticexpialidocious" in diagnostics[0].message

    def test_should_warn_when_a_word_exceeds_max_width(self):
        """A single word wider than max_width cannot wrap and is flagged"""
        from quickthumb import Canvas

        # given: an unbreakable long word in a 60px column
        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .text(
                "Supercalifragilisticexpialidocious",
                size=40,
                color="#000000",
                position=(10, 10),
                max_width=60,
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then: text-overflow plus the off-canvas warning the overflow causes
        assert [d.code for d in diagnostics] == ["text-overflow", "off-canvas"]
        assert diagnostics[0].severity == "warning"
        assert diagnostics[0].layer_index == 1

    def test_should_include_structured_values_for_text_overflow(self):
        """Text-overflow diagnostics expose the word, measured width, bbox, and suggestion"""
        from quickthumb import Canvas

        # given: an unbreakable long word in a 60px column
        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .text(
                "Supercalifragilisticexpialidocious",
                size=40,
                color="#000000",
                position=(10, 10),
                max_width=60,
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        finding = diagnostics[0]
        assert finding.code == "text-overflow"
        assert finding.layer_id == "layer:1"
        assert finding.bbox is not None
        assert finding.bbox.x == 10
        assert finding.bbox.y == 10
        assert finding.related_layers == ["layer:1"]
        assert finding.measured["word"] == "Supercalifragilisticexpialidocious"
        assert finding.measured["max_width"] == 60
        assert finding.measured["word_width"] > finding.measured["max_width"]
        expected_suggestion = (
            f"increase max_width to at least {finding.measured['word_width']}px "
            "or enable auto_scale"
        )
        assert finding.suggestion == expected_suggestion

    def test_should_warn_when_wrapped_text_extends_past_canvas(self):
        """Wrapped text that runs beyond the canvas receives a text-clipped warning"""
        from quickthumb import Canvas

        # given: a wrapped text block starting too low to fit all rendered lines
        canvas = (
            Canvas(260, 110)
            .background(color="#FFFFFF")
            .text(
                "one two three four five six seven eight nine ten",
                size=30,
                color="#000000",
                position=(10, 70),
                max_width=90,
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [d.code for d in diagnostics] == ["text-clipped", "off-canvas"]
        finding = diagnostics[0]
        assert finding.bbox is not None
        bbox = finding.bbox.model_dump()
        assert bbox["width"] <= 90
        assert bbox["y"] + bbox["height"] > 110
        assert finding.model_dump() == {
            "code": "text-clipped",
            "severity": "warning",
            "layer_index": 1,
            "message": (
                f"wrapped text block at (10, 70) size {bbox['width']}x{bbox['height']} "
                "exceeds canvas and may be clipped"
            ),
            "layer_id": "layer:1",
            "layer_name": None,
            "bbox": {"x": 10, "y": 70, "width": bbox["width"], "height": bbox["height"]},
            "related_layers": ["layer:1"],
            "measured": {
                "text_bbox": {"x": 10, "y": 70, "width": bbox["width"], "height": bbox["height"]},
                "wrapped_line_count": 10,
                "max_width": 90,
                "text_width": bbox["width"],
                "text_height": bbox["height"],
                "canvas_width": 260,
                "canvas_height": 110,
                "clipped_by": "canvas",
                "overflow": {"bottom": bbox["y"] + bbox["height"] - 110},
            },
            "suggestion": (
                "move the text fully inside the canvas, reduce text size, increase max_width, "
                "or enable auto_scale"
            ),
        }

    def test_should_warn_when_wrapped_text_exceeds_declared_width(self):
        """Wrapped text wider than max_width receives a text-clipped warning"""
        from quickthumb import Canvas

        # given: a wrapped block with an unbreakable word that exceeds max_width
        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .text(
                "overlong ok",
                size=40,
                color="#000000",
                position=(10, 10),
                max_width=50,
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [d.code for d in diagnostics] == ["text-overflow", "text-clipped"]
        finding = diagnostics[1]
        assert finding.bbox is not None
        bbox = finding.bbox.model_dump()
        assert bbox["width"] > 50
        assert bbox["x"] + bbox["width"] <= 400
        assert finding.model_dump() == {
            "code": "text-clipped",
            "severity": "warning",
            "layer_index": 1,
            "message": (
                f"wrapped text block at (10, 10) size {bbox['width']}x{bbox['height']} "
                "exceeds max_width and may be clipped"
            ),
            "layer_id": "layer:1",
            "layer_name": None,
            "bbox": {"x": 10, "y": 10, "width": bbox["width"], "height": bbox["height"]},
            "related_layers": ["layer:1"],
            "measured": {
                "text_bbox": {"x": 10, "y": 10, "width": bbox["width"], "height": bbox["height"]},
                "wrapped_line_count": 2,
                "max_width": 50,
                "text_width": bbox["width"],
                "text_height": bbox["height"],
                "canvas_width": 400,
                "canvas_height": 300,
                "clipped_by": "max_width",
                "overflow_width": bbox["width"] - 50,
            },
            "suggestion": (
                "move the text fully inside the canvas, reduce text size, increase max_width, "
                "or enable auto_scale"
            ),
        }

    def test_should_warn_when_overflowing_word_also_extends_past_canvas_vertically(self):
        """Text overflow does not suppress vertical text-clipped canvas diagnostics"""
        from quickthumb import Canvas

        # given: a wrapped block with an overflowing word that starts too low to fit
        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .text(
                "overlong ok",
                size=40,
                color="#000000",
                position=(10, 250),
                max_width=50,
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [d.code for d in diagnostics] == ["text-overflow", "text-clipped", "off-canvas"]
        finding = diagnostics[1]
        assert finding.bbox is not None
        bbox = finding.bbox.model_dump()
        assert finding.model_dump() == {
            "code": "text-clipped",
            "severity": "warning",
            "layer_index": 1,
            "message": (
                f"wrapped text block at (10, 250) size {bbox['width']}x{bbox['height']} "
                "exceeds canvas and may be clipped"
            ),
            "layer_id": "layer:1",
            "layer_name": None,
            "bbox": {"x": 10, "y": 250, "width": bbox["width"], "height": bbox["height"]},
            "related_layers": ["layer:1"],
            "measured": {
                "text_bbox": {"x": 10, "y": 250, "width": bbox["width"], "height": bbox["height"]},
                "wrapped_line_count": 2,
                "max_width": 50,
                "text_width": bbox["width"],
                "text_height": bbox["height"],
                "canvas_width": 400,
                "canvas_height": 300,
                "clipped_by": "canvas",
                "overflow": {"bottom": bbox["y"] + bbox["height"] - 300},
            },
            "suggestion": (
                "move the text fully inside the canvas, reduce text size, increase max_width, "
                "or enable auto_scale"
            ),
        }

    def test_should_warn_when_default_font_renders_missing_glyph(self, monkeypatch):
        """Characters rendered as the active font replacement glyph are flagged"""
        from quickthumb import Canvas

        # given: the bundled default font and a Hangul character it cannot draw
        monkeypatch.delenv("QUICKTHUMB_DEFAULT_FONT", raising=False)
        canvas = (
            Canvas(200, 120)
            .background(color="#FFFFFF")
            .text("\ud55c", size=40, color="#000000", position=(10, 10))
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [d.code for d in diagnostics] == ["missing-glyph"]
        finding = diagnostics[0]
        assert finding.bbox is not None
        bbox = finding.bbox.model_dump()
        assert finding.model_dump() == {
            "code": "missing-glyph",
            "severity": "warning",
            "layer_index": 1,
            "message": (
                "text contains glyphs that render as the font replacement glyph: " + repr("\ud55c")
            ),
            "layer_id": "layer:1",
            "layer_name": None,
            "bbox": {"x": 10, "y": 10, "width": bbox["width"], "height": bbox["height"]},
            "related_layers": ["layer:1"],
            "measured": {"characters": ["\ud55c"], "character_count": 1},
            "suggestion": "use a font that supports '\ud55c'",
        }

    def test_should_warn_when_later_rich_text_part_renders_same_character_as_missing_glyph(self):
        """Missing-glyph checks evaluate repeated characters across rich-text font runs"""
        from quickthumb import Canvas, TextPart

        # given: the first font supports the character, but a later font renders it as tofu
        missing = "\u0180"
        canvas = (
            Canvas(200, 120)
            .background(color="#FFFFFF")
            .text(
                [
                    TextPart(text=missing, font="NotoSans"),
                    TextPart(text=missing, font="Roboto"),
                ],
                size=40,
                color="#000000",
                position=(10, 10),
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [d.code for d in diagnostics] == ["missing-glyph"]
        finding = diagnostics[0]
        assert finding.bbox is not None
        bbox = finding.bbox.model_dump()
        assert finding.model_dump() == {
            "code": "missing-glyph",
            "severity": "warning",
            "layer_index": 1,
            "message": (
                "text contains glyphs that render as the font replacement glyph: " + repr(missing)
            ),
            "layer_id": "layer:1",
            "layer_name": None,
            "bbox": {"x": 10, "y": 10, "width": bbox["width"], "height": bbox["height"]},
            "related_layers": ["layer:1"],
            "measured": {"characters": [missing], "character_count": 1},
            "suggestion": f"use a font that supports {repr(missing)}",
        }

    def test_should_not_warn_for_skipped_missing_glyph_sentinels(self, monkeypatch):
        """Replacement glyph sentinels and whitespace are not reported as missing glyphs"""
        from quickthumb import Canvas

        # given: sentinel characters are intentional fallback markers, not missing content
        monkeypatch.delenv("QUICKTHUMB_DEFAULT_FONT", raising=False)
        canvas = (
            Canvas(200, 120)
            .background(color="#FFFFFF")
            .text("\ufffd \u25a1\n\tA", size=40, color="#000000", position=(10, 10))
        )

        # when / then
        assert canvas.diagnose() == []

    def test_should_warn_for_low_contrast_text(self):
        """Near-white text on a white background is flagged as low contrast"""
        from quickthumb import Canvas

        # given
        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .text("ghost text", size=40, color="#F8F8F8", position=(10, 10))
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [d.code for d in diagnostics] == ["low-contrast"]
        assert diagnostics[0].severity == "warning"
        assert diagnostics[0].layer_index == 1

    def test_should_include_structured_values_for_low_contrast_text(self):
        """Low-contrast diagnostics expose measured contrast and a repair suggestion"""
        from quickthumb import Canvas

        # given: near-white text on a white background
        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .text(
                "ghost text",
                size=40,
                color="#F8F8F8",
                position=(10, 10),
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        finding = diagnostics[0]
        assert finding.code == "low-contrast"
        assert finding.layer_id == "layer:1"
        assert finding.layer_name is None
        assert finding.bbox is not None
        assert finding.bbox.x == 10
        assert finding.bbox.y == 10
        assert finding.bbox.width > 0
        assert finding.bbox.height > 0
        assert finding.related_layers == ["layer:1"]
        assert finding.measured == {
            "contrast": 1.0620159366897584,
            "threshold": 2.0,
            "method": "worst-tile",
            "tile_bbox": {"x": 10, "y": 10, "width": 32, "height": 32},
            "tile_count": 12,
            "tile_size": 32,
            "foreground_rgb": (248.0, 248.0, 248.0),
            "background_rgb": (255.0, 255.0, 255.0),
        }
        assert finding.suggestion == "increase foreground/background contrast to at least 2.0:1"

    def test_should_warn_for_worst_tile_contrast_on_busy_background(self):
        """Mixed backgrounds fail when any tile under the text has low contrast"""
        from quickthumb import Canvas

        def paint_split_background(image: Image.Image) -> None:
            image.paste((0, 0, 0, 255), (0, 0, 240, 120))
            image.paste((255, 255, 255, 255), (116, 0, 240, 120))

        # given: white text spans a black/white split background whose average is readable
        canvas = (
            Canvas(240, 120)
            .custom(paint_split_background)
            .text("BUSY TITLE", size=36, color="#FFFFFF", position=(20, 30))
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [d.code for d in diagnostics] == ["low-contrast"]
        finding = diagnostics[0]
        assert finding.measured == {
            "contrast": 1.0,
            "threshold": 2.0,
            "method": "worst-tile",
            "tile_bbox": {"x": 116, "y": 30, "width": 32, "height": 26},
            "tile_count": 6,
            "tile_size": 32,
            "foreground_rgb": (255.0, 255.0, 255.0),
            "background_rgb": (255.0, 255.0, 255.0),
        }

    def test_should_ignore_low_contrast_tiles_without_text_pixels(self):
        """Whitespace inside the text bbox does not drive low-contrast findings"""
        from quickthumb import Canvas

        def paint_background_with_light_gap(image: Image.Image) -> None:
            image.paste((0, 0, 0, 255), (0, 0, 300, 120))
            image.paste((255, 255, 255, 255), (70, 0, 120, 120))

        # given: white glyphs sit on black while only the empty space crosses white
        canvas = (
            Canvas(300, 120)
            .custom(paint_background_with_light_gap)
            .text("A          A", size=36, color="#FFFFFF", position=(20, 30))
        )

        # when / then
        assert canvas.diagnose() == []

    def test_should_not_warn_for_readable_rich_text_on_split_background(self):
        """Rich text colors are compared only where each colored run renders"""
        from quickthumb import Canvas

        def paint_split_background(image: Image.Image) -> None:
            image.paste((0, 0, 0, 255), (0, 0, 300, 120))
            image.paste((255, 255, 255, 255), (70, 0, 300, 120))

        # given: white rich text renders on black and black rich text renders on white
        canvas = (
            Canvas(300, 120)
            .custom(paint_split_background)
            .text(
                [
                    {"text": "L", "color": "#FFFFFF"},
                    {"text": "          R", "color": "#000000"},
                ],
                size=36,
                position=(20, 30),
            )
        )

        # when / then
        assert canvas.diagnose() == []

    def test_should_use_default_text_color_for_worst_tile_contrast(self):
        """Text without a color still uses the public default black foreground"""
        from quickthumb import Canvas

        # given: default black text over a black background
        canvas = (
            Canvas(200, 120).background(color="#000000").text("default", size=36, position=(20, 20))
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [finding.code for finding in diagnostics] == ["low-contrast"]
        assert diagnostics[0].measured["foreground_rgb"] == (0.0, 0.0, 0.0)

    def test_should_warn_for_low_opacity_text(self):
        """Semi-transparent text is checked by its effective rendered contrast"""
        from quickthumb import Canvas

        # given: faint black text renders close to white over a white background
        canvas = (
            Canvas(240, 120)
            .background(color="#FFFFFF")
            .text("faint", size=36, color="#000000", opacity=0.1, position=(20, 20))
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [finding.code for finding in diagnostics] == ["low-contrast"]
        assert diagnostics[0].measured == {
            "contrast": 1.2480715209939224,
            "threshold": 2.0,
            "method": "worst-tile",
            "tile_bbox": {"x": 20, "y": 20, "width": 32, "height": 28},
            "tile_count": 3,
            "tile_size": 32,
            "foreground_rgb": (230.0, 230.0, 230.0),
            "background_rgb": (255.0, 255.0, 255.0),
        }

    def test_should_warn_for_low_contrast_rich_text_run_inside_tile(self):
        """A high-contrast run cannot hide a low-contrast run in the same tile"""
        from unittest.mock import ANY

        from quickthumb import Canvas

        # given: white rich text is readable but the following black run is invisible
        canvas = (
            Canvas(260, 120)
            .background(color="#000000")
            .text(
                [
                    {"text": "HELLO", "color": "#FFFFFF"},
                    {"text": "I", "color": "#000000"},
                ],
                size=36,
                position=(20, 20),
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [finding.code for finding in diagnostics] == ["low-contrast"]
        assert diagnostics[0].measured == {
            "contrast": 1.0,
            "threshold": 2.0,
            "method": "worst-tile",
            "tile_bbox": {"x": 116, "y": 20, "width": ANY, "height": 32},
            "tile_count": 8,
            "tile_size": 32,
            "foreground_rgb": (0.0, 0.0, 0.0),
            "background_rgb": (0.0, 0.0, 0.0),
        }

    @pytest.mark.parametrize(
        "background,color",
        [
            ("#FFFFFF", "#000000"),  # maximal contrast
            ("#777777", "#FFFFFF"),  # ratio ~4.5: clean under the 2.0 threshold
        ],
    )
    def test_should_not_warn_for_sufficient_contrast_text(self, background, color):
        """Contrast at or above the 2.0 ratio threshold produces no finding"""
        from quickthumb import Canvas

        # given
        canvas = (
            Canvas(400, 300)
            .background(color=background)
            .text("readable", size=40, color=color, position=(10, 10))
        )

        # when / then
        assert canvas.diagnose() == []

    def test_should_use_rich_text_part_colors_for_contrast(self):
        """Contrast checks read TextPart colors, not just the layer-level color"""
        from quickthumb import Canvas

        # given: near-invisible white parts on a white background, behind a black layer color
        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .text(
                [{"text": "ghost", "color": "#FFFFFF"}, {"text": " parts", "color": "#F8F8F8"}],
                size=40,
                color="#000000",
                position=(10, 10),
            )
        )

        # when / then: the part colors drive the finding despite the high-contrast layer color
        assert [d.code for d in canvas.diagnose()] == ["low-contrast"]

    def test_should_not_warn_for_readable_rich_text_part_colors(self):
        """Rich text whose parts contrast well with the backdrop produces no finding"""
        from quickthumb import Canvas

        # given: white parts on a near-black background
        canvas = (
            Canvas(400, 300)
            .background(color="#111111")
            .text(
                [{"text": "hero", "color": "#FFFFFF"}, {"text": " title", "color": "#EEEEEE"}],
                size=40,
                position=(10, 10),
            )
        )

        # when / then
        assert canvas.diagnose() == []

    def test_should_not_flag_auto_scaled_text_that_fits_after_scaling(self):
        """diagnose evaluates auto_scale text at its rendered size, not its declared size"""
        from quickthumb import Canvas

        # given: 80px text that auto-scales down to fit a 150px column
        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .text(
                "WORDS WRAP HERE",
                size=80,
                color="#000000",
                position=(10, 10),
                max_width=150,
                auto_scale=True,
            )
        )

        # when / then: no overflow or off-canvas findings for text that scales to fit
        assert canvas.diagnose() == []

    def test_should_diagnose_text_children_inside_groups(self):
        """Legibility checks apply to text nested in group layers, not only top-level text"""
        from quickthumb import Canvas

        # given: a 10px text child (threshold is 18px on 720p) inside a group
        canvas = (
            Canvas(1280, 720)
            .background(color="#FFFFFF")
            .group(
                children=[{"type": "text", "content": "credits", "size": 10, "color": "#000000"}],
                position=(10, 10),
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then: the finding points at the group's layer index
        assert [d.code for d in diagnostics] == ["tiny-text"]
        assert diagnostics[0].layer_index == 1

    def test_should_evaluate_contrast_against_layers_below(self):
        """Contrast uses the composited layers under the text, not just the bottom background"""
        from quickthumb import Canvas

        # given: white text over a dark overlay that sits on a white background
        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .background(color="#111111")
            .text("hero", size=60, color="#FFFFFF", position=(10, 10))
        )

        # when / then: the dark overlay makes white text readable
        assert canvas.diagnose() == []


class TestDiagnoseLayerOverlap:
    """Test suite for suspicious layer overlap findings"""

    def test_should_warn_when_text_layers_overlap(self):
        """Text over text is flagged because it is almost always unreadable"""
        from quickthumb import Canvas

        # given: two readable text layers whose measured boxes intersect
        canvas = (
            Canvas(360, 220)
            .background(color="#FFFFFF")
            .text("Alpha", size=48, color="#000000", position=(20, 20))
            .text("Beta", size=48, color="#000000", position=(50, 32))
        )

        # when
        diagnostics = canvas.diagnose()

        # then: the overlap points at the upper text layer and includes measured values
        overlap_findings = [finding for finding in diagnostics if finding.code == "layer-overlap"]
        assert len(overlap_findings) == 1
        finding = overlap_findings[0]
        assert finding.severity == "warning"
        assert finding.layer_index == 2
        assert "text layer layer:2 (order 2) overlaps text layer layer:1 (order 1)" in (
            finding.message
        )
        assert "bbox_overlap_pct=" in finding.message
        assert "visible_overlap_pct=" in finding.message
        assert "% of upper" in finding.message
        assert "move layer 2" in finding.message

    def test_should_allow_text_over_backdrop(self):
        """Text fully contained by a lower non-text backdrop is intentional layout"""
        from quickthumb import Canvas

        # given: a large backdrop shape behind a text label
        canvas = (
            Canvas(300, 180)
            .background(color="#FFFFFF")
            .shape(
                shape="rectangle",
                position=(20, 20),
                width=220,
                height=90,
                color="#EEEEEE",
            )
            .text("Label", size=40, color="#000000", position=(40, 38))
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [finding.code for finding in diagnostics] == []

    def test_should_warn_for_partial_overlap(self):
        """Substantial partial overlap between measured boxes is suspicious"""
        from quickthumb import Canvas

        # given: two visible shapes with a 40x40 intersection
        canvas = (
            Canvas(240, 180)
            .background(color="#FFFFFF")
            .shape(
                shape="rectangle",
                position=(20, 20),
                width=100,
                height=60,
                color="#FF0000",
            )
            .shape(
                shape="rectangle",
                position=(80, 40),
                width=80,
                height=50,
                color="#00FF00",
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [finding.model_dump(mode="json", exclude_none=True) for finding in diagnostics] == [
            {
                "code": "layer-overlap",
                "severity": "warning",
                "layer_index": 2,
                "message": (
                    "shape layer layer:2 (order 2) overlaps shape layer layer:1 "
                    "(order 1); bbox_overlap=1600px "
                    "(bbox_overlap_pct=40% of upper, 27% of lower), "
                    "visible_overlap=1600px "
                    "(visible_overlap_pct=40% of upper, 27% of lower); "
                    "move layer 2 to y=88 to clear the overlap"
                ),
                "layer_id": "layer:2",
                "bbox": {"x": 80, "y": 40, "width": 40, "height": 40},
                "related_layers": ["layer:2", "layer:1"],
                "measured": {
                    "lower_layer_id": "layer:1",
                    "upper_layer_id": "layer:2",
                    "lower_bbox": {"x": 20, "y": 20, "width": 100, "height": 60},
                    "upper_bbox": {"x": 80, "y": 40, "width": 80, "height": 50},
                    "overlap_bbox": {"x": 80, "y": 40, "width": 40, "height": 40},
                    "bbox_overlap": 1600,
                    "bbox_overlap_pct_lower": 1600 / 6000,
                    "bbox_overlap_pct_upper": 1600 / 4000,
                    "visible_overlap": 1600,
                    "visible_overlap_pct_lower": 1600 / 6000,
                    "visible_overlap_pct_upper": 1600 / 4000,
                },
                "suggestion": "move layer 2 to y=88 to clear the overlap",
            }
        ]

    def test_should_report_each_overlap_when_one_layer_intersects_multiple_layers(self):
        """Overlapping several layers reports every suspicious pair through diagnose"""
        from quickthumb import Canvas

        # given: three visible shapes with pairwise intersections
        canvas = (
            Canvas(260, 220)
            .background(color="#FFFFFF")
            .shape(
                shape="rectangle",
                position=(20, 20),
                width=100,
                height=100,
                color="#FF0000",
            )
            .shape(
                shape="rectangle",
                position=(40, 40),
                width=100,
                height=100,
                color="#00FF00",
            )
            .shape(
                shape="rectangle",
                position=(60, 60),
                width=100,
                height=100,
                color="#0000FF",
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then: each intersecting pair is represented at the public boundary
        overlap_findings = [finding for finding in diagnostics if finding.code == "layer-overlap"]
        assert [finding.related_layers for finding in overlap_findings] == [
            ["layer:2", "layer:1"],
            ["layer:3", "layer:1"],
            ["layer:3", "layer:2"],
        ]

    def test_should_not_warn_for_ellipse_corner_bbox_overlap(self):
        """Ellipse masks prevent corner-only bounding-box intersections from warning"""
        from quickthumb import Canvas

        # given: a rectangle fully inside an ellipse bbox corner but outside the ellipse pixels
        canvas = (
            Canvas(200, 200)
            .background(color="#FFFFFF")
            .shape(
                shape="ellipse",
                position=(20, 20),
                width=80,
                height=80,
                color="#FF0000",
            )
            .shape(
                shape="rectangle",
                position=(20, 20),
                width=10,
                height=10,
                color="#00FF00",
            )
        )

        # when / then
        assert canvas.diagnose() == []

    def test_should_not_warn_for_composed_mask_corner_bbox_overlap(self):
        """Layer masks remove transparent composition pixels from overlap diagnostics"""
        from quickthumb import Canvas

        # given: a small upper shape sits only in the transparent corner of a masked rectangle
        canvas = (
            Canvas(80, 80)
            .shape(
                shape="rectangle",
                position=(10, 10),
                width=60,
                height=60,
                color="#FF0000",
                mask={"shape": "ellipse", "position": (10, 10), "width": 60, "height": 60},
            )
            .shape(
                shape="rectangle",
                position=(10, 10),
                width=5,
                height=5,
                color="#0000FF",
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [finding for finding in diagnostics if finding.code == "layer-overlap"] == []

    def test_should_not_warn_for_transparent_png_bbox_overlap(self, tmp_path):
        """Transparent image pixels do not count as visible overlap"""
        from quickthumb import Canvas

        # given: two same-size PNG layers whose opaque pixels occupy opposite sides
        lower = tmp_path / "lower.png"
        upper = tmp_path / "upper.png"
        lower_image = Image.new("RGBA", (80, 80), (0, 0, 0, 0))
        upper_image = Image.new("RGBA", (80, 80), (0, 0, 0, 0))
        for x in range(0, 30):
            for y in range(80):
                lower_image.putpixel((x, y), (255, 0, 0, 255))
        for x in range(50, 80):
            for y in range(80):
                upper_image.putpixel((x, y), (0, 255, 0, 255))
        lower_image.save(lower)
        upper_image.save(upper)

        canvas = (
            Canvas(160, 120)
            .background(color="#FFFFFF")
            .image(path=str(lower), position=(20, 20))
            .image(path=str(upper), position=(20, 20))
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert diagnostics == []

    def test_should_not_warn_for_glyph_hole_bbox_overlap(self):
        """Text masks use rendered glyph pixels, not just text bounding boxes"""
        from quickthumb import Canvas

        # given: a shape placed inside the hollow center of a large glyph
        canvas = (
            Canvas(180, 160)
            .background(color="#FFFFFF")
            .text("O", size=110, color="#000000", position=(20, 10))
            .shape(
                shape="rectangle",
                position=(58, 50),
                width=24,
                height=24,
                color="#00FF00",
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert diagnostics == []

    @pytest.mark.parametrize(
        "canvas_size,lower_position,lower_size,upper_position,upper_size,expected_suggestion",
        [
            (
                (240, 180),
                (20, 100),
                (100, 60),
                (80, 110),
                (80, 50),
                "move layer 2 to y=42 to clear the overlap",
            ),
            (
                (180, 140),
                (20, 20),
                (80, 110),
                (60, 40),
                (40, 80),
                "move layer 2 to x=108 to clear the overlap",
            ),
            (
                (180, 140),
                (80, 20),
                (80, 110),
                (90, 40),
                (40, 80),
                "move layer 2 to x=32 to clear the overlap",
            ),
            (
                (120, 120),
                (20, 20),
                (40, 40),
                (10, 10),
                (80, 80),
                "move or resize layer 2 to clear the overlap",
            ),
        ],
    )
    def test_should_suggest_available_moves_for_overlaps(
        self,
        canvas_size,
        lower_position,
        lower_size,
        upper_position,
        upper_size,
        expected_suggestion,
    ):
        """Overlap suggestions use an available clear direction or fall back to resize"""
        from quickthumb import Canvas

        # given: overlapping shapes arranged to force a specific repair suggestion
        canvas = (
            Canvas(*canvas_size)
            .background(color="#FFFFFF")
            .shape(
                shape="rectangle",
                position=lower_position,
                width=lower_size[0],
                height=lower_size[1],
                color="#FF0000",
            )
            .shape(
                shape="rectangle",
                position=upper_position,
                width=upper_size[0],
                height=upper_size[1],
                color="#00FF00",
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        overlap_findings = [finding for finding in diagnostics if finding.code == "layer-overlap"]
        assert len(overlap_findings) == 1
        assert overlap_findings[0].severity == "warning"
        assert overlap_findings[0].layer_index == 2
        assert overlap_findings[0].message.endswith(expected_suggestion)

    def test_should_use_current_canvas_size_for_overlap_suggestions(self):
        """Overlap suggestions use canvas dimensions current at diagnose time"""
        from quickthumb import Canvas

        # given: a canvas resized wide enough to make a rightward overlap repair possible
        canvas = (
            Canvas(100, 100)
            .background(color="#FFFFFF")
            .shape(
                shape="rectangle",
                position=(20, 5),
                width=90,
                height=90,
                color="#FF0000",
            )
            .shape(
                shape="rectangle",
                position=(30, 10),
                width=80,
                height=80,
                color="#00FF00",
            )
        )
        canvas.width = 220

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [finding.code for finding in diagnostics] == ["layer-overlap"]
        assert diagnostics[0].message.endswith("move layer 2 to x=118 to clear the overlap")

    def test_should_warn_when_shape_fully_covers_shape(self):
        """A complete non-backdrop coverage overlap is still suspicious"""
        from quickthumb import Canvas

        # given: the upper shape fully covers the lower shape
        canvas = (
            Canvas(120, 120)
            .background(color="#FFFFFF")
            .shape(
                shape="rectangle",
                position=(20, 20),
                width=40,
                height=40,
                color="#FF0000",
            )
            .shape(
                shape="rectangle",
                position=(10, 10),
                width=80,
                height=80,
                color="#00FF00",
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [finding.code for finding in diagnostics] == ["layer-overlap", "layer-hidden"]
        assert "visible_overlap_pct=25% of upper, 100% of lower" in diagnostics[0].message

    def test_should_warn_when_large_shape_fully_covers_small_shape(self):
        """Complete coverage is suspicious even when the covering layer is much larger"""
        from quickthumb import Canvas

        # given: a large upper shape fully covers a tiny lower shape
        canvas = (
            Canvas(300, 300)
            .background(color="#FFFFFF")
            .shape(
                shape="rectangle",
                position=(100, 100),
                width=10,
                height=10,
                color="#FF0000",
            )
            .shape(
                shape="rectangle",
                position=(0, 0),
                width=250,
                height=250,
                color="#00FF00",
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [finding.code for finding in diagnostics] == ["layer-overlap", "layer-hidden"]
        assert "visible_overlap_pct=0% of upper, 100% of lower" in diagnostics[0].message

    def test_should_remeasure_alpha_masks_after_canvas_layers_change(self):
        """Repeated diagnoses do not reuse stale alpha masks for changed layers"""
        from quickthumb import Canvas

        # given: a canvas whose first pass caches a hollow ellipse corner mask
        canvas = (
            Canvas(200, 200)
            .background(color="#FFFFFF")
            .shape(
                shape="ellipse",
                position=(20, 20),
                width=80,
                height=80,
                color="#FF0000",
            )
            .shape(
                shape="rectangle",
                position=(20, 20),
                width=10,
                height=10,
                color="#00FF00",
            )
        )
        first_diagnostics = canvas.diagnose()

        # when: the same implicit layer IDs now point to overlapping opaque rectangles
        canvas.layers = [canvas.layers[0]]
        canvas.shape(
            shape="rectangle",
            position=(20, 20),
            width=80,
            height=80,
            color="#FF0000",
        )
        canvas.shape(
            shape="rectangle",
            position=(20, 20),
            width=10,
            height=10,
            color="#00FF00",
        )
        second_diagnostics = canvas.diagnose()

        # then
        assert first_diagnostics == []
        assert [finding.code for finding in second_diagnostics] == ["layer-overlap"]

    def test_should_warn_when_shape_covers_text(self):
        """Non-text layers covering text are suspicious, unlike text on a backdrop"""
        from quickthumb import Canvas

        # given: a shape later in render order covers an earlier text layer
        canvas = (
            Canvas(240, 180)
            .background(color="#FFFFFF")
            .text("Label", size=40, color="#000000", position=(20, 20))
            .shape(
                shape="rectangle",
                position=(15, 15),
                width=180,
                height=70,
                color="#00FF00",
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [finding.code for finding in diagnostics] == ["layer-overlap", "layer-hidden"]
        assert diagnostics[0].layer_index == 2
        assert "shape layer layer:2" in diagnostics[0].message
        assert "text layer layer:1" in diagnostics[0].message

    def test_should_not_warn_for_non_overlapping_layers(self):
        """Separated measured boxes do not produce overlap findings"""
        from quickthumb import Canvas

        # given: two visible shapes with a gap between their boxes
        canvas = (
            Canvas(240, 180)
            .background(color="#FFFFFF")
            .shape(
                shape="rectangle",
                position=(20, 20),
                width=60,
                height=60,
                color="#FF0000",
            )
            .shape(
                shape="rectangle",
                position=(100, 20),
                width=60,
                height=60,
                color="#00FF00",
            )
        )

        # when / then
        assert canvas.diagnose() == []

    def test_should_not_warn_for_touching_layer_edges(self):
        """Boxes whose edges touch without intersecting do not overlap"""
        from quickthumb import Canvas

        # given: two visible shapes with adjacent edges
        canvas = (
            Canvas(240, 180)
            .background(color="#FFFFFF")
            .shape(
                shape="rectangle",
                position=(20, 20),
                width=60,
                height=60,
                color="#FF0000",
            )
            .shape(
                shape="rectangle",
                position=(80, 20),
                width=60,
                height=60,
                color="#00FF00",
            )
        )

        # when / then
        assert canvas.diagnose() == []

    def test_should_not_warn_for_layers_separated_vertically(self):
        """Boxes with overlapping x-ranges but separated y-ranges do not overlap"""
        from quickthumb import Canvas

        # given: two visible shapes stacked with a gap between their boxes
        canvas = (
            Canvas(240, 180)
            .background(color="#FFFFFF")
            .shape(
                shape="rectangle",
                position=(20, 20),
                width=80,
                height=40,
                color="#FF0000",
            )
            .shape(
                shape="rectangle",
                position=(30, 80),
                width=80,
                height=40,
                color="#00FF00",
            )
        )

        # when / then
        assert canvas.diagnose() == []

    def test_should_ignore_invisible_overlapping_layers(self):
        """Transparent layers do not participate in overlap diagnostics"""
        from quickthumb import Canvas

        # given: an invisible top shape whose box intersects a visible lower shape
        canvas = (
            Canvas(200, 160)
            .background(color="#FFFFFF")
            .shape(
                shape="rectangle",
                position=(20, 20),
                width=80,
                height=60,
                color="#FF0000",
            )
            .shape(
                shape="rectangle",
                position=(40, 30),
                width=80,
                height=60,
                color="#00FF00",
                opacity=0,
            )
        )

        # when / then
        assert canvas.diagnose() == []

    def test_should_warn_when_grouped_text_overlaps_outer_text(self):
        """Grouped child measurements participate in z-order-aware overlap checks"""
        from quickthumb import Canvas

        # given: text inside a group and a later top-level text layer overlap
        canvas = (
            Canvas(360, 220)
            .background(color="#FFFFFF")
            .group(
                children=[
                    {
                        "type": "text",
                        "content": "Alpha",
                        "size": 48,
                        "color": "#000000",
                    }
                ],
                position=(20, 20),
            )
            .text("Beta", size=48, color="#000000", position=(50, 32))
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        overlap_findings = [finding for finding in diagnostics if finding.code == "layer-overlap"]
        assert len(overlap_findings) == 1
        assert overlap_findings[0].layer_index == 2
        assert "text layer layer:2 (order 2) overlaps text layer layer:1:0 (order 1)" in (
            overlap_findings[0].message
        )


class TestDiagnoseVisibility:
    """Test suite for visibility and platform-safe diagnostics"""

    def test_should_warn_when_layer_is_fully_hidden_by_later_opaque_layer(self):
        """A later opaque layer covering every visible pixel produces a layer-hidden warning"""
        from quickthumb import Canvas

        # given: a small shape entirely covered by a later opaque rectangle
        canvas = (
            Canvas(240, 180)
            .background(color="#FFFFFF")
            .shape(
                shape="rectangle",
                position=(80, 70),
                width=40,
                height=30,
                color="#FF0000",
            )
            .shape(
                shape="rectangle",
                position=(70, 60),
                width=80,
                height=60,
                color="#00FF00",
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        hidden = [finding for finding in diagnostics if finding.code == "layer-hidden"]
        assert len(hidden) == 1
        finding = hidden[0]
        assert finding.severity == "warning"
        assert finding.layer_index == 1
        assert finding.layer_id == "layer:1"
        assert finding.bbox is not None
        assert finding.bbox.model_dump() == {"x": 80, "y": 70, "width": 40, "height": 30}
        assert finding.related_layers == ["layer:1", "layer:2"]
        assert finding.measured == {
            "layer_type": "shape",
            "visible_area": 1200,
            "hidden_visible_pct": 1.0,
            "covering_layer_ids": ["layer:2"],
        }
        assert finding.suggestion == (
            "remove layer 1, move it above the covering layers, or move the covering layers"
        )

    def test_should_warn_when_later_layers_jointly_hide_a_layer(self):
        """Layer-hidden measures cumulative coverage from multiple later layers"""
        from quickthumb import Canvas

        # given: two later opaque rectangles that together cover a lower rectangle
        canvas = (
            Canvas(240, 180)
            .background(color="#FFFFFF")
            .shape(
                shape="rectangle",
                position=(80, 70),
                width=40,
                height=40,
                color="#FF0000",
            )
            .shape(
                shape="rectangle",
                position=(80, 70),
                width=20,
                height=40,
                color="#00FF00",
            )
            .shape(
                shape="rectangle",
                position=(100, 70),
                width=20,
                height=40,
                color="#0000FF",
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        hidden = [finding for finding in diagnostics if finding.code == "layer-hidden"]
        assert len(hidden) == 1
        assert hidden[0].layer_id == "layer:1"
        assert hidden[0].related_layers == ["layer:1", "layer:2", "layer:3"]

    def test_should_not_hide_layer_behind_translucent_cover(self):
        """Translucent later layers do not count as fully painting over a lower layer"""
        from quickthumb import Canvas

        # given: a lower layer geometrically covered by a translucent layer
        canvas = (
            Canvas(240, 180)
            .background(color="#FFFFFF")
            .shape(
                shape="rectangle",
                position=(80, 70),
                width=40,
                height=30,
                color="#FF0000",
            )
            .shape(
                shape="rectangle",
                position=(70, 60),
                width=80,
                height=60,
                color="#00FF00",
                opacity=0.5,
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert "layer-hidden" not in [finding.code for finding in diagnostics]

    def test_should_not_hide_layer_behind_transparent_shape_color(self):
        """Transparent RGBA shape colors do not count as visible or hidden coverage"""
        from quickthumb import Canvas

        # given: a transparent same-size shape over a visible lower shape
        canvas = (
            Canvas(100, 100)
            .shape(
                shape="rectangle",
                position=(20, 20),
                width=30,
                height=30,
                color="#FF0000",
            )
            .shape(
                shape="rectangle",
                position=(20, 20),
                width=30,
                height=30,
                color="#00000000",
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert diagnostics == []

    def test_should_not_hide_layer_behind_partially_transparent_shape_color(self):
        """Partially transparent RGBA shape colors may overlap but do not hide lower pixels"""
        from quickthumb import Canvas

        # given: a semi-transparent shape over a visible lower shape
        canvas = (
            Canvas(100, 100)
            .shape(
                shape="rectangle",
                position=(20, 20),
                width=30,
                height=30,
                color="#FF0000",
            )
            .shape(
                shape="rectangle",
                position=(20, 20),
                width=30,
                height=30,
                color="#00FF0080",
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [finding.code for finding in diagnostics] == ["layer-overlap"]

    def test_should_warn_when_later_opaque_background_hides_layer(self):
        """An opaque later background layer fully covers earlier visible layers"""
        from quickthumb import Canvas

        # given: a visible shape followed by a full-canvas solid background
        canvas = (
            Canvas(100, 100)
            .shape(
                shape="rectangle",
                position=(20, 20),
                width=30,
                height=30,
                color="#FF0000",
            )
            .background(color="#000000")
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [finding.code for finding in diagnostics] == ["layer-hidden"]
        assert diagnostics[0].related_layers == ["layer:0", "layer:1"]

    def test_should_not_hide_layer_behind_transparent_background_color(self):
        """Transparent RGBA background colors do not count as opaque full-canvas coverage"""
        from quickthumb import Canvas

        # given: a visible shape followed by a transparent full-canvas background
        canvas = (
            Canvas(100, 100)
            .shape(
                shape="rectangle",
                position=(20, 20),
                width=30,
                height=30,
                color="#FF0000",
            )
            .background(color="#00000000")
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert diagnostics == []

    def test_should_warn_when_later_opaque_gradient_background_hides_layer(self):
        """Opaque gradient backgrounds participate in layer-hidden diagnostics"""
        from quickthumb import Canvas, LinearGradient

        # given: a visible shape followed by an opaque full-canvas gradient background
        canvas = (
            Canvas(100, 100)
            .shape(
                shape="rectangle",
                position=(20, 20),
                width=30,
                height=30,
                color="#FF0000",
            )
            .background(
                gradient=LinearGradient(
                    angle=0,
                    stops=[("#000000", 0), ("#111111", 1)],
                )
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [finding.code for finding in diagnostics] == ["layer-hidden"]

    def test_should_warn_when_layer_crowds_default_safe_margin(self):
        """A layer inside the canvas but too near an edge produces edge-crowding"""
        from quickthumb import Canvas

        # given: a visible shape two pixels from the left edge on a 400px canvas
        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .shape(
                shape="rectangle",
                position=(2, 120),
                width=40,
                height=40,
                color="#FF0000",
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [finding.model_dump(mode="json", exclude_none=True) for finding in diagnostics] == [
            {
                "code": "edge-crowding",
                "severity": "warning",
                "layer_index": 1,
                "message": (
                    "shape layer layer:1 is too close to the left edge(s) of the safe area; "
                    "move layer 1 to x=4, y=120 to stay inside the safe area"
                ),
                "layer_id": "layer:1",
                "bbox": {"x": 2, "y": 120, "width": 40, "height": 40},
                "related_layers": ["layer:1"],
                "measured": {
                    "layer_type": "shape",
                    "platform": None,
                    "edges": ["left"],
                    "distances": {"left": 2, "top": 120, "right": 358, "bottom": 140},
                    "margins": {"top": 4, "right": 4, "bottom": 4, "left": 4},
                    "safe_bbox": {"x": 4, "y": 4, "width": 392, "height": 292},
                },
                "suggestion": "move layer 1 to x=4, y=120 to stay inside the safe area",
            }
        ]

    def test_should_report_edge_crowding_with_unrelated_text_warning(self):
        """Safe-area warnings are not suppressed by unrelated text diagnostics"""
        from quickthumb import Canvas

        # given: low-contrast text placed too close to the left edge
        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .text("ghost", size=40, color="#FFFFFF", position=(2, 120))
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [finding.code for finding in diagnostics] == ["low-contrast", "edge-crowding"]

    def test_should_apply_youtube_platform_overlay_diagnostics(self):
        """Canvas.for_platform enables preset dimensions, margins, and UI overlays"""
        from quickthumb import Canvas

        # given: a YouTube alias layer crossing the bottom-right duration badge overlay
        canvas = (
            Canvas.for_platform("youtube")
            .background(color="#FFFFFF")
            .shape(
                shape="rectangle",
                position=(1100, 620),
                width=90,
                height=20,
                color="#FF0000",
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        crowding = [finding for finding in diagnostics if finding.code == "edge-crowding"]
        assert len(crowding) == 1
        finding = crowding[0]
        assert canvas.platform == "youtube-thumbnail"
        assert finding.model_dump(include={"layer_index", "bbox", "measured"}) == {
            "layer_index": 1,
            "bbox": {"x": 1100, "y": 620, "width": 90, "height": 20},
            "measured": {
                "layer_type": "shape",
                "platform": "youtube-thumbnail",
                "overlay": "duration-badge",
                "overlay_label": "duration badge",
                "overlay_bbox": {"x": 1075, "y": 619, "width": 179, "height": 72},
                "overlap_bbox": {"x": 1100, "y": 620, "width": 90, "height": 20},
            },
        }

    def test_should_apply_youtube_shorts_platform_overlay_diagnostics(self):
        """Canvas.for_platform supports YouTube Shorts vertical safe overlays"""
        from quickthumb import Canvas

        # given: a Shorts layer crossing the right action rail without crowding the edge margin
        canvas = (
            Canvas.for_platform("youtube-shorts")
            .background(color="#FFFFFF")
            .shape(
                shape="rectangle",
                position=(930, 820),
                width=40,
                height=80,
                color="#FF0000",
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        crowding = [finding for finding in diagnostics if finding.code == "edge-crowding"]
        assert len(crowding) == 1
        finding = crowding[0]
        assert (canvas.width, canvas.height) == (1080, 1920)
        assert finding.model_dump(include={"layer_index", "bbox", "measured"}) == {
            "layer_index": 1,
            "bbox": {"x": 930, "y": 820, "width": 40, "height": 80},
            "measured": {
                "layer_type": "shape",
                "platform": "youtube-shorts",
                "overlay": "right-rail",
                "overlay_label": "right action rail",
                "overlay_bbox": {"x": 929, "y": 806, "width": 130, "height": 768},
                "overlap_bbox": {"x": 930, "y": 820, "width": 40, "height": 80},
            },
        }

    def test_should_normalize_platform_aliases_to_canonical_names(self):
        """Platform aliases keep old inputs while exposing canonical preset names"""
        from quickthumb import Canvas

        # given: legacy platform aliases
        youtube = Canvas.for_platform("youtube")
        instagram = Canvas.for_platform("instagram-reel")

        # when
        youtube_payload = json.loads(youtube.to_json())
        instagram_payload = json.loads(instagram.to_json())

        # then
        assert (
            youtube.platform,
            instagram.platform,
            youtube_payload,
            instagram_payload,
        ) == (
            "youtube-thumbnail",
            "instagram-reels",
            {"width": 1280, "height": 720, "layers": [], "platform": "youtube-thumbnail"},
            {"width": 1080, "height": 1920, "layers": [], "platform": "instagram-reels"},
        )


class TestDiagnoseMeasuredLayers:
    """Test suite for layer measurement paths used by diagnostics"""

    def test_should_expose_bbox_geometry_helpers(self):
        """BBox exposes reusable geometry helpers without tuple unpacking"""
        from quickthumb._measurements import BBox

        # given: two overlapping boxes
        first = BBox(x=10, y=20, width=30, height=40)
        second = BBox.from_points(35, 45, 65, 80)

        # when
        union = BBox.union([first, second])

        # then
        assert first.right == 40
        assert first.bottom == 60
        assert first.area == 1200
        assert not first.is_empty
        assert union == BBox(x=10, y=20, width=55, height=60)

    def test_should_measure_layers_with_stable_internal_contract(self):
        """measure_layers() returns deterministic LayerMeasurement objects"""
        from quickthumb import Canvas
        from quickthumb._measurements import BBox, measure_layers

        # given: a canvas with known shape geometry
        canvas = (
            Canvas(100, 100)
            .background(color="#FFFFFF")
            .shape(shape="rectangle", position=(10, 20), width=30, height=40, color="#FF0000")
        )

        # when
        measurements = measure_layers(canvas)

        # then
        background, shape = measurements
        assert background.index == 0
        assert background.order == 0
        assert background.layer_type == "unknown"
        assert background.bbox is None
        assert background.layer_id == "layer:0"
        assert background.name is None
        assert background.visible
        assert background.raw_layer is canvas.layers[0]
        assert background.metadata["measurable"] is False

        assert shape.index == 1
        assert shape.order == 1
        assert shape.z_order == 1
        assert shape.layer_type == "shape"
        assert shape.bbox == BBox(x=10, y=20, width=30, height=40)
        assert shape.layer_id == "layer:1"
        assert shape.raw_layer is canvas.layers[1]
        assert shape.metadata["shape"] == "rectangle"

    def test_should_measure_aligned_shape_for_off_canvas_detection(self):
        """Aligned shape bounds are diagnosed from their rendered top-left coordinate"""
        from quickthumb import Canvas

        # given: a centered shape whose aligned bounds cross the right edge
        canvas = (
            Canvas(100, 100)
            .background(color="#FFFFFF")
            .shape(
                shape="rectangle",
                position=(95, 50),
                width=20,
                height=20,
                color="#FF0000",
                align=("center", "middle"),
            )
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [finding.model_dump(mode="json", exclude_none=True) for finding in diagnostics] == [
            {
                "code": "off-canvas",
                "severity": "warning",
                "layer_index": 1,
                "message": (
                    "shape layer at (85, 40) size 20x20 extends past the edge of the 100x100 canvas"
                ),
                "layer_id": "layer:1",
                "bbox": {"x": 85, "y": 40, "width": 20, "height": 20},
                "related_layers": ["layer:1"],
                "measured": {
                    "layer_type": "shape",
                    "canvas_width": 100,
                    "canvas_height": 100,
                    "outside": "partially",
                },
                "suggestion": "move layer to x=90, y=50 to fit within the canvas",
            }
        ]

    def test_should_measure_text_for_off_canvas_detection(self):
        """Text bounds flow through the shared measurement path before diagnostics"""
        from quickthumb import Canvas
        from quickthumb._measurements import measure_layers

        # given: readable text positioned so its measured block crosses the right edge
        canvas = (
            Canvas(120, 80)
            .background(color="#FFFFFF")
            .text("wide", size=36, color="#000000", position=(100, 10))
        )

        # when
        diagnostics = canvas.diagnose()
        measurements = measure_layers(canvas)

        # then
        text_measurement = measurements[1]
        assert text_measurement.layer_type == "text"
        assert text_measurement.layer_id == "layer:1"
        assert text_measurement.raw_layer is canvas.layers[1]
        assert text_measurement.effective_text_layer is not None
        assert text_measurement.effective_text_layer.content == "wide"
        assert [finding.code for finding in diagnostics] == ["off-canvas"]
        assert diagnostics[0].severity == "warning"
        assert diagnostics[0].layer_index == 1
        assert diagnostics[0].message.startswith("text layer at (100, 10) size ")

    def test_should_not_diagnose_invisible_layers(self):
        """Invisible measured layers do not participate in diagnostics"""
        from quickthumb import Canvas
        from quickthumb._measurements import measure_layers

        # given: a transparent shape entirely outside the canvas
        canvas = Canvas(100, 100).shape(
            shape="rectangle",
            position=(150, 10),
            width=10,
            height=10,
            color="#FF0000",
            opacity=0,
        )

        # when
        diagnostics = canvas.diagnose()
        measurements = measure_layers(canvas)

        # then
        assert diagnostics == []
        assert measurements[0].visible is False

    def test_should_measure_image_with_intrinsic_aspect_ratio_for_off_canvas_detection(
        self, tmp_path
    ):
        """Image bounds use inferred dimensions when only one dimension is declared"""
        from quickthumb import Canvas

        # given: an 80x40 source image rendered 60px wide near the right edge
        fixture = tmp_path / "sample.png"
        Image.new("RGBA", (80, 40), (0, 255, 0, 255)).save(fixture)
        canvas = (
            Canvas(100, 100)
            .background(color="#FFFFFF")
            .image(path=str(fixture), position=(70, 20), width=60)
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [finding.model_dump(mode="json", exclude_none=True) for finding in diagnostics] == [
            {
                "code": "off-canvas",
                "severity": "warning",
                "layer_index": 1,
                "message": (
                    "image layer at (70, 20) size 60x30 extends past the edge of the 100x100 canvas"
                ),
                "layer_id": "layer:1",
                "bbox": {"x": 70, "y": 20, "width": 60, "height": 30},
                "related_layers": ["layer:1"],
                "measured": {
                    "layer_type": "image",
                    "canvas_width": 100,
                    "canvas_height": 100,
                    "outside": "partially",
                },
                "suggestion": "move layer to x=40, y=20 to fit within the canvas",
            }
        ]

    def test_should_measure_svg_layer_for_off_canvas_detection(self, monkeypatch):
        """SVG bounds use explicit dimensions in the shared measurement path"""
        from quickthumb import Canvas
        from quickthumb._images import ImageEngine

        # given: an explicitly sized svg layer crossing the right edge
        monkeypatch.setattr(ImageEngine, "render_svg_layer", lambda _self, _image, _layer: None)
        canvas = (
            Canvas(100, 100)
            .background(color="#FFFFFF")
            .svg(path=FIXTURE_SVG, position=(75, 10), width=40, height=20)
        )

        # when
        diagnostics = canvas.diagnose()

        # then
        assert [finding.model_dump(mode="json", exclude_none=True) for finding in diagnostics] == [
            {
                "code": "off-canvas",
                "severity": "warning",
                "layer_index": 1,
                "message": (
                    "svg layer at (75, 10) size 40x20 extends past the edge of the 100x100 canvas"
                ),
                "layer_id": "layer:1",
                "bbox": {"x": 75, "y": 10, "width": 40, "height": 20},
                "related_layers": ["layer:1"],
                "measured": {
                    "layer_type": "svg",
                    "canvas_width": 100,
                    "canvas_height": 100,
                    "outside": "partially",
                },
                "suggestion": "move layer to x=60, y=10 to fit within the canvas",
            }
        ]

    def test_should_measure_group_text_children_for_legibility_diagnostics(self):
        """Placed text inside groups keeps the parent layer index for diagnostics"""
        from quickthumb import Canvas
        from quickthumb._measurements import BBox, measure_layers

        # given: white group text over a white background
        canvas = (
            Canvas(200, 120)
            .background(color="#FFFFFF")
            .group(
                children=[{"type": "text", "content": "ghost", "size": 36, "color": "#FFFFFF"}],
                position=(10, 10),
            )
        )

        # when
        diagnostics = canvas.diagnose()
        measurements = measure_layers(canvas)

        # then
        assert [finding.code for finding in diagnostics] == ["low-contrast"]
        assert diagnostics[0].layer_index == 1
        group = measurements[1]
        assert group.layer_type == "group"
        assert group.layer_id == "layer:1"
        assert len(group.children) == 1
        assert group.bbox == group.children[0].bbox
        assert group.children[0].layer_id == "layer:1:0"
        assert group.children[0].layer_type == "text"
        assert isinstance(group.metadata["layout_bbox"], BBox)


class TestDiagnoseValidation:
    """Test suite for diagnose() error behavior"""

    def test_should_raise_for_missing_image_files(self):
        """diagnose() validates referenced asset paths like render() does"""
        from quickthumb import Canvas

        canvas = Canvas(200, 200).image(path="no/such/image.png", position=(0, 0))

        with pytest.raises(FileNotFoundError, match="no/such/image.png"):
            canvas.diagnose()
