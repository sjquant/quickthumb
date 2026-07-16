"""Multi-slide / multi-image decks built on top of Canvas.

A Deck is an ordered collection of Canvas objects ("slides"). It renders to a
multi-page PDF, a multi-slide PPTX, an animated GIF/WebM/MP4, or a numbered
sequence of raster images, reusing the exact same per-canvas render pipeline
so every slide looks identical to rendering that Canvas on its own.
"""

from __future__ import annotations

import contextlib
import math
import os
import tempfile
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from typing_extensions import Self

from quickthumb._base import FileFormat, aspect_ratio_dimensions
from quickthumb.canvas import Canvas
from quickthumb.errors import RenderingError, ValidationError
from quickthumb.models import (
    AudioTrack,
    GifOptions,
    VideoOptions,
    coerce_audio_track,
)
from quickthumb.transitions import Transition, coerce_transition

if TYPE_CHECKING:
    from quickthumb._export_video import AnimationFormat

_DOCUMENT_EXTENSIONS = {".pdf", ".pptx", ".html", ".htm"}
_RASTER_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
_ANIMATION_EXTENSIONS = {".gif", ".webm"}


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
        # Slide transitions are a deck concern: a deck-wide default
        # plus an optional per-slide override kept parallel to ``_slides``. The
        # Canvas itself stays unaware of transitions.
        self._transition = self._coerce_transition(transition)
        self._slides: list[Canvas] = []
        self._slide_transitions: list[Transition | None] = []
        self._slide_audio: list[AudioTrack | None] = []
        self._slide_durations: list[float | None] = []
        for slide in slides or []:
            self._append_slide(slide)

    @staticmethod
    def _coerce_transition(value: Transition | dict | str | None) -> Transition | None:
        return coerce_transition(value)

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

    def transition(self, transition: Transition | dict | str) -> Self:
        """Set the default slide transition for slides that don't set their own.

        Pass a transition effect object (e.g. ``Fade()`` or ``Push(direction="left")``
        from ``quickthumb.transitions``), a dict, or an effect string. A slide that
        sets its own transition (via ``Deck.slide(..., transition=...)``) overrides
        this default. Honoured by PPTX and HTML export.
        """
        self._transition = self._coerce_transition(transition)
        return self

    @property
    def default_transition(self) -> Transition | None:
        """The deck-wide default slide transition, if set."""
        return self._transition

    def slide(
        self,
        canvas: Canvas,
        transition: Transition | dict | str | None = None,
        *,
        audio: AudioTrack | str | dict | None = None,
        duration: float | None = None,
    ) -> Self:
        """Append a single Canvas as the next slide (chainable).

        Pass ``transition`` to set this slide's transition inline; it overrides
        the deck default for this slide only. ``audio`` supplies this slide's
        MP4 narration, while ``duration`` trims or pads it to an exact length.
        """
        # Validate the transition before mutating state so a bad value can't
        # leave a half-added slide behind.
        override = self._coerce_transition(transition)
        if duration is not None and (
            not isinstance(duration, (int, float))
            or isinstance(duration, bool)
            or not math.isfinite(duration)
            or duration <= 0
        ):
            raise ValidationError("duration must be a finite value > 0")
        normalized_audio = coerce_audio_track(audio)
        self._append_slide(canvas)
        if override is not None:
            self._slide_transitions[-1] = override
        self._slide_audio[-1] = normalized_audio
        self._slide_durations[-1] = duration
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
        self._slide_audio.append(None)
        self._slide_durations.append(None)

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
        animation: GifOptions | VideoOptions | None = None,
    ) -> list[str]:
        """Render the deck, dispatching on the output extension.

        ``.pdf`` and ``.pptx`` produce a single multi-page/multi-slide document.
        ``.gif`` and ``.webm`` produce one animation that plays each slide's
        layer animations and transitions. ``.mp4`` renders static slides with
        per-slide narration unless ``animation=VideoOptions(...)`` is supplied,
        in which case it uses the animated timeline. Raster
        extensions (``.png``, ``.jpg``, ``.jpeg``, ``.webp``) write one file per
        slide as a zero-padded
        numbered sequence derived from ``output_path`` (e.g. ``slides.png`` ->
        ``slides_01.png``, ``slides_02.png``). Pass ``GifOptions`` for GIF or
        ``VideoOptions`` for MP4/WebM to tune animated output. Returns the list
        of written file paths (unlike
        ``Canvas.render``, which returns None).
        """
        self._require_slides()
        extension = os.path.splitext(output_path)[1].lower()

        if animation is not None and extension not in (*_ANIMATION_EXTENSIONS, ".mp4"):
            raise RenderingError(
                "animation options require an animated output extension (.gif, .mp4, or .webm)."
            )

        if extension == ".mp4" and animation is None:
            if quality is not None:
                raise RenderingError(
                    "Quality parameter is only supported for JPEG and WEBP formats, "
                    "not .mp4 output."
                )
            if format is not None:
                raise RenderingError(
                    "format override is only supported for raster output, not .mp4 output."
                )
            self.render_mp4(output_path)
            return [output_path]

        if extension in (*_ANIMATION_EXTENSIONS, ".mp4"):
            if quality is not None:
                raise RenderingError(
                    "Quality parameter is only supported for JPEG and WEBP formats, "
                    f"not {extension} output."
                )
            if format is not None:
                raise RenderingError(
                    "format override is only supported for raster output, "
                    f"not {extension} animations."
                )
            self._render_animated_file(
                output_path,
                cast("AnimationFormat", extension[1:]),
                animation,
            )
            return [output_path]

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
                "Render slides individually with Canvas.to_svg(), or use .pdf, .pptx, or .html."
            )

        raise RenderingError(
            f"Unsupported deck output format: {extension or output_path!r}.\n"
            "Use .pdf, .pptx, .html, an animated extension (.gif, .webm), .mp4 for "
            "narrated slides, or a raster extension (.png, .jpg, .jpeg, .webp)."
        )

    def _render_animated_file(
        self,
        output_path: str,
        format: AnimationFormat,
        animation: GifOptions | VideoOptions | None = None,
    ) -> None:
        """Render an animated Deck, mixing scheduled narration when requested."""
        from quickthumb._export_video import write_animation

        if format == "gif":
            write_animation(
                self._slides,
                self._resolved_transitions(),
                output_path,
                format=format,
                animation=animation,
            )
            return
        if isinstance(animation, GifOptions):
            raise ValidationError("GifOptions are only supported for GIF output")
        slide_durations, audio_durations = self._animation_audio_schedule()
        write_animation(
            self._slides,
            self._resolved_transitions(),
            output_path,
            format=format,
            slide_audio=self._slide_audio,
            slide_durations=slide_durations,
            audio_durations=audio_durations,
            animation=animation,
        )

    def _animation_audio_schedule(
        self, default_duration: float = 3.0
    ) -> tuple[list[float | None], list[float]]:
        """Resolve visual overrides and finite durations for the audio mixer."""
        from quickthumb._export_deck_mp4 import ffprobe_binary, resolve_audio_duration

        for audio in self._slide_audio:
            if audio is not None and not os.path.isfile(audio.path):
                raise ValidationError(f"Audio file not found: {audio.path!r}")
        ffprobe = (
            ffprobe_binary()
            if any(
                audio is not None and duration is None
                for audio, duration in zip(self._slide_audio, self._slide_durations, strict=True)
            )
            else ""
        )
        durations = [
            resolve_audio_duration(audio, duration, default_duration, ffprobe)
            for audio, duration in zip(self._slide_audio, self._slide_durations, strict=True)
        ]
        visual_durations = [
            resolved if audio is not None or duration is not None else None
            for audio, duration, resolved in zip(
                self._slide_audio,
                self._slide_durations,
                durations,
                strict=True,
            )
        ]
        return visual_durations, durations

    def _render_document(self, output_path: str, extension: str) -> None:
        if extension == ".pdf":
            from quickthumb._export_pdf import PdfExporter

            PdfExporter().save_canvases(self._slides, output_path)
            return

        if extension in (".html", ".htm"):
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(self.to_html())
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

    def to_html(self, responsive: bool = True, embed_fonts: bool = True) -> str:
        """Render the deck to a standalone HTML slideshow document string.

        Each slide becomes a fixed-size stage; the runtime shows one at a time
        and advances on click (running that slide's per-layer animations first,
        then moving to the next slide) or with the arrow keys. Each slide's
        ``transition`` animates the change into it (the incoming slide), with
        slides that set none falling back to a cross-fade. With
        ``responsive=True`` (default) the active stage is scaled to fill the
        viewport. ``embed_fonts`` defaults to ``True`` so the slideshow carries
        its fonts and renders identically on any machine; pass ``False`` for a
        smaller file that relies on the viewer's system fonts. This is the one
        *interactive* format where transitions and animations play; the
        animated GIF/WebM exports play them too, on a fixed timeline.
        """
        self._require_slides()
        from quickthumb._export_html import export_deck

        return export_deck(
            self._slides,
            embed_fonts=embed_fonts,
            responsive=responsive,
            transitions=self._resolved_transitions(),
        )

    def to_pptx(self) -> bytes:
        """Render the deck to a multi-slide PPTX as bytes (requires quickthumb[pptx])."""
        self._require_slides()
        from quickthumb._export_pptx import PptxExporter

        return PptxExporter().export_bytes_canvases(
            self._slides, transitions=self._resolved_transitions()
        )

    def to_gif(
        self,
        fps: float = 20.0,
        slide_duration: float = 3.0,
        loop: int = 0,
        matte: str = "#000000",
    ) -> bytes:
        """Render the deck to animated GIF bytes.

        Each slide plays its layer animations, holds its settled state, then
        its transition animates the change into the next slide (a slide with
        no transition set cross-fades in over 0.5s; slide 0 with none starts
        instantly). ``on_click`` animations play automatically in sequence --
        there are no clicks in a video. A slide holds for its transition's
        ``advance_after`` when set, else for ``slide_duration`` seconds after
        its animations finish. ``loop`` is the GIF repeat count (0 = forever).
        Frames are composited onto the opaque ``matte`` color, and mixed-size
        slides are letterboxed onto the first slide's size.
        """
        self._require_slides()
        from quickthumb._export_video import export_animation_bytes

        return export_animation_bytes(
            self._slides,
            self._resolved_transitions(),
            format="gif",
            fps=fps,
            slide_duration=slide_duration,
            loop=loop,
            matte=matte,
        )

    def to_mp4(
        self,
        fps: float = 30.0,
        slide_duration: float = 3.0,
    ) -> bytes:
        """Return a static, narrated Deck MP4 as bytes.

        Every slide becomes a still frame. Its optional ``audio`` is used as
        narration; its ``duration`` overrides that audio's length, and silent
        slides use ``slide_duration``. Layer animations and transitions are
        not played by this Deck-specific MP4 export.
        """
        self._require_slides()
        descriptor, output_path = tempfile.mkstemp(suffix=".mp4")
        os.close(descriptor)
        try:
            self.render_mp4(output_path, default_duration=slide_duration, fps=fps)
            with open(output_path, "rb") as rendered:
                return rendered.read()
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.remove(output_path)

    def to_animated_mp4(
        self,
        fps: float = 30.0,
        slide_duration: float = 3.0,
        matte: str = "#000000",
        soundtrack: AudioTrack | str | dict | None = None,
        loop_audio: bool | None = None,
    ) -> bytes:
        """Render the Deck's animated timeline to MP4 bytes.

        Unlike ``to_mp4()``, this path plays layer animations and slide
        transitions. Per-slide narration and the optional ``soundtrack`` are
        mixed into the complete timeline; a narration without an explicit
        duration holds its slide for the source audio length.
        """
        self._require_slides()
        return self._export_animated_video_bytes(
            format="mp4",
            fps=fps,
            slide_duration=slide_duration,
            matte=matte,
            soundtrack=soundtrack,
            loop_audio=loop_audio,
        )

    def _export_animated_video_bytes(
        self,
        *,
        format: AnimationFormat,
        fps: float,
        slide_duration: float,
        matte: str,
        soundtrack: AudioTrack | str | dict | None,
        loop_audio: bool | None,
    ) -> bytes:
        """Export animated MP4/WebM bytes with the Deck's narration schedule."""
        from quickthumb._export_video import export_animation_bytes

        slide_durations, audio_durations = self._animation_audio_schedule(slide_duration)
        return export_animation_bytes(
            self._slides,
            self._resolved_transitions(),
            format=format,
            fps=fps,
            slide_duration=slide_duration,
            matte=matte,
            soundtrack=soundtrack,
            loop_audio=loop_audio,
            slide_audio=self._slide_audio,
            slide_durations=slide_durations,
            audio_durations=audio_durations,
        )

    def render_mp4(
        self, output_path: str, default_duration: float = 3.0, fps: float = 30.0
    ) -> None:
        """Render static slides and their per-slide AAC audio into an MP4 file.

        Requires ``ffmpeg`` and ``ffprobe``. The first slide defines the video
        dimensions (rounded down to even yuv420p dimensions); other slides are
        letterboxed. Every output includes an AAC audio stream, including for
        silent slides. This initial MP4 path intentionally does not play deck
        transitions or layer animations.
        """
        self._require_slides()
        from quickthumb._export_deck_mp4 import render_deck_mp4

        render_deck_mp4(
            self._slides,
            self._slide_audio,
            self._slide_durations,
            output_path,
            default_duration=default_duration,
            fps=fps,
        )

    def to_webm(
        self,
        fps: float = 30.0,
        slide_duration: float = 3.0,
        matte: str = "#000000",
        soundtrack: AudioTrack | str | dict | None = None,
        loop_audio: bool | None = None,
    ) -> bytes:
        """Render the deck to WebM (VP9) bytes; timing model as in ``to_gif``.

        Requires the ``ffmpeg`` binary on PATH (or ``QUICKTHUMB_FFMPEG``).
        Odd-sized canvases lose their last pixel row/column (VP9 4:2:0 output
        needs even dimensions). Per-slide narration and ``soundtrack`` are
        mixed as Opus and trimmed to the video length; a narration without an
        explicit duration holds its slide for the source audio length.
        ``loop_audio`` overrides `AudioTrack.loop`, while legacy string paths
        continue to loop by default.
        """
        self._require_slides()
        return self._export_animated_video_bytes(
            format="webm",
            fps=fps,
            slide_duration=slide_duration,
            matte=matte,
            soundtrack=soundtrack,
            loop_audio=loop_audio,
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
        for canvas, override, audio, duration in zip(
            self._slides,
            self._slide_transitions,
            self._slide_audio,
            self._slide_durations,
            strict=True,
        ):
            slide = json.loads(canvas.to_json())
            # Per-slide overrides live on the deck, so attach them to the slide
            # dict here rather than in Canvas.to_json (which knows nothing of them).
            if override is not None:
                slide["transition"] = json.loads(override.model_dump_json())
            if audio is not None:
                slide["audio"] = audio.model_dump()
            if duration is not None:
                slide["duration"] = duration
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
                audio = slide.get("audio")
                duration = slide.get("duration")
                slide = {
                    key: value
                    for key, value in slide.items()
                    if key not in {"transition", "audio", "duration"}
                }
                # Share the deck-level theme so $theme.* tokens resolve; a slide's
                # own theme block takes precedence.
                if theme:
                    slide = {**slide, "theme": {**theme, **slide.get("theme", {})}}
            deck.slide(
                Canvas.from_json(json.dumps(slide)),
                transition=override,
                audio=audio,
                duration=duration,
            )
        return deck
