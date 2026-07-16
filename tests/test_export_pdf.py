"""Tests for PDF export (Canvas.to_pdf and rendering to .pdf files)"""

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.misc.psCharStrings import T2CharString
from fontTools.pens.ttGlyphPen import TTGlyphPen
from PIL import Image
from quickthumb import BackdropBlur, Canvas, Deck, LinearGradient
from quickthumb.errors import RenderingError

from tests._helpers import pixel_scalar
from tests._optional import require_pypdfium2

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_IMAGE = str(FIXTURES_DIR / "sample_image.jpg")


def open_pdf(canvas: Canvas):
    pdfium = require_pypdfium2()
    return pdfium.PdfDocument(BytesIO(canvas.to_pdf()))


def _cff_rectangle(width: int, height: int) -> T2CharString:
    """Build one CFF outline with unique dimensions for glyph fidelity tests."""
    return T2CharString(
        program=[
            0,
            0,
            "hmoveto",
            0,
            height,
            "vmoveto",
            width,
            0,
            "rlineto",
            0,
            -height,
            "rlineto",
            -width,
            0,
            "rlineto",
            "endchar",
        ]
    )


def create_cff_fixture(path: Path, content: str, fs_type: int = 0) -> Path:
    """Create a small portable CFF font fixture for PDF fallback tests."""
    glyph_order = [".notdef"]
    charstrings = {".notdef": _cff_rectangle(280, 360)}
    metrics = {".notdef": (380, 0)}
    character_map = {}
    characters = list(dict.fromkeys(content))

    def add_glyph(name: str, glyph: T2CharString, advance: int) -> None:
        glyph_order.append(name)
        charstrings[name] = glyph
        metrics[name] = (advance, 0)

    if "A" in characters or "Á" in characters:
        add_glyph("A", _cff_rectangle(360, 620), 470)
    if "Á" in characters:
        add_glyph("acute", _cff_rectangle(160, 160), 260)
        add_glyph("Aacute", T2CharString(program=[0, 0, 65, 194, "endchar"]), 470)

    normal_index = 0
    for character in characters:
        if character == "A":
            character_map[ord(character)] = "A"
            continue
        if character == "Á":
            character_map[ord(character)] = "Aacute"
            continue
        width = 340 + normal_index * 80
        height = 460 + normal_index * 70
        glyph_name = f"glyph{normal_index}"
        add_glyph(glyph_name, _cff_rectangle(width, height), width + 110)
        character_map[ord(character)] = glyph_name
        normal_index += 1

    builder = FontBuilder(1000, isTTF=False)
    builder.setupGlyphOrder(glyph_order)
    builder.setupCharacterMap(character_map)
    builder.setupHorizontalMetrics(metrics)
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


def _ttf_rectangle(width: int, height: int):
    """Build a TrueType rectangle outline for a portable direct-font fixture."""
    pen = TTGlyphPen(None)
    pen.moveTo((0, 0))
    pen.lineTo((0, height))
    pen.lineTo((width, height))
    pen.lineTo((width, 0))
    pen.closePath()
    return pen.glyph()


def create_ttf_fixture(path: Path, content: str, fs_type: int = 0) -> Path:
    """Create a portable TrueType font fixture with one distinct glyph per character."""
    glyph_order = [".notdef"]
    glyphs = {".notdef": _ttf_rectangle(280, 360)}
    metrics = {".notdef": (380, 0)}
    character_map = {}
    for index, character in enumerate(dict.fromkeys(content)):
        width = 340 + index * 80
        height = 460 + index * 70
        glyph_name = f"glyph{index}"
        glyph_order.append(glyph_name)
        glyphs[glyph_name] = _ttf_rectangle(width, height)
        metrics[glyph_name] = (width + 110, 0)
        character_map[ord(character)] = glyph_name

    builder = FontBuilder(1000, isTTF=True)
    builder.setupGlyphOrder(glyph_order)
    builder.setupCharacterMap(character_map)
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics(metrics)
    builder.setupHorizontalHeader(ascent=800, descent=-200, lineGap=0)
    builder.setupOS2(
        fsType=fs_type,
        sTypoAscender=800,
        sTypoDescender=-200,
        sTypoLineGap=0,
        usWinAscent=800,
        usWinDescent=200,
        usWeightClass=400,
    )
    builder.setupNameTable(
        {
            "familyName": "Quickthumb TTF Fixture",
            "styleName": "Regular",
            "uniqueFontIdentifier": "Quickthumb TTF Fixture Regular",
            "fullName": "Quickthumb TTF Fixture Regular",
            "psName": "QuickthumbTTFFixture",
        }
    )
    builder.setupPost()
    builder.setupHead()
    builder.save(path)
    return path


