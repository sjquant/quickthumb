"""Visual snapshot tests for document exporters.

Each snapshot is a vertical comparison strip: the PIL raster render on top, the
exported document rasterized back to pixels below, separated by a magenta
divider. Open the PNGs in tests/snapshots/ (or view them in a PR diff) to judge
export fidelity the same way as the regular rendering snapshots.

SVG output is rasterized with cairosvg using the repo fonts (fontconfig is
pinned in conftest.py). PPTX output is rasterized with LibreOffice when it is
installed and skipped otherwise.
"""

import os
import shutil
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

import pytest
from inline_snapshot import external_file
from PIL import Image
from quickthumb import Canvas, LinearGradient, RadialGradient, TextPart
from quickthumb.models import Background, Glow, Shadow, Stroke

from tests._optional import require_cairosvg

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_IMAGE = str(FIXTURES_DIR / "sample_image.jpg")
SAMPLE_SVG = str(FIXTURES_DIR / "sample.svg")

SOFFICE = shutil.which("soffice") or shutil.which("libreoffice")


def render_reference(canvas: Canvas) -> Image.Image:
    """Render the canvas through the regular raster pipeline."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "reference.png")
        canvas.render(path)
        return Image.open(path).convert("RGB")


def rasterize_svg(canvas: Canvas) -> Image.Image:
    """Rasterize the SVG export back to pixels."""
    cairosvg = require_cairosvg()
    png_bytes = cairosvg.svg2png(bytestring=canvas.to_svg().encode())
    return Image.open(BytesIO(png_bytes)).convert("RGB")


def rasterize_pptx(canvas: Canvas) -> Image.Image:
    """Rasterize the PPTX export back to pixels via LibreOffice.

    Skips the test when LibreOffice cannot perform the conversion in this
    environment; run with --inline-snapshot=create on a machine with a working
    LibreOffice to (re)generate the PPTX comparison snapshots.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        deck_path = os.path.join(tmpdir, "deck.pptx")
        canvas.render(deck_path)
        try:
            subprocess.run(
                [SOFFICE, "--headless", "--convert-to", "png", "--outdir", tmpdir, deck_path],
                check=True,
                timeout=180,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            image = Image.open(os.path.join(tmpdir, "deck.png")).convert("RGB")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            pytest.skip(f"LibreOffice could not rasterize the PPTX: {e}")
        image.load()
    return image


def comparison_strip(reference: Image.Image, produced: Image.Image) -> bytes:
    """Stack reference (top) and produced (bottom) with a magenta divider."""
    produced = produced.resize(reference.size)
    divider_height = 4
    strip = Image.new(
        "RGB", (reference.width, reference.height * 2 + divider_height), (255, 0, 110)
    )
    strip.paste(reference, (0, 0))
    strip.paste(produced, (0, reference.height + divider_height))
    buffer = BytesIO()
    strip.save(buffer, format="PNG")
    return buffer.getvalue()


def build_vector_shapes_canvas() -> Canvas:
    return (
        Canvas(480, 270)
        .background(
            gradient=LinearGradient(
                angle=35, stops=[("#0F172A", 0.0), ("#7C3AED", 0.6), ("#F472B6", 1.0)]
            )
        )
        .background(
            gradient=RadialGradient(
                stops=[("#FFFFFF40", 0.0), ("#00000000", 0.7)], center=(0.3, 0.4)
            )
        )
        .shape(
            shape="rectangle",
            position=(30, 30),
            width=120,
            height=70,
            color="#22C55E",
            border_radius=14,
        )
        .shape(shape="ellipse", position=(190, 30), width=90, height=70, color="#F59E0BCC")
        .shape(
            shape="pill",
            position=(310, 30),
            width=130,
            height=46,
            color="#3B82F6",
            rotation=18,
        )
        .shape(
            shape="star",
            position=(50, 150),
            width=85,
            height=85,
            color="#FACC15",
            star_points=5,
            effects=[Shadow(offset_x=5, offset_y=6, color="#000000", blur_radius=4)],
        )
        .shape(
            shape="triangle",
            position=(200, 150),
            width=85,
            height=80,
            color="#EF4444",
            opacity=0.85,
        )
        .shape(
            shape="polygon",
            position=(330, 145),
            width=95,
            height=95,
            color="#14B8A6",
            points=[(0.5, 0.0), (1.0, 0.4), (0.8, 1.0), (0.2, 1.0), (0.0, 0.4)],
            effects=[Stroke(width=3, color="#FFFFFF")],
        )
        .outline(width=5, color="#FFFFFF", offset=8, opacity=0.9)
    )


def build_text_styles_canvas() -> Canvas:
    return (
        Canvas(480, 270)
        .background(color="#101826")
        .text(
            content="WRAPPED HEADLINE ACROSS LINES",
            font="Roboto",
            size=36,
            bold=True,
            color="#FFFFFF",
            position=("50%", 24),
            align="top-center",
            max_width=380,
            effects=[Shadow(offset_x=3, offset_y=3, color="#000000", blur_radius=2)],
        )
        .text(
            content="Stroke and glow",
            font="Roboto",
            size=28,
            color="#FFD166",
            position=(36, 140),
            effects=[Stroke(width=2, color="#7C3AED"), Glow(color="#FFD166", radius=5)],
        )
        .text(
            content="SPACED",
            font="Roboto",
            size=28,
            color="#9AE6B4",
            position=(36, 185),
            letter_spacing=10,
        )
        .text(
            content="badge",
            font="Roboto",
            size=20,
            color="#FFFFFF",
            position=(380, 200),
            align="center",
            effects=[Background(color="#7C3AED", padding=8, border_radius=6)],
        )
    )


def build_rich_text_canvas() -> Canvas:
    return (
        Canvas(480, 270)
        .background(color="#1A1033")
        .text(
            content=[
                TextPart(text="Rich ", color="#FFFFFF", size=30),
                TextPart(text="parts ", color="#F472B6", size=40, bold=True),
                TextPart(text="mixed", color="#60A5FA", size=24, italic=True),
            ],
            font="Roboto",
            position=(36, 50),
        )
        .text(
            content="GRADIENT FILL",
            font="Roboto",
            size=38,
            bold=True,
            position=(36, 120),
            fill=LinearGradient(angle=0, stops=[("#F59E0B", 0.0), ("#EF4444", 1.0)]),
        )
        .text(
            content="rotated",
            font="Roboto",
            size=24,
            color="#FFFFFF",
            position=(370, 190),
            align="center",
            rotation=-20,
            effects=[Background(color="#0EA5E9", padding=8, border_radius=6)],
        )
    )


def build_group_layout_canvas() -> Canvas:
    return (
        Canvas(480, 270)
        .background(color="#0B1320")
        .group(
            children=[
                {
                    "type": "text",
                    "content": "AUTO LAYOUT",
                    "font": "Roboto",
                    "size": 30,
                    "bold": True,
                    "color": "#FFFFFF",
                },
                {
                    "type": "text",
                    "content": "children stack without coordinates",
                    "font": "Roboto",
                    "size": 16,
                    "color": "#94A3B8",
                },
                {
                    "type": "shape",
                    "shape": "pill",
                    "width": 140,
                    "height": 32,
                    "color": "#22C55E",
                },
            ],
            direction="column",
            gap=14,
            padding=20,
            position=("50%", "50%"),
            align="center",
            item_align="center",
        )
    )


def build_image_and_blend_canvas() -> Canvas:
    return (
        Canvas(480, 270)
        .background(color="#404040")
        .image(path=SAMPLE_IMAGE, position=(0, 0), width=480, blend_mode="multiply", opacity=0.9)
        .svg(path=SAMPLE_SVG, position=(360, 30), width=80)
        .shape(shape="rectangle", position=(30, 190), width=180, height=50, color="#F59E0B")
        .text(content="over the blend", font="Roboto", size=20, color="#000000", position=(45, 203))
    )


class TestSvgVisualSnapshots:
    """Side-by-side snapshots: PIL render (top) vs rasterized SVG export (bottom)"""

    def setup_method(self):
        require_cairosvg()

    def test_snapshot_svg_vector_shapes(self):
        """Gradients, every shape primitive, effects, and outline as native SVG"""
        canvas = build_vector_shapes_canvas()
        strip = comparison_strip(render_reference(canvas), rasterize_svg(canvas))
        assert strip == external_file("snapshots/export_svg_vector_shapes.png")

    def test_snapshot_svg_text_styles(self):
        """Wrapping, shadow, stroke+glow, letter spacing, and badge backgrounds"""
        canvas = build_text_styles_canvas()
        strip = comparison_strip(render_reference(canvas), rasterize_svg(canvas))
        assert strip == external_file("snapshots/export_svg_text_styles.png")

    def test_snapshot_svg_rich_text(self):
        """Rich parts, gradient glyph fill, and rotated badge text"""
        canvas = build_rich_text_canvas()
        strip = comparison_strip(render_reference(canvas), rasterize_svg(canvas))
        assert strip == external_file("snapshots/export_svg_rich_text.png")

    def test_snapshot_svg_group_layout(self):
        """Auto-layout group children exported natively at their positions"""
        canvas = build_group_layout_canvas()
        strip = comparison_strip(render_reference(canvas), rasterize_svg(canvas))
        assert strip == external_file("snapshots/export_svg_group_layout.png")

    def test_snapshot_svg_image_and_blend(self):
        """Blend-mode flattening, SVG overlay embedding, and native layers above"""
        canvas = build_image_and_blend_canvas()
        strip = comparison_strip(render_reference(canvas), rasterize_svg(canvas))
        assert strip == external_file("snapshots/export_svg_image_and_blend.png")


@pytest.mark.skipif(SOFFICE is None, reason="LibreOffice is required to rasterize PPTX")
class TestPptxVisualSnapshots:
    """Side-by-side snapshots: PIL render (top) vs LibreOffice-rendered PPTX (bottom)"""

    def test_snapshot_pptx_vector_shapes(self):
        """Gradients, autoshapes, and outline as a PowerPoint slide"""
        expected = Path("tests/snapshots/export_pptx_vector_shapes.png")
        if not expected.exists():
            pytest.skip(f"Missing PPTX snapshot baseline: {expected}")
        canvas = build_vector_shapes_canvas()
        strip = comparison_strip(render_reference(canvas), rasterize_pptx(canvas))
        assert strip == external_file("snapshots/export_pptx_vector_shapes.png")

    def test_snapshot_pptx_text_styles(self):
        """Editable text boxes with wrapping, effects, and badge backgrounds"""
        expected = Path("tests/snapshots/export_pptx_text_styles.png")
        if not expected.exists():
            pytest.skip(f"Missing PPTX snapshot baseline: {expected}")
        canvas = build_text_styles_canvas()
        strip = comparison_strip(render_reference(canvas), rasterize_pptx(canvas))
        assert strip == external_file("snapshots/export_pptx_text_styles.png")
