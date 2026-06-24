"""Tests for Deck: multi-slide / multi-image collections of Canvas objects."""

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from quickthumb import Canvas, Deck
from quickthumb.errors import RenderingError, ValidationError

from tests._optional import require_pypdfium2

pptx = pytest.importorskip("pptx", reason="python-pptx is required for some deck tests")
from pptx import Presentation  # noqa: E402


def make_slide(text: str, width: int = 1280, height: int = 720) -> Canvas:
    """Build a small, self-contained slide with a solid background and label."""
    return (
        Canvas(width, height)
        .background(color="#101820")
        .text(content=text, size=96, color="#FFFFFF", position=("50%", "50%"), align="center")
    )


class TestDeckComposition:
    """Building a deck and inspecting its slides."""

    def test_should_collect_slides_via_constructor_and_chaining(self):
        """slide() and add() append canvases while staying chainable."""
        # given
        first = make_slide("1")
        second = make_slide("2")
        third = make_slide("3")

        # when
        deck = Deck([first]).slide(second).add(third)

        # then
        assert list(deck) == [first, second, third]
        assert len(deck) == 3
        assert deck[1] is second

    def test_should_reject_non_canvas_slides(self):
        """Adding something that is not a Canvas raises a validation error."""
        # given
        deck = Deck()

        # when / then
        with pytest.raises(ValidationError, match="must be Canvas"):
            deck.slide("not a canvas")  # type: ignore[arg-type]

    def test_should_reject_rendering_an_empty_deck(self, tmp_path: Path):
        """An empty deck cannot be rendered to any format."""
        # given
        deck = Deck()

        # when / then
        with pytest.raises(RenderingError, match="no slides"):
            deck.render(str(tmp_path / "out.pdf"))


class TestRenderDispatch:
    """render() dispatches on the output extension and rejects bad combinations."""

    def test_should_reject_single_svg_output(self, tmp_path: Path):
        """A deck has no single-file SVG form and says so explicitly."""
        # given
        deck = Deck().slide(make_slide("1"))

        # when / then
        with pytest.raises(RenderingError, match="single .svg"):
            deck.render(str(tmp_path / "deck.svg"))

    def test_should_reject_unknown_extension(self, tmp_path: Path):
        """An unrecognized extension is rejected rather than guessed."""
        # given
        deck = Deck().slide(make_slide("1"))

        # when / then
        with pytest.raises(RenderingError, match="Unsupported deck output format"):
            deck.render(str(tmp_path / "deck.gif"))

    def test_should_reject_format_override_for_document_output(self, tmp_path: Path):
        """A raster format override is meaningless for document output."""
        # given
        deck = Deck().slide(make_slide("1"))

        # when / then
        with pytest.raises(RenderingError, match="format override"):
            deck.render(str(tmp_path / "deck.pdf"), format="PNG")


class TestRasterSequence:
    """Rendering a deck to per-slide raster images."""

    def test_should_write_zero_padded_numbered_sequence(self, tmp_path: Path):
        """Raster output writes one file per slide with a zero-padded index."""
        # given
        deck = Deck().add(make_slide("a"), make_slide("b"), make_slide("c"))
        output = tmp_path / "slides.png"

        # when
        written = deck.render(str(output))

        # then
        assert written == [
            str(tmp_path / "slides_01.png"),
            str(tmp_path / "slides_02.png"),
            str(tmp_path / "slides_03.png"),
        ]
        for path in written:
            assert Path(path).exists()
            assert Image.open(path).size == (1280, 720)

    def test_should_pass_quality_through_for_jpeg_sequence(self, tmp_path: Path):
        """Raster sequences honor the quality argument for JPEG output."""
        # given
        deck = Deck().add(make_slide("a"), make_slide("b"))
        output = tmp_path / "slides.jpg"

        # when
        written = deck.render(str(output), quality=50)

        # then
        assert len(written) == 2
        assert all(Path(path).exists() for path in written)


