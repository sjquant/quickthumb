"""SVG plugin admission observes local pixels; executed routes remain truthful."""

import hashlib
import xml.etree.ElementTree as ET

import pytest
from quickthumb import Canvas, ExportPolicy, PluginLayer, PluginRegistry, RenderingError

from tests._optional import require_cairosvg

LIMITS = {"pixel_tolerance": 0, "max_different_pixel_ratio": 0.01, "min_hash_similarity": 0}


def svg(color):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="6" height="4">'
        '<defs><linearGradient id="paint"><stop stop-color="' + color + '"/>'
        '<stop offset="1" stop-color="' + color + '"/></linearGradient></defs>'
        '<rect width="6" height="4" fill="url(#paint)"/></svg>'
    )


@pytest.mark.parametrize(
    "color,accepted,tolerance,verdict",
    [
        ("#FF0000", True, 0, "exact"),
        ("#FE0000", True, 1, "tolerated"),
        ("#0000FF", False, 0, "exact"),
    ],
)
def test_native_plugin_gate_uses_local_assets_pixels_and_executed_source_ids(
    tmp_path, color, accepted, tolerance, verdict
):
    require_cairosvg()
    raw = bytes([255, 0, 0, 255]) * 24
    asset = tmp_path / "pixels.rgba"
    asset.write_bytes(raw)
    registry, calls = PluginRegistry(), []

    def raster(params, context):
        return context.read_asset("pixels")

    def native(params, context):
        calls.append(context.read_asset("pixels"))
        return svg(color)

    registry.register("badge", "1", raster=raster, svg=native)
    layer = PluginLayer(
        type="plugin",
        renderer="badge",
        version="1",
        params={},
        width=6,
        height=4,
        position=(20, 30),
        assets={"pixels": str(asset)},
    )
    scene = Canvas(96, 96, layers=[layer, layer], registry=registry)
    policy = ExportPolicy(fidelity={"svg": {**LIMITS, "pixel_tolerance": tolerance}})
    source_ids = [item.id for item in scene.inspect().layers]
    assert registry.capabilities("badge", "1") == ("raster", "svg")
    assert all(row.support == "partial" for row in scene.validate_export("svg", policy))
    assert calls == []  # Discovery and validation never certify or execute native pixels.
    path = tmp_path / "badge.svg"
    result = scene.export(path, policy=policy)
    rows = [row for row in result.capability_report if row.feature == "plugin"]
    assert [row.layer_id for row in rows] == source_ids
    assert all(row.support == ("native" if accepted else "fallback") for row in rows)
    assert all(
        row.native_attempt is True and "Local plugin RGBA comparison" in row.message for row in rows
    )
    # A wrong 6x4 plugin occupies <1% of this canvas, but must fail the local 1% gate.
    assert all(
        ("pixel_diff_ratio=0.0" if accepted else "pixel_diff_ratio=1.0") in row.message
        for row in rows
    )
    images = ET.parse(path).getroot().findall(".//{http://www.w3.org/2000/svg}image")
    assert len(images) == 2
    prefix = "data:image/svg+xml;base64," if accepted else "data:image/png;base64,"
    assert all(
        item.attrib["{http://www.w3.org/1999/xlink}href"].startswith(prefix) for item in images
    )
    assert calls == [raw, raw]
    assert scene.layers[0] is scene.layers[1] is layer
    assert any(
        item.content_hash == hashlib.sha256(raw).hexdigest() for item in result.asset_manifest
    )
    # The separate document-wide observer measures the final emitted representation.
    assert result.pixel_metrics.fidelity.verdict == verdict
    path.write_bytes(b"existing")
    strict = ExportPolicy(unsupported_motion="error", fidelity=policy.fidelity)
    if accepted:
        assert scene.export(path, policy=strict).fallback_diagnostics == []
    else:
        with pytest.raises(RenderingError, match="raster fallback"):
            scene.export(path, policy=strict)
        assert path.read_bytes() == b"existing"


