"""Public pixels and failures of trusted synchronous RGBA plugins."""

import hashlib
import json

import pytest
from jsonschema import validate
from PIL import Image
from quickthumb import (
    Canvas,
    Deck,
    PluginLayer,
    PluginRegistry,
    canvas_json_schema,
    inspect_document,
)
from quickthumb.errors import RenderingError, ValidationError


def test_plugin_box_matches_png_sample_deck_and_json(tmp_path):
    """A plugin patch keeps its box, alpha and placement through public document outputs."""
    # Given: a callback that draws only its local box and consumes a private params copy
    registry = PluginRegistry()

    def badge(params, context):
        color = params.pop("color")
        with Image.new("RGBA", context.size, color) as image:
            return image.tobytes()

    registry.register("badge", "1", raster=badge)
    canvas = Canvas(8, 6, registry=registry).plugin(
        "badge",
        version="1",
        params={"color": "#FF000080"},
        width=4,
        height=2,
        position=("50%", "50%"),
        align="center",
        opacity=0.5,
        id="badge",
    )

    # When: the same scene crosses JSON and Canvas/Deck sample and export boundaries
    restored = Canvas.from_json(canvas.to_json(), registry=registry)
    validate(json.loads(canvas.to_json()), canvas_json_schema(registry=registry))
    sample = canvas.sample().frames[0].to_bytes()
    assert restored.sample().frames[0].to_bytes() == sample
    assert Deck(slides=[canvas]).sample().frames[0].to_bytes() == sample
    result = canvas.export(tmp_path / "badge.png")

    # Then: straight alpha is multiplied once and the original parameters are intact
    with Image.open(result.written_paths[0]) as image:
        assert image.tobytes() == sample
        assert image.getpixel((2, 2)) == (255, 0, 0, 64)
        assert image.getpixel((1, 2)) == (0, 0, 0, 0)
    layer = canvas.layers[0]
    assert isinstance(layer, PluginLayer)
    assert layer.params == {"color": "#FF000080"}
    bounds = canvas.inspect().layers[0].bbox
    assert bounds is not None
    assert (bounds.x, bounds.y, bounds.width, bounds.height) == (2, 2, 4, 2)
    definition = registry.lookup("badge", "1")
    assert definition is not None
    assert definition.model_dump() == {
        "renderer": "badge",
        "version": "1",
        "params_schema": None,
    }


def test_plugin_reads_only_declared_byte_assets(tmp_path):
    """A declared byte asset renders; an undeclared name produces a structured plugin error."""
    # Given: a raw RGBA asset referenced by its declared name
    asset = tmp_path / "pixels.rgba"
    asset.write_bytes(bytes([12, 34, 56, 78]) * 4)
    registry = PluginRegistry()
    registry.register(
        "asset", "1", raster=lambda params, context: context.read_asset(params["key"])
    )
    canvas = Canvas(2, 2, registry=registry).plugin(
        "asset",
        version="1",
        params={"key": "pixels"},
        width=2,
        height=2,
        assets={"pixels": str(asset)},
        id="asset",
    )

    # When: declared dependencies are prefetched before sampling and inspection
    [entry] = canvas.prefetch_assets().asset_manifest
    assert canvas.sample().frames[0].to_bytes() == asset.read_bytes()
    report = inspect_document(canvas)

    # Then: the same public metadata describes the local bytes used by the callback
    assert entry.asset_type == "plugin" and entry.status == "local"
    assert entry.source == str(asset)
    assert entry.content_hash == hashlib.sha256(asset.read_bytes()).hexdigest()
    assert report.asset_manifest == [entry]
    layer = canvas.layers[0]
    assert isinstance(layer, PluginLayer)
    layer.params["key"] = "undeclared"
    with pytest.raises(RenderingError, match="not declared") as caught:
        canvas.export(tmp_path / "missing.png")
    assert caught.value.code == "plugin_render_failed"
    assert caught.value.details[0].layer_id == "asset"
    assert not (tmp_path / "missing.png").exists()


@pytest.mark.parametrize("raw", [None, b"RGB"])
def test_invalid_plugin_pixels_preserve_destination(tmp_path, raw):
    """A callback returning a non-byte or wrong-sized result fails before replacing output."""
    # Given: a destination and callback violating the canonical RGBA byte contract
    destination = tmp_path / "invalid.png"
    destination.write_bytes(b"existing")
    registry = PluginRegistry()
    registry.register("invalid", "1", raster=lambda params, context: raw)
    canvas = Canvas(2, 2, registry=registry).plugin(
        "invalid",
        version="1",
        params={},
        width=2,
        height=2,
        id="invalid",
    )

    # When / Then: the structured error identifies the layer and retains the destination
    with pytest.raises(RenderingError) as caught:
        canvas.export(destination)
    assert caught.value.code == "plugin_invalid_rgba"
    assert caught.value.details[0].layer_id == "invalid"
    assert destination.read_bytes() == b"existing"


def test_replacing_registration_replaces_or_removes_its_callback():
    """Replacing metadata never leaves an old executable callback attached to that version."""
    # Given: an existing document using a versioned callback
    registry = PluginRegistry()
    registry.register("badge", "1", raster=lambda params, context: bytes([1, 2, 3, 255]))
    canvas = Canvas(1, 1, registry=registry).plugin(
        "badge", version="1", params={}, width=1, height=1
    )
    assert canvas.sample().frames[0].to_bytes() == bytes([1, 2, 3, 255])

    # When: the registration is replaced with a callback, then with metadata alone
    registry.register(
        "badge", "1", replace=True, raster=lambda params, context: bytes([4, 5, 6, 255])
    )
    assert canvas.sample().frames[0].to_bytes() == bytes([4, 5, 6, 255])
    registry.register("badge", "1", replace=True)

    # Then: stale executable code is unavailable and removing metadata is also observable
    with pytest.raises(RenderingError, match="no raster callback"):
        canvas.sample()
    registry.clear()
    with pytest.raises(ValidationError, match="not registered"):
        canvas.sample()


@pytest.mark.parametrize(
    ("target", "extension"),
    [("svg", "svg"), ("html", "html"), ("pdf", "pdf"), ("pptx", "pptx"), ("video", "gif")],
)
def test_plugin_document_targets_fail_explicitly(tmp_path, target, extension):
    """Capability queries report unsupported plugins; actual exports preserve existing output."""
    # Given: a valid raster plugin and a document-format destination
    registry = PluginRegistry()
    registry.register("badge", "1", raster=lambda params, context: bytes([1, 2, 3, 255]))
    canvas = Canvas(96, 96, registry=registry).plugin(
        "badge", version="1", params={}, width=1, height=1, id="badge"
    )
    destination = tmp_path / f"badge.{extension}"

    destination.write_bytes(b"existing")

    # When: a caller asks about support without rendering or writing a file
    [diagnostic] = canvas.validate_export(target)

    # Then: the query reports the limitation and actual export enforces it before writing
    assert diagnostic.feature == "plugin" and diagnostic.support == "unsupported"
    assert diagnostic.layer_id == "badge"
    with pytest.raises(RenderingError, match="settled raster output only"):
        canvas.export(destination)
    assert destination.read_bytes() == b"existing"
