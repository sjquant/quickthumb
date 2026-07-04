"""Tests for canvas diagnostics (canvas.diagnose())"""

from pathlib import Path

import pytest
from inline_snapshot import snapshot
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
        from quickthumb.models import Diagnostic

        assert diagnostics == snapshot(
            [
                Diagnostic(
                    code="off-canvas",
                    severity="warning",
                    layer_index=1,
                    message=(
                        "shape layer at (180, 180) size 50x50 extends past the edge "
                        "of the 200x200 canvas"
                    ),
                )
            ]
        )

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
        from quickthumb.models import Diagnostic

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
        assert diagnostics == snapshot(
            [
                Diagnostic(
                    code="layer-overlap",
                    severity="warning",
                    layer_index=2,
                    message=(
                        "shape layer layer:2 (order 2) overlaps shape layer layer:1 "
                        "(order 1); bbox_overlap=1600px "
                        "(bbox_overlap_pct=40% of upper, 27% of lower), "
                        "visible_overlap=1600px "
                        "(visible_overlap_pct=40% of upper, 27% of lower); "
                        "move layer 2 to y=88 to clear the overlap"
                    ),
                )
            ]
        )

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
        assert [finding.code for finding in diagnostics] == ["layer-overlap"]
        assert diagnostics[0].severity == "warning"
        assert diagnostics[0].layer_index == 2
        assert diagnostics[0].message.endswith(expected_suggestion)

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
        assert [finding.code for finding in diagnostics] == ["layer-overlap"]
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
        assert [finding.code for finding in diagnostics] == ["layer-overlap"]
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
        assert [finding.code for finding in diagnostics] == ["layer-overlap"]
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
        from quickthumb.models import Diagnostic

        assert diagnostics == snapshot(
            [
                Diagnostic(
                    code="off-canvas",
                    severity="warning",
                    layer_index=1,
                    message=(
                        "shape layer at (85, 40) size 20x20 extends past the edge "
                        "of the 100x100 canvas"
                    ),
                )
            ]
        )

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
        from quickthumb.models import Diagnostic

        assert diagnostics == snapshot(
            [
                Diagnostic(
                    code="off-canvas",
                    severity="warning",
                    layer_index=1,
                    message=(
                        "image layer at (70, 20) size 60x30 extends past the edge "
                        "of the 100x100 canvas"
                    ),
                )
            ]
        )

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
        from quickthumb.models import Diagnostic

        assert diagnostics == snapshot(
            [
                Diagnostic(
                    code="off-canvas",
                    severity="warning",
                    layer_index=1,
                    message=(
                        "svg layer at (75, 10) size 40x20 extends past the edge "
                        "of the 100x100 canvas"
                    ),
                )
            ]
        )

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