def render_canvas_image(canvas: Canvas, tmp_path: Path, name: str) -> Image.Image:
    """Render a Canvas through Pillow and return a loaded RGB reference image."""
    path = tmp_path / name
    canvas.render(str(path))
    with Image.open(path) as image:
        rgba = image.convert("RGBA")
    flattened = Image.new("RGB", rgba.size, "white")
    flattened.paste(rgba, mask=rgba.getchannel("A"))
    return flattened


def _mask_overlap(actual: Image.Image, expected: Image.Image) -> float:
    """Return the intersection-over-union of dark-pixel masks."""
    actual_pixels = actual.convert("L")
    expected_pixels = expected.convert("L")
    actual_ink = {
        (x, y)
        for y in range(actual.height)
        for x in range(actual.width)
        if pixel_scalar(actual_pixels, (x, y)) < 220
    }
    expected_ink = {
        (x, y)
        for y in range(expected.height)
        for x in range(expected.width)
        if pixel_scalar(expected_pixels, (x, y)) < 220
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

    def test_should_release_reportlab_family_mappings_after_cff_exports(self, tmp_path):
        """CFF subset exports restore ReportLab's family mapping globals"""
        # given
        from reportlab.lib import fonts

        font_path = create_cff_fixture(tmp_path / "fixture.otf", "AÁB")
        tt2ps_before = dict(fonts._tt2ps_map)
        ps2tt_before = dict(fonts._ps2tt_map)

        # when
        for content in ("A", "AB", "AÁB"):
            data = (
                Canvas(300, 100)
                .text(
                    content=content,
                    font=str(font_path),
                    size=30,
                    color="#000000",
                    position=(10, 20),
                )
                .to_pdf()
            )
            assert b"FontFile" in data

        # then
        assert fonts._tt2ps_map == tt2ps_before
        assert fonts._ps2tt_map == ps2tt_before

    def test_should_complete_concurrent_exports_with_the_same_font(self, tmp_path):
        """Parallel PDF exports do not release a font another export is using"""
        # given
        font_path = create_ttf_fixture(tmp_path / "fixture.ttf", "AB")
        canvases = [
            Canvas(300, 100).text(
                content="AB",
                font=str(font_path),
                size=30,
                color="#000000",
                position=(10, 20),
            )
            for _ in range(8)
        ]

        # when
        with ThreadPoolExecutor(max_workers=4) as executor:
            documents = list(executor.map(lambda canvas: canvas.to_pdf(), canvases))

        # then
        assert all(b"FontFile" in document for document in documents)


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

    def test_should_recheck_embedding_permissions_when_a_font_file_is_replaced(self, tmp_path):
        """Replacing a font at one path does not reuse stale embedding permissions"""
        # given
        font_path = tmp_path / "replaceable.otf"
        create_cff_fixture(font_path, "A")
        first = Canvas(300, 100).text(
            content="A",
            font=str(font_path),
            size=30,
            color="#000000",
            position=(10, 20),
        )
        assert b"FontFile" in first.to_pdf()
        create_cff_fixture(font_path, "A", fs_type=0x0002)
        second = Canvas(300, 100).text(
            content="A",
            font=str(font_path),
            size=30,
            color="#000000",
            position=(10, 20),
        )

        # when
        expected = render_canvas_image(second, tmp_path, "expected.png")
        data = second.to_pdf()
        page = require_pypdfium2().PdfDocument(BytesIO(data))[0]
        actual = page.render(scale=1).to_pil().convert("RGB")

        # then
        assert b"FontFile" not in data
        assert _mask_overlap(actual, expected) >= 0.98

    def test_should_embed_distinct_cff_glyphs_across_deck_pages(self, tmp_path):
        """One document subset retains distinct and composite CFF glyphs on every page"""
        # given
        font_path = create_cff_fixture(tmp_path / "fixture.otf", "AÁB")
        first = Canvas(300, 120).text(
            content="A",
            font=str(font_path),
            size=36,
            color="#000000",
            position=(20, 30),
        )
        second = Canvas(300, 120).text(
            content="ÁB",
            font=str(font_path),
            size=36,
            color="#000000",
            position=(20, 30),
        )
        expected_first = render_canvas_image(first, tmp_path, "first.png")
        expected_second = render_canvas_image(second, tmp_path, "second.png")

        # when
        data = Deck(slides=[first, second]).to_pdf()
        document = require_pypdfium2().PdfDocument(BytesIO(data))
        actual_first = document[0].render(scale=1).to_pil().convert("RGB")
        actual_second = document[1].render(scale=1).to_pil().convert("RGB")

        # then
        assert len(document) == 2
        assert b"FontFile" in data
        assert document[0].get_textpage().get_text_range() == "A"
        assert document[1].get_textpage().get_text_range() == "ÁB"
        assert _mask_overlap(actual_first, expected_first) >= 0.8
        assert _mask_overlap(actual_second, expected_second) >= 0.8


class TestPdfDirectFonts:
    """Test vector eligibility checks for TrueType fonts ReportLab can embed directly."""

    def setup_method(self):
        require_pypdfium2()

    def test_should_fallback_to_raster_for_direct_ttf_complex_script_shaping(self, tmp_path):
        """Arabic TrueType text avoids ReportLab's unshaped vector path"""
        # given
        content = "سلام"
        font_path = create_ttf_fixture(tmp_path / "arabic.ttf", content)
        canvas = Canvas(300, 100).text(
            content=content,
            font=str(font_path),
            size=30,
            color="#000000",
            position=(10, 20),
        )

        # when
        expected = render_canvas_image(canvas, tmp_path, "expected.png")
        data = canvas.to_pdf()
        page = require_pypdfium2().PdfDocument(BytesIO(data))[0]
        actual = page.render(scale=1).to_pil().convert("RGB")

        # then
        assert b"FontFile" not in data
        assert _mask_overlap(actual, expected) >= 0.98

    def test_should_fallback_to_raster_for_missing_direct_ttf_glyph(self, tmp_path):
        """A missing TrueType glyph preserves Pillow's fallback rendering"""
        # given
        content = "한글"
        font_path = create_ttf_fixture(tmp_path / "missing.ttf", "한")
        canvas = Canvas(300, 100).text(
            content=content,
            font=str(font_path),
            size=30,
            color="#000000",
            position=(10, 20),
        )

        # when
        expected = render_canvas_image(canvas, tmp_path, "expected.png")
        data = canvas.to_pdf()
        page = require_pypdfium2().PdfDocument(BytesIO(data))[0]
        actual = page.render(scale=1).to_pil().convert("RGB")

        # then
        assert b"FontFile" not in data
        assert _mask_overlap(actual, expected) >= 0.98

    def test_should_keep_same_named_ttf_faces_independent(self, tmp_path):
        """Two files with one internal font name keep their own glyph programs"""
        # given
        first_font = create_ttf_fixture(tmp_path / "first.ttf", "A")
        second_font = create_ttf_fixture(tmp_path / "second.ttf", "B")
        canvas = (
            Canvas(300, 100)
            .background(color="#FFFFFF")
            .text(
                content="A",
                font=str(first_font),
                size=30,
                color="#000000",
                position=(20, 20),
            )
            .text(
                content="B",
                font=str(second_font),
                size=30,
                color="#000000",
                position=(130, 20),
            )
        )

        # when
        expected = render_canvas_image(canvas, tmp_path, "expected.png")
        data = canvas.to_pdf()
        page = require_pypdfium2().PdfDocument(BytesIO(data))[0]
        actual = page.render(scale=1).to_pil().convert("RGB")

        # then
        assert b"FontFile" in data
        assert "".join(page.get_textpage().get_text_range().split()) == "AB"
        assert _mask_overlap(actual, expected) >= 0.8
        assert b"FontFile" in canvas.to_pdf()

    def test_should_keep_shared_text_layer_layouts_on_each_deck_page(self, tmp_path):
        """Reused TextLayer objects resolve positions against their own slide size"""
        # given
        font_path = create_ttf_fixture(tmp_path / "shared.ttf", "AB")
        seed = Canvas(1, 1).text(
            content="AB",
            font=str(font_path),
            size=30,
            color="#000000",
            position=("50%", "50%"),
            align="center",
        )
        shared_layer = seed.layers[-1]
        first = Canvas(100, 100, layers=[shared_layer])
        second = Canvas(300, 100, layers=[shared_layer])
        expected_first = render_canvas_image(first, tmp_path, "first.png")
        expected_second = render_canvas_image(second, tmp_path, "second.png")

        # when
        document = require_pypdfium2().PdfDocument(BytesIO(Deck(slides=[first, second]).to_pdf()))
        actual_first = document[0].render(scale=1).to_pil().convert("RGB")
        actual_second = document[1].render(scale=1).to_pil().convert("RGB")

        # then
        assert _mask_overlap(actual_first, expected_first) >= 0.8
        assert _mask_overlap(actual_second, expected_second) >= 0.8


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
                effects=[BackdropBlur(radius=5)],
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
