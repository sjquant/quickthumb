"""Tests for PDF export (Canvas.to_pdf and rendering to .pdf files)"""

from io import BytesIO
from pathlib import Path

import pytest
from quickthumb import Canvas, LinearGradient
from quickthumb.errors import RenderingError

from tests._optional import require_cairosvg, require_pypdfium2

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_IMAGE = str(FIXTURES_DIR / "sample_image.jpg")


def open_pdf(canvas: Canvas):
    pdfium = require_pypdfium2()
    return pdfium.PdfDocument(BytesIO(canvas.to_pdf()))


class TestPdfDocument:
    """Test suite for document-level PDF output"""

    def setup_method(self):
        require_cairosvg()

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


class TestPdfContent:
    """Test suite for the PDF carrying every layer's content"""

    def setup_method(self):
        require_cairosvg()
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
