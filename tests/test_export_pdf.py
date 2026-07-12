"""Tests for PDF export (Canvas.to_pdf and rendering to .pdf files)"""

from io import BytesIO
from pathlib import Path

import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.misc.psCharStrings import T2CharString
from PIL import Image
from quickthumb import Canvas, LinearGradient
from quickthumb.errors import RenderingError

from tests._optional import require_pypdfium2

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_IMAGE = str(FIXTURES_DIR / "sample_image.jpg")


def open_pdf(canvas: Canvas):
    pdfium = require_pypdfium2()
    return pdfium.PdfDocument(BytesIO(canvas.to_pdf()))


def create_cff_fixture(path: Path, content: str, fs_type: int = 0) -> Path:
    """Create a small portable CFF font fixture for PDF fallback tests."""
    glyph_order = [".notdef"]
    charstrings = {
        ".notdef": T2CharString(
            program=[
                0,
                0,
                "hmoveto",
                0,
                700,
                "vmoveto",
                500,
                0,
                "rlineto",
                0,
                -700,
                "rlineto",
                -500,
                0,
                "rlineto",
                "endchar",
            ]
        )
    }
    character_map = {}
    for index, character in enumerate(dict.fromkeys(content)):
        glyph_name = f"glyph{index}"
        glyph_order.append(glyph_name)
        character_map[ord(character)] = glyph_name
        charstrings[glyph_name] = T2CharString(
            program=[
                0,
                0,
                "hmoveto",
                0,
                700,
                "vmoveto",
                500,
                0,
                "rlineto",
                0,
                -700,
                "rlineto",
                -500,
                0,
                "rlineto",
                "endchar",
            ]
        )

    builder = FontBuilder(1000, isTTF=False)
    builder.setupGlyphOrder(glyph_order)
    builder.setupCharacterMap(character_map)
    builder.setupHorizontalMetrics(dict.fromkeys(glyph_order, (600, 0)))
    builder.setupHorizontalHeader(ascent=1055, descent=-455, lineGap=0)
    builder.setupOS2(
        fsType=fs_type,
        sTypoAscender=750,
        sTypoDescender=-250,
        sTypoLineGap=510,
        usWinAscent=1055,
        usWinDescent=455,
        usWeightClass=400,
        fsSelection=64,
    )
    builder.setupNameTable(
        {
            "familyName": "Quickthumb CFF Fixture",
            "styleName": "Regular",
            "uniqueFontIdentifier": "Quickthumb CFF Fixture Regular",
            "fullName": "Quickthumb CFF Fixture Regular",
            "psName": "QuickthumbCFFFixture",
        }
    )
    builder.setupCFF(
        "QuickthumbCFFFixture",
        {
            "FamilyName": "Quickthumb CFF Fixture",
            "Weight": "Regular",
            "FontMatrix": [0.001, 0, 0, -0.001, 0, 0],
        },
        charstrings,
        {"defaultWidthX": 600, "nominalWidthX": 0},
    )
    builder.setupPost()
    builder.setupHead()
    builder.save(path)
    return path


def _mask_overlap(actual: Image.Image, expected: Image.Image) -> float:
    """Return the intersection-over-union of dark-pixel masks."""
    actual_pixels = actual.convert("L").load()
    expected_pixels = expected.convert("L").load()
    actual_ink = {
        (x, y)
        for y in range(actual.height)
        for x in range(actual.width)
        if actual_pixels[x, y] < 220
    }
    expected_ink = {
        (x, y)
        for y in range(expected.height)
        for x in range(expected.width)
        if expected_pixels[x, y] < 220
    }
    if not actual_ink and not expected_ink:
        return 1.0
    return len(actual_ink & expected_ink) / len(actual_ink | expected_ink)


