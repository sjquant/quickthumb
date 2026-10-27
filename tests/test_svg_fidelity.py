"""Explicit SVG checks report actual Cairo output without changing representation."""

import builtins
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from quickthumb import Canvas, ExportPolicy
from quickthumb.errors import RenderingError

from tests._optional import require_cairosvg


def policy(*, pixel_tolerance: int = 0, ratio: float = 0, similarity: float = 1) -> ExportPolicy:
    return ExportPolicy(
        fidelity={
            "svg": {
                "pixel_tolerance": pixel_tolerance,
                "max_different_pixel_ratio": ratio,
                "min_hash_similarity": similarity,
            }
        }
    )


def test_svg_fidelity_is_optional_and_format_scoped(tmp_path, monkeypatch):
    """Default exports need no Cairo; requesting an unavailable SVG check fails before writing."""
    # Given: a caller without the optional reference renderer
    original_import = builtins.__import__

    def without_cairo(name, *args, **kwargs):
        if name in {"cairosvg", "cairocffi"}:
            raise ImportError("reference renderer is unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_cairo)
    scene = Canvas(12, 8).background(color="#123456")

    # When: the renderer is not requested for the selected format
    ordinary = scene.export(tmp_path / "ordinary.svg")
    raster = scene.export(tmp_path / "ordinary.png", policy=policy())
    assert ordinary.pixel_metrics.fidelity is None
    assert raster.pixel_metrics.fidelity is None
    assert "fidelity" not in ordinary.pixel_metrics.model_dump()

    # Then: requesting it preserves an existing destination and gives an actionable error
    destination = tmp_path / "checked.svg"
    destination.write_text("keep", encoding="utf-8")
    with pytest.raises(RenderingError) as error:
        scene.export(destination, policy=policy())
    assert error.value.code == "fidelity_unavailable"
    assert destination.read_text() == "keep"


def test_svg_fidelity_ignores_only_fully_hidden_rgb(tmp_path):
    """Hidden RGB can differ from Cairo's transparent black while visible RGBA remains exact."""
    require_cairosvg()

    # Given: canonical pixels whose hidden RGB is retained by a custom drawing callback
    def hidden_rgb(image):
        image.paste((240, 10, 20, 0), (0, 0, *image.size))

    scene = Canvas(4, 4).custom(hidden_rgb)
    assert scene.sample().frames[0].to_bytes()[:4] == bytes((240, 10, 20, 0))

    # When: Cairo renders the invisible content as transparent black
    result = scene.export(tmp_path / "hidden.svg", policy=policy())

    # Then: exact refers to visible RGBA, rather than the canonical raw-pixel SHA
    comparison = result.pixel_metrics.fidelity
    assert comparison is not None
    assert comparison.verdict == "exact"
    assert comparison.pixel_diff_ratio == comparison.mean_absolute_error == 0
    assert comparison.hash_similarity == 1


def test_svg_fidelity_applies_caller_limits_without_rasterizing(tmp_path):
    """A native ellipse fails strict limits or satisfies a caller-selected edge budget."""
    require_cairosvg()
    # Given: an antialiased ellipse whose Cairo and Pillow edge coverage differs
    scene = Canvas(64, 48).shape("ellipse", (6, 5), 36, 25, "#42CEB7")
    native = scene.to_svg()

    # When: checking exact pixels and a fixture-specific budget for edge differences
    strict = scene.export(tmp_path / "strict.svg", policy=policy())
    edge_policy = policy(ratio=0.15, similarity=0.95)
    tolerant = scene.export(tmp_path / "tolerant.svg", policy=edge_policy)
    edge_policy.fidelity["svg"]["max_different_pixel_ratio"] = 0.5

    # Then: verdicts explain the chosen budget while both outputs retain their native elements
    first, second = strict.pixel_metrics.fidelity, tolerant.pixel_metrics.fidelity
    assert first is not None and second is not None
    assert first.verdict == "out_of_policy"
    assert second.verdict == "tolerated"
    assert second.pixel_diff_ratio is not None and 0 < second.pixel_diff_ratio <= 0.15
    assert second.max_channel_delta is not None and second.max_channel_delta > 0
    assert second.limits["max_different_pixel_ratio"] == 0.15
    assert (tmp_path / "strict.svg").read_text() == native
    assert (tmp_path / "tolerant.svg").read_text() == native
    assert "<ellipse" in native
    assert strict.fallback_diagnostics == tolerant.fallback_diagnostics == []
    diagnostic = next(item for item in strict.capability_report if item.feature == "fidelity")
    assert diagnostic.support == "partial" and diagnostic.fallback is None
    assert "out_of_policy" in diagnostic.message


@pytest.mark.parametrize(
    ("mutate", "size", "ratio"),
    [
        (lambda svg: svg.replace('width="4"', 'width="8"', 1), (8, 4), None),
        (lambda svg: svg.replace(' fill-opacity="0"', ""), (4, 4), 1.0),
    ],
    ids=["wrong-dimensions", "lost-alpha"],
)
def test_svg_fidelity_detects_size_or_alpha_loss(tmp_path, monkeypatch, mutate, size, ratio):
    """Incorrect dimensions and opacity cannot pass a perfect white-composited hash."""
    require_cairosvg()
    # Given: an exporter regression changes the generated dimensions or transparent fill
    scene = Canvas(4, 4).background(color="#FFFFFF00")
    produced = mutate(scene.to_svg())
    monkeypatch.setattr(scene, "to_svg", lambda: produced)

    # When: the real Cairo renderer rasterizes those SVG bytes
    result = scene.export(tmp_path / "changed.svg", policy=policy())

    # Then: the report preserves dimensions and alpha evidence without resizing or false fallback
    comparison = result.pixel_metrics.fidelity
    assert comparison is not None
    assert comparison.verdict == "out_of_policy"
    assert comparison.hash_similarity == 1
    assert (comparison.actual_width, comparison.actual_height) == size
    assert comparison.pixel_diff_ratio == ratio
    assert (result.pixel_metrics.width, result.pixel_metrics.height) == (4, 4)
    assert result.fallback_diagnostics == []
    assert (tmp_path / "changed.svg").read_text() == produced


def test_svg_fidelity_reports_font_image_and_environment(tmp_path):
    """Text and images retain their SVG representation with measured static renderer context."""
    require_cairosvg()
    # Given: fonts pinned by the test fontconfig and an embedded raster image
    scene = (
        Canvas(96, 64)
        .background(color="#FFFFFF")
        .text("Hi", position=(6, 6), size=16, font="assets/fonts/Roboto-Regular.ttf")
        .image(
            str(Path(__file__).parent / "fixtures/sample_image.jpg"), (40, 5), width=32, height=24
        )
    )
    native = scene.to_svg()

    # When: the caller requests observations under an exact policy
    result = scene.export(tmp_path / "content.svg", policy=policy())

    # Then: measured context makes this a Cairo/static observation, not a browser guarantee
    comparison = result.pixel_metrics.fidelity
    assert comparison is not None
    assert comparison.renderer == "cairosvg" and comparison.renderer_version
    assert comparison.cairo_version
    assert comparison.scope == "authored_static"
    assert comparison.canonical_environment == scene.sample().environment
    assert (comparison.actual_width, comparison.actual_height) == (96, 64)
    assert comparison.mean_absolute_error is not None
    assert "<text" in native and "data:image/png;base64," in native
    assert (tmp_path / "content.svg").read_text() == native


def test_svg_fidelity_hash_limit_rejects_within_pixel_budget(tmp_path, monkeypatch):
    """A hash mismatch is rejected even when the caller permits every pixel to differ."""
    require_cairosvg()
    # Given: generated SVG unexpectedly paints half of a white scene black
    scene = Canvas(16, 16).background(color="#FFFFFF")
    root = ET.fromstring(scene.to_svg())
    ET.SubElement(
        root,
        "{http://www.w3.org/2000/svg}rect",
        {
            "width": "8",
            "height": "16",
            "fill": "#000000",
        },
    )
    produced = ET.tostring(root, encoding="unicode")
    monkeypatch.setattr(scene, "to_svg", lambda: produced)

    # When: the pixel budget accepts the change but hash similarity must be perfect
    result = scene.export(tmp_path / "hash.svg", policy=policy(ratio=1, similarity=1))

    # Then: the independent hash criterion makes the observation out of policy
    comparison = result.pixel_metrics.fidelity
    assert comparison is not None
    assert comparison.pixel_diff_ratio == 0.5
    assert comparison.hash_similarity < 1
    assert comparison.verdict == "out_of_policy"


def test_svg_fidelity_renderer_failure_preserves_output(tmp_path, monkeypatch):
    """A reference-renderer failure leaves the caller's existing SVG untouched."""
    renderer = require_cairosvg()

    # Given: the reference renderer fails independently of native SVG generation
    def fail_reference(**kwargs):
        raise RuntimeError("reference failed")

    monkeypatch.setattr(renderer, "svg2png", fail_reference)
    destination = tmp_path / "existing.svg"
    destination.write_text("keep", encoding="utf-8")

    # When/Then: the export reports an operational failure before opening the destination
    with pytest.raises(RenderingError) as error:
        Canvas(4, 4).background(color="#FFFFFF").export(destination, policy=policy())
    assert error.value.code == "fidelity_comparison_failed"
    assert destination.read_text() == "keep"
