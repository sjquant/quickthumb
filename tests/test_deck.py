"""Tests for Deck: multi-slide / multi-image collections of Canvas objects."""

import json
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
        deck = Deck(slides=[first]).slide(second).add(third)

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


class TestDefaultSize:
    """A deck size lets slides be written as bare, unsized canvases."""

    def test_should_inject_deck_size_into_unsized_slides(self):
        """An unsized Canvas added to a sized deck inherits the deck dimensions."""
        # given a deck with a default size and bare canvases
        deck = (
            Deck(1280, 720)
            .slide(Canvas().background(color="#101820"))
            .slide(Canvas().background(color="#1A1A2E"))
        )

        # then both slides take the deck size
        assert [(c.width, c.height) for c in deck] == [(1280, 720), (1280, 720)]

    def test_should_keep_explicit_slide_size_over_deck_default(self):
        """An explicitly sized canvas keeps its own dimensions inside a sized deck."""
        # given
        deck = Deck(1280, 720).slide(Canvas(1080, 1080).background(color="#101820"))

        # then the explicit size wins
        assert (deck[0].width, deck[0].height) == (1080, 1080)

    def test_should_derive_default_size_from_aspect_ratio(self):
        """from_aspect_ratio sets the deck default that unsized slides inherit."""
        # given
        deck = Deck.from_aspect_ratio("16:9", 1280).slide(Canvas().background(color="#101820"))

        # then
        assert (deck[0].width, deck[0].height) == (1280, 720)

    def test_should_reject_a_malformed_aspect_ratio(self):
        """A malformed ratio raises the library's ValidationError, not a raw error."""
        # when / then
        with pytest.raises(ValidationError, match="Aspect ratio"):
            Deck.from_aspect_ratio("16-9", 1280)

    def test_should_reject_unsized_slide_without_a_deck_size(self):
        """An unsized slide needs either a deck size or its own size."""
        # given a deck with no default size
        deck = Deck()

        # when / then
        with pytest.raises(ValidationError, match="no default size"):
            deck.slide(Canvas().background(color="#101820"))

    def test_should_reject_rendering_an_unsized_canvas_directly(self, tmp_path: Path):
        """A bare Canvas cannot be rendered until it is given a size."""
        # given
        canvas = Canvas().background(color="#101820")

        # when / then
        with pytest.raises(ValidationError, match="no size yet"):
            canvas.render(str(tmp_path / "out.png"))


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

    def test_should_not_write_partial_sequence_when_a_slide_fails(self, tmp_path: Path):
        """A missing asset on a later slide fails before any file is written."""
        # given a deck whose second slide references a missing image
        broken = make_slide("b").image(str(tmp_path / "missing.png"), position=(0, 0))
        deck = Deck().add(make_slide("a"), broken, make_slide("c"))
        output = tmp_path / "slides.png"

        # when / then: rendering raises and leaves no partial output behind
        with pytest.raises(FileNotFoundError):
            deck.render(str(output))
        assert list(tmp_path.glob("slides_*.png")) == []


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

    def test_should_size_each_pdf_page_to_its_own_slide(self, tmp_path: Path):
        """Unlike PPTX, a mixed-size PDF sizes every page to its slide."""
        # given a deck with two differently shaped slides
        pdfium = require_pypdfium2()
        deck = Deck().add(make_slide("wide", 1280, 720), make_slide("square", 800, 800))
        output = tmp_path / "deck.pdf"

        # when
        deck.render(str(output))

        # then each page keeps its slide's pixel dimensions (1pt per pixel)
        document = pdfium.PdfDocument(str(output))
        assert [tuple(round(v) for v in document[i].get_size()) for i in range(len(document))] == [
            (1280, 720),
            (800, 800),
        ]


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

    def test_should_preserve_default_size_across_json(self):
        """A restored deck keeps its default size so bare slides still inherit it."""
        # given a sized deck round-tripped through JSON
        deck = Deck(1280, 720).add(make_slide("1"))
        restored = Deck.from_json(deck.to_json())

        # when a bare, unsized canvas is added to the restored deck
        restored.slide(Canvas().background(color="#101820"))

        # then it inherits the deck default size instead of raising
        assert (restored[-1].width, restored[-1].height) == (1280, 720)

    def test_should_share_a_deck_level_theme_with_each_slide(self):
        """A top-level theme resolves $theme.* tokens inside every slide."""
        # given a deck spec with a shared theme and a slide that references it
        spec = json.dumps(
            {
                "width": 1280,
                "height": 720,
                "theme": {"brand": "#B8FF00"},
                "slides": [
                    {
                        "width": 1280,
                        "height": 720,
                        "layers": [{"type": "background", "color": "$theme.brand"}],
                    }
                ],
            }
        )

        # when
        deck = Deck.from_json(spec)

        # then the slide's token resolved to the deck-level theme value
        assert deck[0].layers[0].color == "#B8FF00"
        # and the theme survives another round-trip
        assert json.loads(deck.to_json())["theme"] == {"brand": "#B8FF00"}
