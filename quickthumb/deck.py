"""Multi-slide / multi-image decks built on top of Canvas.

A Deck is an ordered collection of Canvas objects ("slides"). It renders to a
multi-page PDF, a multi-slide PPTX, or a numbered sequence of raster images,
reusing the exact same per-canvas render pipeline so every slide looks
identical to rendering that Canvas on its own.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from typing_extensions import Self

from quickthumb._base import FileFormat, aspect_ratio_dimensions
from quickthumb.canvas import Canvas
from quickthumb.errors import RenderingError, ValidationError
from quickthumb.models import Transition

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
        theme: dict | None = None,
        transition: Transition | dict | str | None = None,
    ):
        if (width is None) != (height is None):
            raise ValidationError("Provide both width and height, or neither.")
        if width is not None and width <= 0:
            raise ValidationError("width must be > 0")
        if height is not None and height <= 0:
            raise ValidationError("height must be > 0")
        if theme is not None and not isinstance(theme, dict):
            raise ValidationError("theme must be a dict of token groups.")

        self._width = width
        self._height = height
        self._theme = theme or {}
        # Slide transitions are a deck concern (PPTX-only): a deck-wide default
        # plus an optional per-slide override kept parallel to ``_slides``. The
        # Canvas itself stays unaware of transitions.
        self._transition = self._coerce_transition(transition)
        self._slides: list[Canvas] = []
        self._slide_transitions: list[Transition | None] = []
        for slide in slides or []:
            self._append_slide(slide)

    @staticmethod
    def _coerce_transition(value: Transition | dict | str | None) -> Transition | None:
        if value is None or isinstance(value, Transition):
            return value
        if isinstance(value, str):
            return Transition(effect=value)  # type: ignore[arg-type]  # validated by the model
        if isinstance(value, dict):
            return Transition.model_validate(value)
        raise ValidationError("transition must be a Transition, a dict, a string, or None.")

    @classmethod
    def from_aspect_ratio(cls, ratio: str, base_width: int) -> Self:
        """Create a deck whose default slide size comes from an aspect ratio."""
        width, height = aspect_ratio_dimensions(ratio, base_width)
        return cls(width, height)

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

    def transition(
        self,
        effect: Transition | str = "fade",
        duration: float = 1.0,
        direction: str | None = None,
        advance_on_click: bool = True,
        advance_after: float | None = None,
    ) -> Self:
        """Set the default slide transition for slides that don't set their own.

        Pass a ready-made ``Transition`` as the first argument, or build one from
        keyword arguments. A slide that sets its own transition (via
        ``Deck.slide(..., transition=...)``) overrides this default. Honoured by
        PPTX export only.
        """
        if isinstance(effect, Transition):
            self._transition = effect
        else:
            self._transition = Transition(
                effect=effect,  # type: ignore[arg-type]  # validated by the model
                duration=duration,
                direction=direction,  # type: ignore[arg-type]
                advance_on_click=advance_on_click,
                advance_after=advance_after,
            )
        return self

    @property
    def default_transition(self) -> Transition | None:
        """The deck-wide default slide transition, if set."""
        return self._transition

    def slide(
        self, canvas: Canvas, transition: Transition | dict | str | None = None
    ) -> Self:
        """Append a single Canvas as the next slide (chainable).

        Pass ``transition`` to set this slide's transition inline; it overrides
        the deck default for this slide only.
        """
        # Validate the transition before mutating state so a bad value can't
        # leave a half-added slide behind.
        override = self._coerce_transition(transition)
        self._append_slide(canvas)
        if override is not None:
            self._slide_transitions[-1] = override
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
        # Stay aligned with _slides; slide() may overwrite this with an override.
        self._slide_transitions.append(None)

    def _resolved_transitions(self) -> list[Transition | None]:
        """The effective transition per slide: its own override, else the default."""
        return [override or self._transition for override in self._slide_transitions]

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
        ``slides_02.png``). Returns the list of written file paths (unlike
        ``Canvas.render``, which returns None).
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

            PdfExporter().save_canvases(self._slides, output_path)
            return

        from quickthumb._export_pptx import PptxExporter

        PptxExporter().save_canvases(
            self._slides, output_path, transitions=self._resolved_transitions()
        )

    def _render_sequence(
        self, output_path: str, format: FileFormat | None, quality: int | None
    ) -> list[str]:
        # Validate every slide's assets up front so a missing image fails before
        # any file is written, leaving no partial sequence on disk (matching the
        # all-or-nothing behaviour of the PDF/PPTX paths).
        for canvas in self._slides:
            canvas._validate_image_paths()

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

        return PdfExporter().export_bytes_canvases(self._slides)

    def to_pptx(self) -> bytes:
        """Render the deck to a multi-slide PPTX as bytes (requires quickthumb[pptx])."""
        self._require_slides()
        from quickthumb._export_pptx import PptxExporter

        return PptxExporter().export_bytes_canvases(
            self._slides, transitions=self._resolved_transitions()
        )

    def diagnose(self) -> list[DeckDiagnostic]:
        """Collect per-slide diagnostics plus deck-wide layout warnings.

        Each slide's Canvas.diagnose() findings are returned tagged with their
        ``slide_index``. When slides do not all share the same dimensions a
        single ``mixed-slide-size`` warning is prepended, since PPTX uses one
        page size for the whole deck and viewers may letterbox the rest.
        """
        findings: list[DeckDiagnostic] = []

        # Every slide is guaranteed sized: _append_slide is the only way into
        # _slides and it either inherits the deck size or rejects an unsized
        # canvas, so reading .width/.height here cannot raise.
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

    def to_json(self) -> str:
        import json

        payload: dict = {}
        if self._width is not None:
            payload["width"] = self._width
            payload["height"] = self._height
        if self._theme:
            payload["theme"] = self._theme
        if self._transition is not None:
            payload["transition"] = json.loads(self._transition.model_dump_json())
        slides = []
        for canvas, override in zip(self._slides, self._slide_transitions, strict=True):
            slide = json.loads(canvas.to_json())
            # Per-slide overrides live on the deck, so attach them to the slide
            # dict here rather than in Canvas.to_json (which knows nothing of them).
            if override is not None:
                slide["transition"] = json.loads(override.model_dump_json())
            slides.append(slide)
        payload["slides"] = slides
        return json.dumps(payload)

    @classmethod
    def from_json(cls, data: str) -> Self:
        import json

        raw = json.loads(data)
        if not isinstance(raw, dict) or "slides" not in raw:
            raise ValidationError("Deck JSON must be an object with a 'slides' list.")
        slides_raw = raw["slides"]
        if not isinstance(slides_raw, list):
            raise ValidationError("Deck 'slides' must be a list of canvas specs.")

        theme = raw.get("theme", {})
        if not isinstance(theme, dict):
            raise ValidationError("Deck 'theme' must be an object of token groups.")

        transition = raw.get("transition")
        if transition is not None and not isinstance(transition, dict):
            raise ValidationError("Deck 'transition' must be a JSON object.")

        deck = cls(
            width=raw.get("width"),
            height=raw.get("height"),
            theme=theme or None,
            transition=transition,
        )
        for slide in slides_raw:
            override = None
            if isinstance(slide, dict):
                # Lift the per-slide transition off the spec before it reaches
                # Canvas.from_json, which does not understand transitions.
                override = slide.get("transition")
                slide = {key: value for key, value in slide.items() if key != "transition"}
                # Share the deck-level theme so $theme.* tokens resolve; a slide's
                # own theme block takes precedence.
                if theme:
                    slide = {**slide, "theme": {**theme, **slide.get("theme", {})}}
            deck.slide(Canvas.from_json(json.dumps(slide)), transition=override)
        return deck
