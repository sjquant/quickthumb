"""Multi-slide / multi-image decks built on top of Canvas.

A Deck is an ordered collection of Canvas objects ("slides"). It renders to a
multi-page PDF, a multi-slide PPTX, a numbered sequence of raster images, or a
single contact-sheet grid, reusing the exact same per-canvas render pipeline so
every slide looks identical to rendering that Canvas on its own.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from PIL import Image
from typing_extensions import Self

from quickthumb._base import FileFormat
from quickthumb.canvas import Canvas
from quickthumb.errors import RenderingError, ValidationError

_DOCUMENT_EXTENSIONS = {".pdf", ".pptx"}
_RASTER_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass
class DeckDiagnostic:
    """A single deck-level finding.

    Slide findings mirror Canvas.diagnose() entries but carry the originating
    ``slide_index``; deck-wide findings (such as mixed slide sizes) use a
    ``slide_index`` of None and a ``layer_index`` of None.
    """

    code: str
    severity: str
    message: str
    slide_index: int | None = None
    layer_index: int | None = None


class Deck:
    """An ordered collection of Canvas slides with multi-output export.

    A deck can carry a default slide size. Unsized canvases added to it inherit
    that size, so slides can be written as bare ``Canvas()`` without repeating the
    dimensions; an explicitly sized canvas keeps its own size.
    """

    def __init__(
        self,
        width: int | None = None,
        height: int | None = None,
        slides: list[Canvas] | None = None,
    ):
        if (width is None) != (height is None):
            raise ValidationError("Provide both width and height, or neither.")
        if width is not None and width <= 0:
            raise ValidationError("width must be > 0")
        if height is not None and height <= 0:
            raise ValidationError("height must be > 0")

        self._width = width
        self._height = height
        self._slides: list[Canvas] = []
        for slide in slides or []:
            self._append_slide(slide)

    @classmethod
    def from_aspect_ratio(cls, ratio: str, base_width: int) -> Self:
        """Create a deck whose default slide size comes from an aspect ratio."""
        width_ratio, height_ratio = ratio.split(":")
        calculated_height = int(base_width * int(height_ratio) / int(width_ratio))
        return cls(base_width, calculated_height)

    @property
    def slides(self) -> list[Canvas]:
        # Return a copy so callers cannot bypass the Canvas type guard in
        # _append_slide by mutating the internal list directly.
        return list(self._slides)

    def __len__(self) -> int:
        return len(self._slides)

    def __iter__(self):
        return iter(self._slides)

    def __getitem__(self, index: int) -> Canvas:
        return self._slides[index]

    def slide(self, canvas: Canvas) -> Self:
        """Append a single Canvas as the next slide (chainable)."""
        self._append_slide(canvas)
        return self

    def add(self, *canvases: Canvas) -> Self:
        """Append several Canvas slides at once (chainable)."""
        for canvas in canvases:
            self._append_slide(canvas)
        return self

    def _append_slide(self, canvas: Canvas) -> None:
        if not isinstance(canvas, Canvas):
            raise ValidationError("Deck slides must be Canvas instances.")
        if not canvas.has_size:
            if self._width is None or self._height is None:
                raise ValidationError(
                    "This slide has no size and the deck has no default size. "
                    "Give the deck a size (Deck(width, height)) or size the Canvas."
                )
            canvas._inherit_size(self._width, self._height)
        self._slides.append(canvas)

    def _require_slides(self) -> None:
        if not self._slides:
            raise RenderingError("Deck has no slides to render.")

    def render(
        self,
        output_path: str,
        format: FileFormat | None = None,
        quality: int | None = None,
    ) -> list[str]:
        """Render the deck, dispatching on the output extension.

        ``.pdf`` and ``.pptx`` produce a single multi-page/multi-slide document.
        Raster extensions (``.png``, ``.jpg``, ``.jpeg``, ``.webp``) write one
        file per slide as a zero-padded numbered sequence derived from
        ``output_path`` (e.g. ``slides.png`` -> ``slides_01.png``,
        ``slides_02.png``). Returns the list of written file paths.
        """
        self._require_slides()
        extension = os.path.splitext(output_path)[1].lower()

        if extension in _DOCUMENT_EXTENSIONS:
            if quality is not None:
                raise RenderingError(
                    "Quality parameter is only supported for JPEG and WEBP formats, "
                    f"not {extension} output."
                )
            if format is not None:
                raise RenderingError(
                    "format override is only supported for raster output, "
                    f"not {extension} documents."
                )
            self._render_document(output_path, extension)
            return [output_path]

        if extension in _RASTER_EXTENSIONS:
            return self._render_sequence(output_path, format, quality)

        if extension == ".svg":
            raise RenderingError(
                "A deck cannot render to a single .svg file (SVG has no multi-page form). "
                "Render slides individually with Canvas.to_svg(), or use .pdf or .pptx."
            )

        raise RenderingError(
            f"Unsupported deck output format: {extension or output_path!r}.\n"
            "Use .pdf, .pptx, or a raster extension (.png, .jpg, .jpeg, .webp)."
        )

    def _render_document(self, output_path: str, extension: str) -> None:
        if extension == ".pdf":
            from quickthumb._export_pdf import PdfExporter

            PdfExporter(self._slides[0]).save_canvases(self._slides, output_path)
            return

        from quickthumb._export_pptx import PptxExporter

        PptxExporter(self._slides[0]).save_canvases(self._slides, output_path)

    def _render_sequence(
        self, output_path: str, format: FileFormat | None, quality: int | None
    ) -> list[str]:
        stem, extension = os.path.splitext(output_path)
        pad = max(2, len(str(len(self._slides))))
        written: list[str] = []
        for index, canvas in enumerate(self._slides, start=1):
            slide_path = f"{stem}_{index:0{pad}d}{extension}"
            canvas.render(slide_path, format=format, quality=quality)
            written.append(slide_path)
        return written

    def to_pdf(self) -> bytes:
        """Render the deck to a multi-page PDF as bytes (requires quickthumb[pdf])."""
        self._require_slides()
        from quickthumb._export_pdf import PdfExporter

        return PdfExporter(self._slides[0]).export_bytes_canvases(self._slides)

    def to_pptx(self) -> bytes:
        """Render the deck to a multi-slide PPTX as bytes (requires quickthumb[pptx])."""
        self._require_slides()
        from quickthumb._export_pptx import PptxExporter

        return PptxExporter(self._slides[0]).export_bytes_canvases(self._slides)

    def diagnose(self) -> list[DeckDiagnostic]:
        """Collect per-slide diagnostics plus deck-wide layout warnings.

        Each slide's Canvas.diagnose() findings are returned tagged with their
        ``slide_index``. When slides do not all share the same dimensions a
        single ``mixed-slide-size`` warning is prepended, since PPTX uses one
        page size for the whole deck and viewers may letterbox the rest.
        """
        findings: list[DeckDiagnostic] = []

        sizes = {(canvas.width, canvas.height) for canvas in self._slides}
        if len(sizes) > 1:
            findings.append(
                DeckDiagnostic(
                    code="mixed-slide-size",
                    severity="warning",
                    message=(
                        "Slides have differing dimensions "
                        f"({', '.join(f'{w}x{h}' for w, h in sorted(sizes))}). "
                        "PPTX export uses the first slide's size for the whole deck."
                    ),
                )
            )

        for slide_index, canvas in enumerate(self._slides):
            for finding in canvas.diagnose():
                findings.append(
                    DeckDiagnostic(
                        code=finding.code,
                        severity=finding.severity,
                        message=finding.message,
                        slide_index=slide_index,
                        layer_index=finding.layer_index,
                    )
                )
        return findings

    def contact_sheet(
        self,
        columns: int = 3,
        thumb_width: int = 480,
        gap: int = 24,
        padding: int = 24,
        background: str = "#FFFFFF",
    ) -> Canvas:
        """Compose the slides into a single grid image, returned as a Canvas.

        Each slide is rendered and contained (letterboxed) into a uniform cell
        sized from the first slide's aspect ratio. The returned Canvas can be
        rendered to any raster format like a normal canvas.
        """
        self._require_slides()
        if columns < 1:
            raise ValidationError("columns must be >= 1")
        if thumb_width < 1:
            raise ValidationError("thumb_width must be >= 1")

        first = self._slides[0]
        cell_w = thumb_width
        cell_h = max(1, round(thumb_width * first.height / first.width))

        cols = min(columns, len(self._slides))
        rows = -(-len(self._slides) // cols)  # ceil division
        sheet_w = padding * 2 + cols * cell_w + (cols - 1) * gap
        sheet_h = padding * 2 + rows * cell_h + (rows - 1) * gap

        thumbnails = [self._slide_thumbnail(canvas, cell_w, cell_h) for canvas in self._slides]

        def draw_grid(base: Image.Image) -> Image.Image:
            from PIL import ImageColor

            sheet = Image.new("RGBA", base.size, ImageColor.getrgb(background) + (255,))
            for index, thumb in enumerate(thumbnails):
                row, col = divmod(index, cols)
                cell_x = padding + col * (cell_w + gap)
                cell_y = padding + row * (cell_h + gap)
                offset_x = cell_x + (cell_w - thumb.width) // 2
                offset_y = cell_y + (cell_h - thumb.height) // 2
                sheet.alpha_composite(thumb, (offset_x, offset_y))
            return sheet

        return Canvas(sheet_w, sheet_h).custom(draw_grid)

    def _slide_thumbnail(self, canvas: Canvas, cell_w: int, cell_h: int) -> Image.Image:
        # Validate up front so a missing image fails with a clean FileNotFoundError,
        # matching render()/to_pdf()/to_pptx() rather than crashing mid-render.
        canvas._validate_image_paths()
        image = canvas._render_to_image()
        scale = min(cell_w / image.width, cell_h / image.height)
        size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
        return image.resize(size, Image.LANCZOS)

    def to_json(self) -> str:
        import json as _json

        slides = [_json.loads(canvas.to_json()) for canvas in self._slides]
        return _json.dumps({"slides": slides})

    @classmethod
    def from_json(cls, data: str) -> Self:
        import json as _json

        raw = _json.loads(data)
        if not isinstance(raw, dict) or "slides" not in raw:
            raise ValidationError("Deck JSON must be an object with a 'slides' list.")
        slides_raw = raw["slides"]
        if not isinstance(slides_raw, list):
            raise ValidationError("Deck 'slides' must be a list of canvas specs.")

        slides = [Canvas.from_json(_json.dumps(slide)) for slide in slides_raw]
        return cls(slides=slides)