def test_native_callback_requires_criteria_and_replacement_removes_stale_code(tmp_path):
    require_cairosvg()
    registry, calls = PluginRegistry(), []

    def raster(params, context):
        return bytes([255, 0, 0, 255]) * 24

    def native(params, context):
        calls.append("old")
        return svg("red")

    registry.register("badge", "1", raster=raster, svg=native)
    scene = Canvas(12, 8, registry=registry).plugin(
        "badge", version="1", params={}, width=6, height=4
    )
    path = tmp_path / "badge.svg"
    first = scene.export(path)
    assert calls == []
    assert any("explicit fidelity limits" in row.message for row in first.capability_report)
    registry.register("badge", "1", replace=True, raster=raster)
    second = scene.export(path, policy=ExportPolicy(fidelity={"svg": LIMITS}))
    assert calls == [] and registry.capabilities("badge", "1") == ("raster",)
    assert any("no SVG callback" in row.message for row in second.capability_report)
    registry.register("badge", "1", replace=True, raster=raster, svg=lambda p, c: svg("blue"))
    third = scene.export(path, policy=ExportPolicy(fidelity={"svg": LIMITS}))
    assert any(
        row.native_attempt and row.fallback == "rasterize" for row in third.capability_report
    )


@pytest.mark.parametrize(
    "content",
    [
        '<image href="http://127.0.0.1:9/image"/>',
        '<rect style="fill: u\\72l(http://127.0.0.1:9/image)"/>',
        '<style>@import "http://127.0.0.1:9/style";</style>',
        "<script>alert(1)</script>",
        "<style>@keyframes change { to { fill: blue } }</style>",
    ],
)
def test_non_self_contained_plugin_svg_falls_back_before_publication(tmp_path, content):
    require_cairosvg()
    registry = PluginRegistry()
    registry.register(
        "badge",
        "1",
        raster=lambda p, c: bytes([255, 0, 0, 255]) * 24,
        svg=lambda p, c: '<svg xmlns="http://www.w3.org/2000/svg">' + content + "</svg>",
    )
    scene = Canvas(12, 8, registry=registry).plugin(
        "badge", version="1", params={}, width=6, height=4
    )
    path = tmp_path / "unsafe.svg"
    result = scene.export(path, policy=ExportPolicy(fidelity={"svg": LIMITS}))
    assert "data:image/png;base64," in path.read_text()
    assert any(row.native_attempt and "invalid" in row.message for row in result.capability_report)
    path.write_bytes(b"existing")
    with pytest.raises(RenderingError, match="raster fallback"):
        scene.export(
            path, policy=ExportPolicy(unsupported_motion="error", fidelity={"svg": LIMITS})
        )
    assert path.read_bytes() == b"existing"


def test_clipped_plugin_keeps_atomic_png_and_strict_preserves_destination(tmp_path):
    require_cairosvg()
    registry, calls = PluginRegistry(), []

    def native(params, context):
        calls.append("svg")
        return svg("red")

    registry.register("badge", "1", raster=lambda p, c: bytes([255, 0, 0, 255]) * 24, svg=native)
    scene = Canvas(12, 8, registry=registry).plugin(
        "badge",
        version="1",
        params={},
        width=6,
        height=4,
        clip={"shape": "rectangle", "position": (0, 0), "width": 3, "height": 4},
    )
    path = tmp_path / "clip.svg"
    result = scene.export(path, policy=ExportPolicy(fidelity={"svg": LIMITS}))
    assert calls == []
    assert any(
        row.feature == "plugin" and row.fallback == "rasterize" and row.native_attempt is False
        for row in result.capability_report
    )
    path.write_bytes(b"existing")
    with pytest.raises(RenderingError, match="raster fallback"):
        scene.export(
            path, policy=ExportPolicy(unsupported_motion="error", fidelity={"svg": LIMITS})
        )
    assert calls == [] and path.read_bytes() == b"existing"