class TestPdfDocument:
    """Test suite for document-level PDF output"""

    def test_should_produce_a_single_page_pdf(self):
        """to_pdf returns a one-page PDF with the standard PDF header"""
        # given
        canvas = Canvas(480, 270).background(color="#101826")

        # when
        data = canvas.to_pdf()

        # then
        assert data[:5] == b"%PDF-"
        assert len(open_pdf(canvas)) == 1

    def test_should_size_page_to_canvas_pixels(self):
        """The page adopts the canvas dimensions at one point per pixel"""
        # given
        canvas = Canvas(1280, 720).background(color="#000000")

        # when
        page = open_pdf(canvas)[0]

        # then
        width_pt, height_pt = page.get_size()
        assert width_pt == pytest.approx(1280)
        assert height_pt == pytest.approx(720)

    def test_should_render_pdf_file_from_extension(self, tmp_path):
        """render() writes a PDF file when the output path ends in .pdf"""
        # given
        canvas = Canvas(400, 300).background(color="#FF0000")
        output = tmp_path / "card.pdf"

        # when
        canvas.render(str(output))

        # then
        assert output.read_bytes()[:5] == b"%PDF-"

    def test_should_reject_quality_for_pdf_output(self, tmp_path):
        """Quality is a raster-only option and is rejected for PDF output"""
        # given
        canvas = Canvas(400, 300).background(color="#FF0000")
        output = tmp_path / "card.pdf"

        # when / then
        with pytest.raises(RenderingError, match="Quality parameter is only supported"):
            canvas.render(str(output), quality=80)

    def test_should_embed_fonts_for_self_contained_text(self):
        """Text fonts are embedded so the PDF renders without the fonts installed"""
        # given
        canvas = Canvas(600, 200).text(
            content="Embedded",
            font="Roboto",
            size=48,
            bold=True,
            color="#FFFFFF",
            position=(40, 60),
        )

        # when
        data = canvas.to_pdf()

        # then a font program is embedded in the document
        assert b"FontFile" in data

    def test_should_release_temporary_font_registrations_after_export(self):
        """Repeated exports do not accumulate temporary ReportLab font registrations"""
        # given
        from reportlab.pdfbase import pdfmetrics

        canvas = Canvas(600, 200).text(
            content="Embedded",
            font="Roboto",
            size=48,
            color="#FFFFFF",
            position=(40, 60),
        )
        registered_before = set(pdfmetrics.getRegisteredFontNames())

        # when
        for _ in range(3):
            assert b"FontFile" in canvas.to_pdf()

        # then
        assert set(pdfmetrics.getRegisteredFontNames()) == registered_before


class TestPdfUnsupportedFonts:
    """Test PDF behavior for fonts Pillow supports but ReportLab cannot embed."""

    def setup_method(self):
        require_pypdfium2()

    def test_should_convert_text_when_reportlab_cannot_embed_the_pillow_font(self, tmp_path):
        """Unsupported CFF fonts preserve crisp glyphs through vector conversion"""
        # given
        content = "한글"
        font_path = create_cff_fixture(tmp_path / "fixture.otf", content)
        canvas = (
            Canvas(600, 180)
            .background(color="#FFFFFF")
            .text(
                content=content,
                font=str(font_path),
                size=48,
                color="#1D2A35",
                position=(40, 55),
            )
        )
        expected_path = tmp_path / "expected.png"

        # when
        canvas.render(str(expected_path))
        expected = Image.open(expected_path).convert("RGB")
        data = canvas.to_pdf()
        page = require_pypdfium2().PdfDocument(BytesIO(data))[0]
        actual = page.render(scale=1).to_pil().convert("RGB")

        # then
        assert actual.size == expected.size
        assert b"FontFile" in data
        assert page.get_textpage().get_text_range() == content
        assert _mask_overlap(actual, expected) >= 0.8

    def test_should_fallback_to_raster_for_restricted_font_embedding(self, tmp_path):
        """Restricted CFF fonts render without being embedded into the PDF"""
        # given
        content = "한글"
        font_path = create_cff_fixture(tmp_path / "restricted.otf", content, fs_type=0x0002)
        canvas = (
            Canvas(600, 180)
            .background(color="#FFFFFF")
            .text(
                content=content,
                font=str(font_path),
                size=48,
                color="#1D2A35",
                position=(40, 55),
            )
        )
        expected_path = tmp_path / "expected.png"

        # when
        canvas.render(str(expected_path))
        expected = Image.open(expected_path).convert("RGB")
        data = canvas.to_pdf()
        page = require_pypdfium2().PdfDocument(BytesIO(data))[0]
        actual = page.render(scale=1).to_pil().convert("RGB")

        # then
        assert b"FontFile" not in data
        assert _mask_overlap(actual, expected) >= 0.98

    def test_should_fallback_to_raster_for_complex_script_shaping(self, tmp_path):
        """Complex-script CFF text preserves shaping through the raster fallback"""
        # given
        content = "سلام"
        font_path = create_cff_fixture(tmp_path / "arabic.otf", content)
        canvas = (
            Canvas(600, 180)
            .background(color="#FFFFFF")
            .text(
                content=content,
                font=str(font_path),
                size=48,
                color="#1D2A35",
                position=(40, 55),
            )
        )
        expected_path = tmp_path / "expected.png"

        # when
        canvas.render(str(expected_path))
        expected = Image.open(expected_path).convert("RGB")
        data = canvas.to_pdf()
        page = require_pypdfium2().PdfDocument(BytesIO(data))[0]
        actual = page.render(scale=1).to_pil().convert("RGB")

        # then
        assert b"FontFile" not in data
        assert _mask_overlap(actual, expected) >= 0.98

    def test_should_fallback_to_raster_when_a_glyph_is_missing(self, tmp_path):
        """Text with a missing CFF glyph preserves Pillow's fallback rendering"""
        # given
        content = "한글"
        font_path = create_cff_fixture(tmp_path / "missing.otf", "한")
        canvas = (
            Canvas(600, 180)
            .background(color="#FFFFFF")
            .text(
                content=content,
                font=str(font_path),
                size=48,
                color="#1D2A35",
                position=(40, 55),
            )
        )
        expected_path = tmp_path / "expected.png"

        # when
        canvas.render(str(expected_path))
        expected = Image.open(expected_path).convert("RGB")
        data = canvas.to_pdf()
        page = require_pypdfium2().PdfDocument(BytesIO(data))[0]
        actual = page.render(scale=1).to_pil().convert("RGB")

        # then
        assert b"FontFile" not in data
        assert _mask_overlap(actual, expected) >= 0.98


