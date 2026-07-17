"""Tests for HTML export (Canvas.to_html / Deck.to_html and rendering to .html)."""

import base64
import json
import re
import subprocess
from html import unescape
from importlib.resources import files
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from quickthumb import (
    Blinds,
    Box,
    Canvas,
    Checkerboard,
    Circle,
    Deck,
    Diamond,
    Dissolve,
    Fade,
    FitMode,
    LinearGradient,
    RadialGradient,
    TextPart,
    Wheel,
    Wipe,
)
from quickthumb._export_base import font_face_declarations
from quickthumb.errors import RenderingError
from quickthumb.models import BackdropBlur, Background, Shadow, Stroke, TextFillImage

from tests._helpers import pixel_channel

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_IMAGE = str(FIXTURES_DIR / "sample_image.jpg")
SAMPLE_SVG = str(FIXTURES_DIR / "sample.svg")


def stage_style(html: str) -> str:
    """Return the inline style of the (first) stage element."""
    match = re.search(r'class="qt-stage"[^>]*style="([^"]*)"', html)
    assert match is not None, "no qt-stage found"
    return match.group(1)


def timelines(html: str) -> list[list[dict]]:
    """Parse every stage's animation timeline JSON."""
    return [json.loads(unescape(raw)) for raw in re.findall(r"data-qt-timeline='([^']*)'", html)]


def first_embedded_png(html: str) -> Image.Image:
    """Decode the first embedded PNG data URL in an exported HTML document."""
    match = re.search(r"data:image/png;base64,([^\"']+)", html)
    assert match is not None
    return Image.open(BytesIO(base64.b64decode(match.group(1)))).convert("RGBA")


class TestHtmlDocument:
    """Test suite for overall HTML document structure"""

    def test_should_emit_standalone_document_with_stage_dimensions(self):
        """Exported HTML is a full document whose stage carries the canvas size"""
        # given
        canvas = Canvas(640, 360).background(color="#112233")

        # when
        html = canvas.to_html()

        # then
        assert html.startswith("<!doctype html>")
        assert "</html>" in html
        assert "width:640px;height:360px" in stage_style(html)

    def test_should_inline_html_assets_without_external_dependencies(self):
        """Exported HTML embeds packaged CSS and JS instead of linking assets"""
        # given
        canvas = Canvas(640, 360).background(color="#112233")

        # when
        html = canvas.to_html()

        # then
        assert "<style>\n" in html
        assert "<script>\n" in html
        assert "function qtTimeline(stage)" in html
        assert "<link" not in html
        assert "<script src" not in html

    def test_should_load_static_html_assets_as_package_resources(self):
        """Static exporter assets are available through importlib.resources"""
        # given
        resource_names = [
            "base.css",
            "fixed.css",
            "fixed_deck.css",
            "presenter.css",
            "timeline.js",
            "canvas_runtime.js",
            "deck_runtime.js",
            "document.html",
        ]

        # when
        contents = [
            files("quickthumb.html").joinpath(resource_name).read_text(encoding="utf-8")
            for resource_name in resource_names
        ]

        # then
        assert all(content for content in contents)
        assert "{{#stage}}" in contents[-1]

    def test_should_render_html_file_from_extension(self, tmp_path):
        """render() writes an HTML document when the output path ends in .html"""
        # given
        canvas = Canvas(200, 100).background(color="#FF0000")
        output = tmp_path / "out.html"

        # when
        canvas.render(str(output))

        # then
        content = output.read_text()
        assert content.startswith("<!doctype html>")
        assert "qt-stage" in content

    def test_should_render_htm_extension_too(self, tmp_path):
        """The .htm extension is treated the same as .html"""
        # given
        canvas = Canvas(200, 100).background(color="#FF0000")
        output = tmp_path / "out.htm"

        # when
        canvas.render(str(output))

        # then
        assert output.read_text().startswith("<!doctype html>")

    def test_should_reject_quality_for_html_output(self, tmp_path):
        """Quality only applies to JPEG/WEBP, so .html output raises RenderingError"""
        # given
        canvas = Canvas(200, 100).background(color="#FF0000")

        # when / then
        with pytest.raises(RenderingError, match="[Qq]uality"):
            canvas.render(str(tmp_path / "out.html"), quality=80)

    def test_should_scale_to_fit_when_responsive(self):
        """A responsive document includes the fitting frame and scale runtime"""
        # given
        canvas = Canvas(640, 360).background(color="#112233")

        # when
        html = canvas.to_html(responsive=True)

        # then
        assert "qt-frame" in html
        assert "ResizeObserver" in html

    def test_should_center_responsive_stage_while_scaling(self):
        """A responsive stage is centered before viewport scaling is applied"""
        # given
        canvas = Canvas(640, 360).background(color="#112233")

        # when
        html = canvas.to_html(responsive=True)

        # then
        assert ".qt-stage{position:absolute;left:50%;top:50%" in html
        assert "stage.style.setProperty('--qt-stage-x','-50%')" in html
        assert "translate(var(--qt-stage-x),var(--qt-stage-y)) scale(" in html

    def test_should_emit_bare_stage_when_not_responsive(self):
        """A non-responsive document drops the fitting frame and scaling"""
        # given
        canvas = Canvas(640, 360).background(color="#112233")

        # when
        html = canvas.to_html(responsive=False)

        # then
        assert "qt-frame" not in html
        assert "var fit=false" in html

    def test_should_overlap_deck_stages_when_not_responsive(self):
        """A non-responsive deck still overlaps stages for slide transitions"""
        # given
        from quickthumb.transitions import Push

        deck = (
            Deck(320, 180)
            .slide(Canvas().background(color="#101820"))
            .slide(Canvas().background(color="#1E293B"), transition=Push())
        )

        # when
        html = deck.to_html(responsive=False)

        # then
        assert "qt-frame" not in html
        assert ".qt-stage{position:absolute" in html
        assert "if(!fit){settle()" not in html