class TestDocumentExport:
    """Rendering a deck to multi-page PDF and multi-slide PPTX documents."""

    def test_should_render_one_pdf_page_per_slide(self, tmp_path: Path):
        """A PDF deck produces a document with a page for every slide."""
        # given
        pdfium = require_pypdfium2()
        deck = Deck().add(make_slide("1"), make_slide("2"), make_slide("3"))
        output = tmp_path / "deck.pdf"

        # when
        deck.render(str(output))

        # then
        document = pdfium.PdfDocument(str(output))
        assert len(document) == 3

    def test_should_render_one_pptx_slide_per_slide(self, tmp_path: Path):
        """A PPTX deck produces a presentation with a slide for every slide."""
        # given
        deck = Deck().add(make_slide("1"), make_slide("2"))
        output = tmp_path / "deck.pptx"

        # when
        deck.render(str(output))

        # then
        presentation = Presentation(str(output))
        assert len(presentation.slides) == 2

    def test_should_expose_pdf_bytes_with_a_page_per_slide(self):
        """to_pdf() returns multi-page PDF bytes."""
        # given
        pdfium = require_pypdfium2()
        deck = Deck().add(make_slide("1"), make_slide("2"))

        # when
        data = deck.to_pdf()

        # then
        assert len(pdfium.PdfDocument(BytesIO(data))) == 2

    def test_should_expose_pptx_bytes_with_a_slide_per_slide(self):
        """to_pptx() returns multi-slide presentation bytes."""
        # given
        deck = Deck().add(make_slide("1"), make_slide("2"), make_slide("3"))

        # when
        data = deck.to_pptx()

        # then
        assert len(Presentation(BytesIO(data)).slides) == 3

    def test_should_reject_quality_for_document_output(self, tmp_path: Path):
        """Document formats do not accept the raster-only quality argument."""
        # given
        deck = Deck().slide(make_slide("1"))

        # when / then
        with pytest.raises(RenderingError, match="Quality parameter"):
            deck.render(str(tmp_path / "deck.pdf"), quality=80)

    def test_should_keep_first_slide_size_for_mixed_pptx(self, tmp_path: Path):
        """With mixed sizes the PPTX page size comes from the first slide."""
        # given
        deck = Deck().add(make_slide("wide", 1280, 720), make_slide("square", 800, 800))
        output = tmp_path / "deck.pptx"

        # when
        deck.render(str(output))

        # then
        presentation = Presentation(str(output))
        assert presentation.slide_width == 1280 * 9525
        assert presentation.slide_height == 720 * 9525


class TestDiagnose:
    """Deck-level diagnostics aggregate per-slide findings and deck-wide issues."""

    def test_should_tag_slide_findings_with_slide_index(self):
        """Per-slide diagnostics carry the originating slide index."""
        # given a slide whose text runs off the canvas
        offending = Canvas(1280, 720).text(
            content="hi", size=64, color="#FFFFFF", position=("200%", "50%")
        )
        deck = Deck().add(make_slide("ok"), offending)

        # when
        findings = deck.diagnose()

        # then
        off_canvas = [f for f in findings if f.code == "off-canvas"]
        assert off_canvas
        assert all(f.slide_index == 1 for f in off_canvas)

    def test_should_warn_when_slides_have_mixed_sizes(self):
        """Differing slide dimensions raise a single deck-wide warning."""
        # given
        deck = Deck().add(make_slide("a", 1280, 720), make_slide("b", 800, 800))

        # when
        findings = deck.diagnose()

        # then
        mixed = [f for f in findings if f.code == "mixed-slide-size"]
        assert len(mixed) == 1
        assert mixed[0].slide_index is None
        assert mixed[0].severity == "warning"

    def test_should_not_warn_when_slides_share_a_size(self):
        """Uniformly sized slides produce no mixed-size warning."""
        # given
        deck = Deck().add(make_slide("a"), make_slide("b"))

        # when
        findings = deck.diagnose()

        # then
        assert not [f for f in findings if f.code == "mixed-slide-size"]


class TestContactSheet:
    """Composing slides into a single grid image."""

    def test_should_lay_out_slides_in_a_grid_canvas(self, tmp_path: Path):
        """contact_sheet() returns a renderable Canvas sized for the grid."""
        # given
        deck = Deck().add(make_slide("1"), make_slide("2"), make_slide("3"))

        # when
        sheet = deck.contact_sheet(columns=2, thumb_width=400, gap=20, padding=20)
        output = tmp_path / "grid.png"
        sheet.render(str(output))

        # then: 2 columns, 2 rows for 3 slides
        cell_h = round(400 * 720 / 1280)
        expected_width = 20 * 2 + 2 * 400 + 20
        expected_height = 20 * 2 + 2 * cell_h + 20
        assert (sheet.width, sheet.height) == (expected_width, expected_height)
        assert Image.open(output).size == (expected_width, expected_height)

    def test_should_clamp_columns_to_slide_count(self):
        """Requesting more columns than slides collapses to a single row."""
        # given
        deck = Deck().add(make_slide("1"), make_slide("2"))

        # when: 4 columns requested for 2 slides
        sheet = deck.contact_sheet(columns=4, thumb_width=400, gap=20, padding=20)

        # then: only 2 cells wide, one row tall
        cell_h = round(400 * 720 / 1280)
        assert sheet.width == 20 * 2 + 2 * 400 + 20
        assert sheet.height == 20 * 2 + cell_h

    def test_should_reject_non_positive_columns(self):
        """A contact sheet needs at least one column."""
        # given
        deck = Deck().slide(make_slide("1"))

        # when / then
        with pytest.raises(ValidationError, match="columns"):
            deck.contact_sheet(columns=0)


class TestJsonRoundTrip:
    """Decks serialize to and from JSON via the underlying canvas specs."""

    def test_should_round_trip_through_json(self):
        """from_json(to_json()) reproduces every slide's spec."""
        # given
        deck = Deck().add(make_slide("1"), make_slide("2"))

        # when
        restored = Deck.from_json(deck.to_json())

        # then
        assert len(restored) == 2
        assert [c.to_json() for c in restored] == [c.to_json() for c in deck]

    def test_should_reject_json_without_slides(self):
        """Deck JSON must carry a 'slides' list."""
        # when / then
        with pytest.raises(ValidationError, match="slides"):
            Deck.from_json('{"pages": []}')
