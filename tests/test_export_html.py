"""Tests for HTML export (Canvas.to_html / Deck.to_html and rendering to .html)."""

import json
import re
from pathlib import Path

import pytest
from quickthumb import (
    Box,
    Canvas,
    Deck,
    Fade,
    LinearGradient,
    TextPart,
    Wipe,
)
from quickthumb.errors import RenderingError
from quickthumb.models import Background, Shadow, Stroke, TextFillImage

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
    return [json.loads(raw) for raw in re.findall(r"data-qt-timeline='([^']*)'", html)]


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
            shape="rectangle", position=(20, 20), width=120, height=60, color="#CC0000",
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
            shape="star", position=(20, 20), width=100, height=100, color="#FFD700",
        )

        # when / then
        assert "clip-path:polygon(" in canvas.to_html()


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

    def test_should_rasterize_image_filled_text(self):
        """Image-filled glyphs fall back to an embedded PNG fragment"""
        # given
        canvas = Canvas(400, 200).text(
            content="IMG",
            size=64,
            fill=TextFillImage(path=SAMPLE_IMAGE, fit="cover"),
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
        assert '<img' in html
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
        # Each slide carries its own enter-transition animation (a cross-fade by
        # default), wired through a data attribute the runtime reads on show().
        assert html.count("data-qt-transition=") == 2
        assert "@keyframes qt-t0{from{opacity:0}to{opacity:1}}" in html

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
            pytest.param(("circle", {}), "clip-path:circle(0% at 50% 50%)", id="circle"),
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

    def test_should_drive_slides_with_keyboard_navigation(self):
        """The deck runtime wires up gated arrow-key navigation"""
        # given
        deck = Deck(320, 180).slide(Canvas().background(color="#101820"))

        # when
        html = deck.to_html()

        # then
        assert "ArrowRight" in html
        assert "go(current-1,true)" in html
        assert "finishTimeline(i)" in html
        assert "function reverse(anim)" in html
        assert "canClick()" in html

    def test_should_ignore_navigation_while_slide_or_timeline_animation_is_running(self):
        """Rapid navigation input is ignored until the active animation finishes"""
        # given
        from quickthumb.transitions import Push

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
            .slide(Canvas().background(color="#1E293B"), transition=Push())
        )

        # when
        html = deck.to_html()

        # then
        assert "transitioning=false,timelineBusy=false" in html
        assert "if(transitioning||timelineBusy||i<0||i>=stages.length||i===current)return;" in html
        assert "if(transitioning||timelineBusy)return;" in html
        assert "timelineBusy=true;" in html
        assert "timelineBusy=false;scheduleAuto();" in html

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