class TestHtmlBackgrounds:
    """Test suite for background layer export"""

    def test_should_emit_solid_color_background(self):
        """A solid background becomes a full-stage div with the color"""
        # given
        canvas = Canvas(400, 300).background(color="#FF8800")

        # when
        html = canvas.to_html()

        # then
        assert "width:400px;height:300px;background:rgb(255,136,0)" in html

    def test_should_emit_linear_gradient_background(self):
        """A gradient background becomes a CSS linear-gradient"""
        # given
        canvas = Canvas(400, 300).background(
            gradient=LinearGradient(angle=90, stops=[("#000000", 0.0), ("#FFFFFF", 1.0)])
        )

        # when
        html = canvas.to_html()

        # then
        assert "linear-gradient(180deg," in html
        # The raster engine ramps the gradient across the box diagonal and crops,
        # so a 400x300 vertical gradient shows only the middle 300/500 of the
        # range. The CSS stops are pushed outside [0,100%] to reproduce exactly
        # that slice instead of stretching the full range over the box.
        assert "rgb(0,0,0) -33.33%" in html
        assert "rgb(255,255,255) 133.33%" in html

    def test_should_emit_radial_gradient_background(self):
        """A radial gradient background becomes a CSS radial-gradient"""
        # given
        canvas = Canvas(400, 300).background(
            gradient=RadialGradient(
                center=(0.25, 0.75),
                stops=[("#000000", 0.0), ("#FFFFFF", 1.0)],
            )
        )

        # when
        html = canvas.to_html()

        # then
        assert "radial-gradient(circle 530.33px at 100px 225px," in html
        assert "rgb(0,0,0) 0px" in html
        assert "rgb(255,255,255) 530.33px" in html

    def test_should_rasterize_background_with_effects(self):
        """A background with filter effects falls back to an embedded PNG"""
        # given
        from quickthumb.models import Filter

        canvas = Canvas(200, 100).background(color="#202020", effects=[Filter(blur=4)])

        # when
        html = canvas.to_html()

        # then
        assert "data:image/png;base64," in html


class TestHtmlOutline:
    """Test suite for outline layer export"""

    def test_should_emit_outline_as_inset_border(self):
        """An outline becomes a border-box div with a solid border"""
        # given
        canvas = Canvas(400, 300).outline(width=10, color="#22C55E")

        # when
        html = canvas.to_html()

        # then
        assert "box-sizing:border-box" in html
        assert "border:10px solid rgb(34,197,94)" in html


