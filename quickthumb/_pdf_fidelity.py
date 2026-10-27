"""Opt-in PDFium observations of the actual authored-static PDF bytes."""

from __future__ import annotations

from threading import Lock
from typing import TYPE_CHECKING

from quickthumb._svg_fidelity import compare_pixels
from quickthumb.errors import RenderingError
from quickthumb.models.document import _FidelityMetrics
from quickthumb.models.options import _FidelityLimits

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas


_PDFIUM_LOCK = Lock()


def measure_pdf_fidelity(
    canvas: Canvas, document: bytes, limits: _FidelityLimits
) -> _FidelityMetrics:
    limits = limits.copy()
    try:
        import pypdfium2 as pdfium
        from pypdfium2 import version
    except (ImportError, OSError) as error:
        raise RenderingError(
            f"PDF fidelity comparison requires PDFium: {error}",
            code="fidelity_unavailable",
            suggestion="install quickthumb[pdf] or omit the PDF fidelity policy",
        ) from error
    reference = canvas.sample()
    try:
        with _PDFIUM_LOCK, pdfium.PdfDocument(document) as pdf:
            page_count = len(pdf)
            page = pdf[0]
            try:
                page_size = page.get_size()
                bitmap = page.render(scale=1, fill_color=(0, 0, 0, 0))
                try:
                    actual = bitmap.to_pil().convert("RGBA")
                finally:
                    bitmap.close()
            finally:
                page.close()
    except Exception as error:
        raise RenderingError(
            f"PDFium could not compare the authored-static PDF: {error}",
            code="fidelity_comparison_failed",
            suggestion="check the PDF and PDFium environment; no output was written",
        ) from error
    metrics = compare_pixels(reference.frames[0].to_image(), actual, limits)
    if page_count != 1 or page_size != (canvas.width, canvas.height):
        metrics["verdict"] = "out_of_policy"
    return _FidelityMetrics(
        renderer="pdfium",
        renderer_version=str(version.PDFIUM_INFO),
        binding_version=str(version.PYPDFIUM_INFO),
        canonical_environment=reference.environment,
        limits=limits,
        actual_width=actual.width,
        actual_height=actual.height,
        page_count=page_count,
        page_size_points=page_size,
        render_scale=1,
        **metrics,
    )