class TestPdfCompositionEffects:
    """Test suite for composition effects in PDF raster fallbacks"""

    def setup_method(self):
        require_pypdfium2()

    def test_should_preserve_backdrop_blur_via_raster_fallback(self):
        """Backdrop blur renders with prior layers in PDF export through raster fallback"""
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
                effects=[{"type": "backdrop_blur", "radius": 5}],
            )
        )

        # when
        control_page = open_pdf(no_blur)[0]
        control = (
            control_page.render(scale=no_blur.width / control_page.get_size()[0])
            .to_pil()
            .convert("RGB")
        )
        blurred_page = open_pdf(with_blur)[0]
        blurred = (
            blurred_page.render(scale=with_blur.width / blurred_page.get_size()[0])
            .to_pil()
            .convert("RGB")
        )

        # then
        assert blurred.getpixel((36, 25))[2] - control.getpixel((36, 25))[2] >= 10


class TestPdfContent:
    """Test suite for the PDF carrying every layer's content"""

    def setup_method(self):
        require_pypdfium2()

    def test_should_render_non_blank_output_for_a_full_canvas(self):
        """A canvas with shapes, text, and an image rasterizes to varied pixels"""
        # given
        canvas = (
            Canvas(400, 300)
            .background(
                gradient=LinearGradient(angle=45, stops=[("#0F172A", 0.0), ("#7C3AED", 1.0)])
            )
            .shape(shape="rectangle", position=(40, 40), width=120, height=80, color="#22C55E")
            .image(path=SAMPLE_IMAGE, position=(220, 40), width=140)
            .text(content="Title", font="Roboto", size=40, color="#FFFFFF", position=(40, 200))
        )

        # when
        page = open_pdf(canvas)[0]
        image = page.render(scale=canvas.width / page.get_size()[0]).to_pil().convert("RGB")

        # then the page is the canvas size and is not a single flat color
        assert image.size == (400, 300)
        assert len(image.getcolors(maxcolors=1_000_000)) > 100

    def test_should_preserve_masked_shape_via_raster_fallback(self):
        """Masked shapes render correctly in PDF export through raster fallback"""
        # given
        canvas = (
            Canvas(80, 80)
            .background(color="#FFFFFF")
            .shape(
                shape="rectangle",
                position=(10, 10),
                width=60,
                height=60,
                color="#FF0000",
                mask={"shape": "ellipse", "position": (10, 10), "width": 60, "height": 60},
            )
        )

        # when
        page = open_pdf(canvas)[0]
        image = page.render(scale=canvas.width / page.get_size()[0]).to_pil().convert("RGB")

        # then
        assert image.getpixel((40, 40)) == (255, 0, 0)
        assert image.getpixel((12, 12)) == (255, 255, 255)