class TestHtmlShapes:
    """Test suite for shape layer export"""

    def test_should_emit_rectangle_with_border_radius(self):
        """A rounded rectangle becomes a div with border-radius"""
        # given
        canvas = Canvas(400, 300).shape(
            shape="rectangle",
            position=(20, 20),
            width=120,
            height=60,
            color="#CC0000",
            border_radius=12,
        )

        # when
        html = canvas.to_html()

        # then
        assert "border-radius:12px" in html
        assert "background:rgb(204,0,0)" in html

    def test_should_emit_ellipse_as_full_radius(self):
        """An ellipse becomes a div with border-radius:50%"""
        # given
        canvas = Canvas(400, 300).shape(
            shape="ellipse", position=(20, 20), width=120, height=60, color="#CC0000"
        )

        # when / then
        assert "border-radius:50%" in canvas.to_html()

    def test_should_emit_polygon_as_clip_path(self):
        """A star/polygon becomes a clip-path polygon"""
        # given
        canvas = Canvas(400, 300).shape(
            shape="star",
            position=(20, 20),
            width=100,
            height=100,
            color="#FFD700",
        )

        # when / then
        assert "clip-path:polygon(" in canvas.to_html()

    def test_should_fall_back_to_raster_for_masked_shape(self):
        """Masked shapes become PNG fragments so HTML preserves the composition"""
        # given
        canvas = Canvas(80, 80).shape(
            shape="rectangle",
            position=(10, 10),
            width=60,
            height=60,
            color="#FF0000",
            mask={"shape": "ellipse", "position": (10, 10), "width": 60, "height": 60},
        )

        # when
        html = canvas.to_html()

        # then
        assert "data:image/png;base64," in html
        assert "background:rgb(255,0,0)" not in html
        embedded = first_embedded_png(html)
        assert embedded.getpixel((embedded.width // 2, embedded.height // 2)) == (255, 0, 0, 255)
        assert pixel_channel(embedded, (0, 0), 3) == 0

    def test_should_fall_back_to_raster_for_backdrop_blur_shape(self, tmp_path):
        """Backdrop-blur shapes become PNG fragments so HTML preserves the effect"""
        # given
        no_blur = (
            Canvas(80, 50)
            .shape(shape="rectangle", position=(0, 0), width=40, height=50, color="#FF0000")
            .shape(shape="rectangle", position=(40, 0), width=40, height=50, color="#0000FF")
            .shape(
                shape="rectangle",
                position=(30, 5),
                width=20,
                height=40,
                color="#FFFFFF40",
            )
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

        # when
        control_output = tmp_path / "control.png"
        no_blur.render(str(control_output))
        control = Image.open(control_output).convert("RGBA")
        html = with_blur.to_html()

        # then
        assert "data:image/png;base64," in html
        embedded = first_embedded_png(html)
        assert pixel_channel(embedded, (36, 25), 2) - pixel_channel(control, (36, 25), 2) >= 10


class TestHtmlText:
    """Test suite for text layer export"""

    def test_should_emit_text_as_span_with_color(self):
        """A simple text layer becomes a positioned span with the fill color"""
        # given
        canvas = Canvas(400, 200).text(content="Hello", size=48, color="#FF0000", position=(20, 20))

        # when
        html = canvas.to_html()

        # then
        assert "<span" in html
        assert ">Hello</span>" in html
        assert "color:rgb(255,0,0)" in html

    def test_should_emit_rich_text_parts_as_separate_spans(self):
        """Each TextPart becomes its own colored span"""
        # given
        canvas = Canvas(600, 200).text(
            content=[TextPart(text="HOT", color="#FF4500"), TextPart(text="COLD", color="#00BFFF")],
            size=48,
            position=(20, 20),
        )

        # when
        html = canvas.to_html()

        # then
        assert ">HOT</span>" in html
        assert ">COLD</span>" in html
        assert "color:rgb(255,69,0)" in html
        assert "color:rgb(0,191,255)" in html

    def test_should_emit_resolved_variations_and_emoji_style_per_span(self):
        """HTML spans preserve inherited and explicitly cleared font settings"""
        # given: a layer-level variable font and color-emoji setting
        canvas = Canvas(600, 200).text(
            content=[
                TextPart(text="wide "),
                TextPart(text="plain", font_variations={}, emoji_style="monochrome"),
            ],
            font="assets/fonts/RobotoFlex-Variable.ttf",
            font_variations={"wdth": 25},
            emoji_style="color",
            size=40,
            position=(20, 60),
        )

        # when: exporting native HTML text
        html = canvas.to_html()
        spans = re.findall(r'<span style="([^"]*)">(wide |plain)</span>', html)

        # then: inherited values apply only to the first span and explicit defaults clear them
        assert len(spans) == 2
        assert "font-variation-settings:'wdth' 25;" in spans[0][0]
        assert "font-variant-emoji:emoji;" in spans[0][0]
        assert "font-variation-settings" not in spans[1][0]
        assert "font-variant-emoji:text;" in spans[1][0]

    def test_should_apply_stroke_and_shadow_effects(self):
        """Stroke maps to -webkit-text-stroke; shadow to an SVG blur+offset filter"""
        # given
        canvas = Canvas(400, 200).text(
            content="FX",
            size=64,
            color="#FFFFFF",
            position=(20, 20),
            effects=[
                Stroke(width=3, color="#000000"),
                Shadow(offset_x=2, offset_y=2, color="#000000", blur_radius=4),
            ],
        )

        # when
        html = canvas.to_html()

        # then
        assert "-webkit-text-stroke:3px rgb(0,0,0)" in html
        # The shadow is an SVG filter (Gaussian sigma == PIL blur radius, no CSS fudge).
        assert "filter:url(#qt-fx" in html
        assert '<feGaussianBlur in="SourceAlpha" stdDeviation="4"' in html
        assert '<feOffset in="b1" dx="2" dy="2"' in html

    def test_should_apply_gradient_fill_via_background_clip(self):
        """A gradient text fill clips a CSS gradient to the glyphs"""
        # given
        canvas = Canvas(600, 200).text(
            content="GRAD",
            size=64,
            fill=LinearGradient(angle=90, stops=[("#FF6B6B", 0.0), ("#4ECDC4", 1.0)]),
            position=(20, 20),
        )

        # when
        html = canvas.to_html()

        # then
        assert "background-clip:text" in html
        assert "color:transparent" in html

    def test_should_apply_radial_gradient_fill_via_background_clip(self):
        """A radial gradient text fill clips a CSS radial-gradient to the glyphs"""
        # given
        canvas = Canvas(600, 200).text(
            content="RAD",
            size=64,
            fill=RadialGradient(
                center=(0.5, 0.5),
                stops=[("#FF6B6B", 0.0), ("#4ECDC4", 1.0)],
            ),
            position=(20, 20),
        )

        # when
        html = canvas.to_html()

        # then
        assert "background-clip:text" in html
        assert "color:transparent" in html
        assert "radial-gradient(circle" in html

    def test_should_rasterize_image_filled_text(self):
        """Image-filled glyphs fall back to an embedded PNG fragment"""
        # given
        canvas = Canvas(400, 200).text(
            content="IMG",
            size=64,
            fill=TextFillImage(path=SAMPLE_IMAGE, fit=FitMode.COVER),
            position=(20, 20),
        )

        # when / then
        assert "data:image/png;base64," in canvas.to_html()

    def test_should_emit_text_background_effect(self):
        """A Background text effect becomes a div behind the glyphs"""
        # given
        canvas = Canvas(400, 200).text(
            content="BG",
            size=48,
            color="#FFFFFF",
            position=(20, 20),
            effects=[Background(color="#111827", padding=(8, 12), border_radius=6)],
        )

        # when
        html = canvas.to_html()

        # then
        assert "background:rgb(17,24,39)" in html
        assert "border-radius:6px" in html


class TestHtmlImages:
    """Test suite for image layer export"""

    def test_should_embed_image_layer_as_png_fragment(self):
        """An image layer is embedded as a base64 PNG img element"""
        # given
        canvas = Canvas(400, 300).image(path=SAMPLE_IMAGE, position=(10, 10), width=120, height=80)

        # when
        html = canvas.to_html()

        # then
        assert "<img" in html
        assert "data:image/png;base64," in html

    def test_should_embed_svg_layer_natively(self):
        """An SVG layer is inlined as an svg+xml data URL"""
        # given
        canvas = Canvas(400, 300).svg(path=SAMPLE_SVG, position=(10, 10), width=80)

        # when / then
        assert "data:image/svg+xml;base64," in canvas.to_html()


class TestHtmlFonts:
    """Test suite for font embedding"""

    def test_should_embed_fonts_as_font_face(self):
        """embed_fonts inlines the used font as an @font-face data URL"""
        # given
        canvas = Canvas(400, 200).text(content="Type", size=48, color="#FFFFFF", position=(20, 20))

        # when
        html = canvas.to_html(embed_fonts=True)

        # then
        assert "@font-face" in html
        assert "data:font/ttf;base64," in html

    def test_should_embed_fonts_by_default(self):
        """The document embeds its fonts by default so it renders identically everywhere"""
        # given
        canvas = Canvas(400, 200).text(content="Type", size=48, color="#FFFFFF", position=(20, 20))

        # when / then
        assert "@font-face" in canvas.to_html()

    def test_should_omit_font_face_when_embed_disabled(self):
        """embed_fonts=False references families but embeds no font data"""
        # given
        canvas = Canvas(400, 200).text(content="Type", size=48, color="#FFFFFF", position=(20, 20))

        # when / then
        assert "@font-face" not in canvas.to_html(embed_fonts=False)

    def test_should_escape_embedded_font_family_names(self, tmp_path):
        """Embedded font-family CSS cannot escape the surrounding style element"""
        # given
        font_path = tmp_path / "bad.ttf"
        font_path.write_bytes(b"font")
        family = "Bad'\"&</style><script>alert(1)</script>"

        # when
        css = font_face_declarations({str(font_path): (family, "400", "normal")})

        # then
        assert "@font-face" in css
        assert "</style" not in css.lower()
        assert "<script" not in css.lower()
        assert "\\22 " in css
        assert "\\26 " in css
        assert "\\3C /style\\3E " in css


class TestHtmlAnimations:
    """Test suite for per-layer animation export"""

    def test_should_emit_keyframes_and_timeline_for_animation(self):
        """An animated layer registers a keyframe and a timeline node"""
        # given
        canvas = Canvas(400, 200).text(
            content="Hi", size=48, color="#FFFFFF", position=(20, 20), animation=Fade()
        )

        # when
        html = canvas.to_html()

        # then
        assert "@keyframes qt-k" in html
        nodes = timelines(html)[0]
        assert len(nodes) == 1
        assert nodes[0]["tr"] == "on_click"
        assert nodes[0]["a"] == "entrance"

    def test_should_start_entrance_layers_hidden(self):
        """An entrance animation hides the element until its node plays"""
        # given
        canvas = Canvas(400, 200).text(
            content="Hi", size=48, color="#FFFFFF", position=(20, 20), animation=Fade()
        )

        # when / then
        assert "visibility:hidden" in canvas.to_html()

    def test_should_preserve_animated_layer_opacity_through_entrance(self):
        """Entrance animation uses and restores the element's original opacity"""
        # given
        canvas = Canvas(400, 200).shape(
            shape="ellipse",
            position=(20, 20),
            width=80,
            height=80,
            color="#22D3EE",
            opacity=0.15,
            animation=Fade(),
        )

        # when
        html = canvas.to_html()

        # then
        assert "to{opacity:var(--qt-opacity,1)}" in html
        assert "var origOpacity={};" in html
        assert "origOpacity[id]=elMap[id].style.opacity;" in html
        assert "elMap[id].style.setProperty('--qt-opacity',origOpacity[id]||'1');" in html
        assert "el.style.opacity=origOp;" in html
        assert "el.style.opacity=origOpacity[id]||'';" in html

    @pytest.mark.parametrize(
        "animation",
        [
            Fade(),
            Box(),
            Wipe(),
            Blinds(),
            Checkerboard(),
            Circle(),
            Diamond(),
            Dissolve(),
            Wheel(),
        ],
    )
    def test_should_apply_original_layer_opacity_during_each_entrance_effect(self, animation):
        """Every entrance effect animates toward the layer's original opacity"""
        # given
        canvas = Canvas(400, 200).shape(
            shape="ellipse",
            position=(20, 20),
            width=80,
            height=80,
            color="#22D3EE",
            opacity=0.25,
            animation=animation,
        )

        # when
        html = canvas.to_html()

        # then
        keyframes = re.findall(r"@keyframes qt-k\d+\{[^}]+\}(?:to\{[^}]+\})?", html)
        assert keyframes
        assert all("opacity:var(--qt-opacity,1)" in keyframe for keyframe in keyframes)
        assert all("opacity:1" not in keyframe for keyframe in keyframes)

    def test_should_emit_soft_center_reveal_for_box_animation(self):
        """Box entrance uses an oval mask instead of a hard rectangular crop"""
        # given
        canvas = Canvas(400, 200).text(
            content="Hi", size=48, color="#FFFFFF", position=(20, 20), animation=Box()
        )

        # when
        html = canvas.to_html()

        # then
        assert "clip-path:ellipse(0% 0% at 50% 50%)" in html
        assert "clip-path:ellipse(75% 75% at 50% 50%)" in html

    def test_should_emit_one_node_per_effect_in_a_list(self):
        """A list of effects on one layer becomes one timeline node each"""
        # given
        canvas = Canvas(400, 200).text(
            content="Hi",
            size=48,
            color="#FFFFFF",
            position=(20, 20),
            animation=[Box(direction="in"), Wipe(animate="exit", trigger="after_previous")],
        )

        # when
        nodes = timelines(canvas.to_html())[0]

        # then
        assert len(nodes) == 2
        assert nodes[1]["tr"] == "after_previous"
        assert nodes[1]["a"] == "exit"

    def test_should_omit_timeline_for_static_canvas(self):
        """A canvas with no animations carries an empty timeline"""
        # given
        canvas = Canvas(400, 200).text(content="Hi", size=48, color="#FFFFFF", position=(20, 20))

        # when / then
        assert timelines(canvas.to_html())[0] == []

    def test_should_reject_animated_layers_that_would_be_flattened(self):
        """Animated layers are rejected before blend-mode rasterization swallows them"""
        # given
        canvas = (
            Canvas(400, 200)
            .text(content="Hi", size=48, color="#FFFFFF", position=(20, 20), animation=Fade())
            .image(SAMPLE_IMAGE, position=(0, 0), width=80, height=80, blend_mode="multiply")
        )

        # when / then
        with pytest.raises(RenderingError, match="cannot animate layers"):
            canvas.to_html()


class TestDeckHtml:
    """Test suite for deck slideshow export"""

    def test_should_emit_one_stage_per_slide(self):
        """A deck becomes a document with a stage per slide"""
        # given
        deck = (
            Deck(640, 360)
            .slide(Canvas().background(color="#101820"))
            .slide(Canvas().background(color="#1E293B"))
        )

        # when
        html = deck.to_html()

        # then
        assert html.count('class="qt-stage"') == 2
        assert 'data-qt-slide-index="0"' in html
        assert 'data-qt-slide-index="1"' in html
        assert re.search(
            r'data-qt-slide-index="1"[^>]* hidden style="width:640px;height:360px;display:none;"',
            html,
        )
        # Each slide carries its own enter-transition animation (a cross-fade by
        # default), wired through a data attribute the runtime reads on show().
        assert html.count("data-qt-transition=") == 2
        assert "@keyframes qt-t0{from{opacity:0}to{opacity:1}}" in html
        assert "function go(i,backward,restoreCursor)" in html
        assert "<script src" not in html

    def test_should_namespace_persisted_state_by_document_content(self):
        """Different decks receive different reload-state identities."""
        # given: two decks served from the same origin and path
        first = Deck(640, 360).slide(Canvas().background(color="#101820"))
        second = Deck(640, 360).slide(Canvas().background(color="#1E293B"))

        # when: both decks are exported
        first_match = re.search(r'data-qt-state-id="([^"]+)"', first.to_html())
        second_match = re.search(r'data-qt-state-id="([^"]+)"', second.to_html())
        assert first_match is not None and second_match is not None
        first_id = first_match.group(1)
        second_id = second_match.group(1)

        # then: a reload state cannot leak between the two documents
        assert first_id != second_id

    def test_should_embed_query_selected_presenter_view_with_speaker_notes(self):
        """Deck HTML activates a current/next presenter dashboard for ?presenter."""
        # given: a deck whose first slide carries private speaker notes
        deck = (
            Deck(640, 360)
            .slide(Canvas().background(color="#101820"), notes="Open with the key metric.")
            .slide(Canvas().background(color="#1E293B"))
        )

        # when: the deck is exported to standalone HTML
        html = deck.to_html(embed_fonts=False)

        # then: notes and the self-contained presenter UI/runtime are embedded
        assert 'data-qt-notes="Open with the key metric."' in html
        assert "get('presenter')" in html
        assert "qt-presenter-shell" in html
        assert "Speaker notes" in html
        assert "Open audience view" in html
        assert "window.BroadcastChannel" in html

    def test_should_escape_speaker_notes_in_stage_attributes(self):
        """Speaker notes cannot escape their stage attribute into executable markup."""
        # given: notes containing HTML-significant characters
        deck = Deck(320, 180).slide(
            Canvas().background(color="#101820"),
            notes='Say "hello" </div><script>alert(1)</script>',
        )

        # when: the deck is exported
        html = deck.to_html(embed_fonts=False)

        # then: the notes remain inert attribute text
        assert 'data-qt-notes="Say &quot;hello&quot; &lt;/div&gt;&lt;script&gt;' in html
        assert "<script>alert(1)</script>" not in html

    def test_should_animate_slides_with_their_transition(self):
        """A slide's transition drives the CSS animation the deck plays into it"""
        # given
        from quickthumb.transitions import Cut, Push

        deck = (
            Deck(640, 360)
            .slide(Canvas().background(color="#101820"))
            .slide(
                Canvas().background(color="#1E293B"),
                transition=Push(direction="left", duration=0.8),
            )
            .slide(Canvas().background(color="#334155"), transition=Cut())
        )

        # when
        html = deck.to_html()

        # then
        # Push slides the incoming stage in from the edge, composed with the fit scale.
        assert (
            "transform:translate(var(--qt-stage-x,0),var(--qt-stage-y,0)) "
            "translateX(100vw) scale(var(--qt-scale,1))"
        ) in html
        assert 'data-qt-transition="qt-t1 0.80s ease both"' in html
        # A hard cut emits no keyframe and no animation.
        assert 'data-qt-transition=""' in html

    @pytest.mark.parametrize(
        ("transition", "expected"),
        [
            pytest.param(
                ("wipe", {"direction": "right"}),
                "clip-path:inset(0 100% 0 0)",
                id="wipe",
            ),
            pytest.param(("cover", {"direction": "left"}), "translateX(100vw)", id="cover"),
            pytest.param(("uncover", {"direction": "up"}), "translateY(-100vh)", id="uncover"),
            pytest.param(("zoom", {"direction": "out"}), "var(--qt-scale,1)*1.4", id="zoom"),
            pytest.param(("split", {"orientation": "vertical"}), "inset(50% 0 50% 0)", id="split"),
            pytest.param(
                ("split", {"orientation": "horizontal"}),
                "inset(0 50% 0 50%)",
                id="split-horizontal",
            ),
            pytest.param(
                ("blinds", {"orientation": "vertical"}),
                "clip-path:inset(0 100% 0 0)",
                id="blinds-vertical",
            ),
            pytest.param(
                ("blinds", {"orientation": "horizontal"}),
                "clip-path:inset(0 0 100% 0)",
                id="blinds-horizontal",
            ),
            pytest.param(
                ("comb", {"orientation": "vertical"}),
                "clip-path:inset(0 0 0 100%)",
                id="comb-vertical",
            ),
            pytest.param(
                ("comb", {"orientation": "horizontal"}),
                "clip-path:inset(100% 0 0 0)",
                id="comb-horizontal",
            ),
            pytest.param(
                ("newsflash", {}),
                "rotate(-180deg) scale(calc(var(--qt-scale,1)*0.1))",
                id="newsflash",
            ),
            pytest.param(("circle", {}), "clip-path:circle(0% at 50% 50%)", id="circle"),
            pytest.param(("wheel", {}), "clip-path:circle(0% at 50% 50%)", id="wheel"),
            pytest.param(("wedge", {}), "clip-path:circle(0% at 50% 50%)", id="wedge"),
            pytest.param(
                ("diamond", {}),
                "clip-path:polygon(50% 50%,50% 50%,50% 50%,50% 50%)",
                id="diamond",
            ),
        ],
    )
    def test_should_emit_css_for_supported_slide_transitions(self, transition, expected):
        """HTML deck output includes CSS keyframes for supported transition families"""
        # given
        effect, options = transition
        deck = (
            Deck(640, 360)
            .slide(Canvas().background(color="#101820"))
            .slide(Canvas().background(color="#1E293B"), transition={"effect": effect, **options})
        )

        # when
        html = deck.to_html()

        # then
        assert expected in html

    def test_should_honor_slide_advance_timing_in_html(self):
        """HTML deck stages serialize click and auto-advance transition timing"""
        # given
        from quickthumb.transitions import Fade as FadeTransition

        deck = (
            Deck(640, 360)
            .slide(Canvas().background(color="#101820"))
            .slide(
                Canvas().background(color="#1E293B"),
                transition=FadeTransition(advance_on_click=False, advance_after=2.5),
            )
        )

        # when
        html = deck.to_html()

        # then
        assert 'data-qt-click="0"' in html
        assert 'data-qt-after="2.50"' in html
        assert "function scheduleAuto()" in html
        assert "function canClick()" in html

    def test_should_render_deck_html_file(self, tmp_path):
        """Deck.render writes a single HTML slideshow and returns its path"""
        # given
        deck = Deck(320, 180).slide(Canvas().background(color="#101820"))
        output = tmp_path / "deck.html"

        # when
        written = deck.render(str(output))

        # then
        assert written == [str(output)]
        assert output.read_text().startswith("<!doctype html>")

    def test_should_reject_quality_for_deck_html_output(self, tmp_path):
        """Deck HTML output is a document format, so raster quality is invalid"""
        # given
        deck = Deck(320, 180).slide(Canvas().background(color="#101820"))

        # when / then
        with pytest.raises(RenderingError, match="[Qq]uality"):
            deck.render(str(tmp_path / "deck.html"), quality=80)

    def test_should_reject_format_override_for_deck_html_output(self, tmp_path):
        """Deck HTML output rejects raster format overrides just like PDF/PPTX"""
        # given
        deck = Deck(320, 180).slide(Canvas().background(color="#101820"))

        # when / then
        with pytest.raises(RenderingError, match="format override"):
            deck.render(str(tmp_path / "deck.html"), format="PNG")

    def test_should_run_deck_navigation_runtime_against_generated_html(self):
        """Generated deck HTML drives timeline and keyboard navigation at runtime"""
        # given
        from quickthumb.transitions import Fade as FadeTransition

        deck = (
            Deck(320, 180)
            .transition(FadeTransition(duration=0.01))
            .slide(
                Canvas().shape(
                    shape="ellipse",
                    position=(20, 20),
                    width=40,
                    height=40,
                    color="#FFFFFF",
                    animation=Fade(duration=0.01),
                )
            )
            .slide(
                Canvas()
                .background(color="#1E293B")
                .shape(
                    shape="rectangle",
                    position=(80, 20),
                    width=40,
                    height=40,
                    color="#FFFFFF",
                    animation=Fade(duration=0.01),
                )
            )
        )
        html = deck.to_html(responsive=False, embed_fonts=False)

        # when
        result = _run_deck_runtime_in_node(html)
        presenter_result = _run_deck_runtime_in_node(html, presenter=True)
        audience_advance_result = _run_deck_runtime_in_node(html, replay_advance=True)

        # then
        assert result.returncode == 0, result.stderr
        assert presenter_result.returncode == 0, presenter_result.stderr
        assert audience_advance_result.returncode == 0, audience_advance_result.stderr

    def test_should_keep_exit_layers_visible_in_presenter_preview(self):
        """Presenter previews keep layers visible until their exit animation runs."""
        # given: a next slide with a layer that exits only after the slide is shown
        deck = (
            Deck(320, 180)
            .slide(Canvas().background(color="#101820"))
            .slide(
                Canvas().shape(
                    shape="rectangle",
                    position=(20, 20),
                    width=40,
                    height=40,
                    color="#FFFFFF",
                    animation=Fade(animate="exit", duration=0.01),
                )
            )
        )
        html = deck.to_html(responsive=False, embed_fonts=False)

        # when: the presenter runtime builds its next-slide preview
        result = _run_deck_runtime_in_node(html, presenter=True, exit_preview=True)

        # then: the exit-only layer remains visible in the preview
        assert result.returncode == 0, result.stderr

    def test_should_namespace_layer_keyframes_per_slide(self):
        """Layer animation keyframes remain unique across deck slides"""
        # given
        deck = (
            Deck(320, 180)
            .slide(
                Canvas().text(
                    content="One",
                    size=48,
                    color="#FFFFFF",
                    position=(20, 20),
                    animation=Fade(),
                )
            )
            .slide(
                Canvas().text(
                    content="Two",
                    size=48,
                    color="#FFFFFF",
                    position=(20, 20),
                    animation=Wipe(),
                )
            )
        )

        # when
        html = deck.to_html()
        layer_keyframes = re.findall(r"@keyframes (qt-s\d+-k\d+)\{", html)
        timeline_keyframes = [node["k"] for timeline in timelines(html) for node in timeline]

        # then
        assert layer_keyframes == ["qt-s0-k1", "qt-s1-k1"]
        assert timeline_keyframes == layer_keyframes
        assert len(layer_keyframes) == len(set(layer_keyframes))

    def test_should_carry_per_slide_animation_timelines(self):
        """Each slide keeps its own animation timeline"""
        # given
        deck = (
            Deck(640, 360)
            .slide(
                Canvas()
                .background(color="#101820")
                .text(content="One", size=48, color="#FFFFFF", position=(20, 20), animation=Fade())
            )
            .slide(Canvas().background(color="#1E293B"))
        )

        # when
        per_slide = timelines(deck.to_html())

        # then
        assert len(per_slide) == 2
        assert len(per_slide[0]) == 1
        assert per_slide[1] == []


def _run_deck_runtime_in_node(
    html: str,
    *,
    presenter: bool = False,
    exit_preview: bool = False,
    replay_advance: bool = False,
) -> subprocess.CompletedProcess[str]:
    script = r"""
const fs = require('fs');
const vm = require('vm');
const html = fs.readFileSync(0, 'utf8');
const presenterMode = process.argv[1].startsWith('presenter');
const exitPreviewMode = process.argv[1] === 'presenter-exit';
const audienceAdvanceMode = process.argv[1] === 'audience-advance';

function decodeAttr(value) {
  return value
    .replace(/&quot;/g, '"')
    .replace(/&#x27;/g, "'")
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>');
}

class Style {
  constructor(styleText) {
    for (const part of styleText.split(';')) {
      const index = part.indexOf(':');
      if (index < 0) continue;
      const name = part.slice(0, index).trim();
      const value = part.slice(index + 1).trim();
      if (name) this[name.replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = value;
    }
  }
  setProperty(name, value) {
    this[name] = String(value);
  }
}

class Element {
  constructor(attrs) {
    this.attrs = attrs || {};
    this.hidden = this.attrs.hidden;
    this.style = new Style(this.attrs.style || '');
    this.parentElement = { clientWidth: 320, clientHeight: 180 };
    this.children = {};
    this.nodes = {};
    this.appended = [];
    this.classList = { add() {} };
  }
  getAttribute(name) {
    return this.attrs[name] || '';
  }
  querySelector(selector) {
    if (selector.startsWith('#')) return this.children[selector.slice(1)] || null;
    if (!this.nodes[selector]) this.nodes[selector] = new Element({});
    return this.nodes[selector];
  }
  setAttribute(name, value) { this.attrs[name] = String(value); }
  appendChild(child) { this.appended.push(child); child.parentElement = this; return child; }
  replaceChildren(...children) { this.appended = children; }
  cloneNode() {
    const clone = new Element({ ...this.attrs });
    clone.hidden = this.hidden;
    clone.style = Object.assign(new Style(''), this.style);
    clone.children = this.children;
    return clone;
  }
  closest() { return null; }
  addEventListener() {}
}

function parseStage(tag) {
  const attrs = {};
  const timeline = tag.match(/data-qt-timeline='([^']*)'/);
  if (timeline) attrs['data-qt-timeline'] = decodeAttr(timeline[1]);
  for (const match of tag.matchAll(/(data-qt-[\w-]+|style)="([^"]*)"/g)) {
    attrs[match[1]] = decodeAttr(match[2]);
  }
  attrs.hidden = /\shidden(?:\s|>)/.test(tag);
  return new Element(attrs);
}

const stages = Array.from(html.matchAll(/<div class="qt-stage"[^>]*>/g), (match) => {
  const stage = parseStage(match[0]);
  for (const node of JSON.parse(stage.getAttribute('data-qt-timeline') || '[]')) {
    for (const id of node.t) {
      const element = html.match(new RegExp(`id="${id}"[^>]*style="([^"]*)"`));
      stage.children[id] = new Element({ style: element ? decodeAttr(element[1]) : '' });
    }
  }
  return stage;
});
const listeners = {};
const syncMessages = [];
let channelListener = null;
const storage = {};
const documentStateId = html.match(/data-qt-state-id="([^"]+)"/)[1];
const localStorage = {
  getItem(key) { return Object.prototype.hasOwnProperty.call(storage, key) ? storage[key] : null; },
  setItem(key, value) { storage[key] = String(value); },
};
class BroadcastChannel {
  addEventListener(type, listener) {
    if (type === 'message') channelListener = listener;
  }
  postMessage(message) { syncMessages.push(message); }
}
function deliver(message) {
  if (channelListener) channelListener({ data: message });
}
const body = new Element({});
body.getAttribute = (name) => name === 'data-qt-state-id' ? documentStateId : null;
const document = {
  body,
  createElement() { return new Element({}); },
  querySelectorAll(selector) {
    return selector === '.qt-stage' ? stages : [];
  },
  addEventListener(type, callback) {
    listeners[type] = callback;
  },
  dispatch(type, event = {}) {
    listeners[type](event);
  },
};
const scripts = Array.from(
  html.matchAll(/<script>\n([\s\S]*?)<\/script>/g),
  (match) => match[1],
).join('\n');
const context = {
  BroadcastChannel,
  CSS: { escape: (value) => value },
  clearTimeout,
  console,
  document,
  isNaN,
  parseFloat,
  Promise,
  setInterval: () => 0,
  setTimeout,
  clearInterval: () => {},
  URL,
  URLSearchParams,
  window: {
    addEventListener() {},
    BroadcastChannel,
    requestAnimationFrame(callback) { callback(); },
    location: {
      href: presenterMode ? 'http://localhost:3030/presenter' : 'http://localhost:3030/',
      origin: 'http://localhost:3030',
      pathname: presenterMode ? '/presenter' : '/',
      search: '',
    },
    localStorage,
  },
};
vm.createContext(context);
vm.runInContext(scripts, context);

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

(async () => {
  if (audienceAdvanceMode) {
    await wait(90);
    deliver({ action: 'advance', state: { slide: 0, timeline: 0 } });
    await wait(30);
    assert(
      stages[0].children['qt-l1'].style.visibility === 'visible',
      'audience replays a presenter timeline advance',
    );
    return;
  }
  if (presenterMode) {
    assert(body.appended.length === 1, 'presenter shell is rendered');
    if (exitPreviewMode) {
      const preview = body.appended[0].nodes['.qt-presenter-next'].appended[0];
      const exitLayer = preview.children[Object.keys(preview.children)[0]];
      assert(exitLayer.style.visibility !== 'hidden', 'exit preview layer stays visible');
      return;
    }
    await wait(90);
    document.dispatch('keydown', { key: 'ArrowRight' });
    await wait(30);
    assert(
      syncMessages.some((message) => message.action === 'advance'),
      'presenter broadcasts a timeline advance before its final state',
    );
    const stateKey = `quickthumb:state:http://localhost:3030/:${documentStateId}`;
    assert(
      storage[stateKey] === JSON.stringify({ slide: 0, timeline: 1 }),
      `presenter persists the complete presentation state (${storage[stateKey]})`,
    );
    stages.forEach((stage) => {
      stage.hidden = true;
      stage.style.display = 'none';
      stage.style.animation = '';
    });
    vm.runInContext(scripts, context);
    await wait(10);
    assert(body.appended.length === 2, 'presenter reload renders the presenter shell');
    assert(stages[0].hidden === false, 'presenter reload restores the saved slide');
    assert(
      stages[0].children['qt-l1'].style.visibility === 'visible',
      'presenter reload restores the saved timeline cursor',
    );
    return;
  }
  assert(stages[0].hidden === false, 'first slide starts visible');
  assert(stages[1].hidden === true, 'second slide starts hidden');
  document.dispatch('click');
  await wait(90);
  assert(stages[0].hidden === false, 'rapid click during transition is ignored');
  assert(stages[1].hidden === true, 'rapid click does not reveal slide two');
  assert(
    syncMessages.some((message) => message.action === 'ready'),
    'audience requests presenter state after its entrance transition settles',
  );
  document.dispatch('click');
  await wait(30);
  assert(
    stages[0].children['qt-l1'].style.visibility === 'visible',
    'timeline click reveals layer',
  );
  document.dispatch('keydown', { key: 'ArrowRight' });
  await wait(90);
  assert(stages[0].hidden === true, 'arrow right hides slide one');
  assert(stages[1].hidden === false, 'arrow right reveals slide two');
  document.dispatch('keydown', { key: 'ArrowLeft' });
  await wait(90);
  assert(stages[0].hidden === false, 'arrow left restores slide one');
  assert(stages[1].hidden === true, 'arrow left hides slide two');
  document.dispatch('keydown', { key: 'ArrowRight' });
  await wait(90);
  assert(stages[1].hidden === false, 'saved current slide is visible before reload');
  const stateKey = `quickthumb:state:http://localhost:3030/:${documentStateId}`;
  assert(storage[stateKey] === undefined, 'audience navigation does not own presenter state');
  storage[stateKey] = JSON.stringify({ slide: 1, timeline: 0 });
  stages.forEach((stage) => {
    stage.hidden = true;
    stage.style.display = 'none';
    stage.style.animation = '';
  });
  vm.runInContext(scripts, context);
  await wait(10);
  assert(stages[0].hidden === true, 'reload keeps the previous slide hidden');
  assert(stages[1].hidden === false, 'reload restores the saved current slide');
  assert(
    stages[1].children['qt-l2'].style.visibility === 'hidden',
    'reload restores the saved timeline cursor',
  );
})().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
"""
    return subprocess.run(
        [
            "node",
            "-e",
            script,
            "audience-advance"
            if replay_advance
            else "presenter-exit"
            if exit_preview
            else "presenter"
            if presenter
            else "audience",
        ],
        capture_output=True,
        check=False,
        input=html,
        text=True,
    )
