"""Public pixels and failures of trusted synchronous RGBA plugins."""

import hashlib
import json

import pytest
from jsonschema import validate
from PIL import Image
from PIL.GifImagePlugin import GifImageFile
from quickthumb import (
    AnimatedTextValue,
    BackdropBlur,
    Canvas,
    Deck,
    ExportPolicy,
    Fade,
    GifOptions,
    LayerClip,
    LayerMask,
    PluginLayer,
    PluginRegistry,
    TextLayer,
    canvas_json_schema,
    inspect_document,
    plugin_layer_json_schema,
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


@pytest.mark.parametrize("target", ["svg", "html", "pdf", "pptx"])
def test_plugin_document_fallback_reports_and_preserves_output(tmp_path, target):
    """Native documents embed plugin RGBA pixels; strict policy rejects before replacement."""
    from tests.test_parent_documents import embedded_png

    # Given: only an explicit registry knows this callback
    registry = PluginRegistry()
    calls = []

    def badge(params, context):
        calls.append(context.size)
        return bytes([12, 34, 56, 255]) * (context.size[0] * context.size[1])

    registry.register("badge", "1", raster=badge)
    canvas = Canvas(96, 96, registry=registry).plugin(
        "badge", version="1", params={}, width=8, height=6, position=(20, 30), id="badge"
    )
    destination = tmp_path / f"badge.{target}"

    # When: a capability query needs no executable callback or rendered pixels
    [diagnostic] = canvas.validate_export(target)
    assert calls == []
    assert diagnostic.feature == "plugin" and diagnostic.support == "fallback"
    assert diagnostic.fallback == "rasterize" and diagnostic.layer_id == "badge"
    assert "badge" in diagnostic.message and "1" in diagnostic.message
    result = canvas.export(destination)

    # Then: every document contains the actual callback pixels with a reported fallback
    assert result.fallback_diagnostics[0].layer_id == "badge"
    if target == "pdf":
        import pypdfium2

        with pypdfium2.PdfDocument(destination) as document:
            page = document[0]
            bitmap = page.render(scale=1)
            assert bitmap.to_pil().getpixel((22, 32))[:3] == (12, 34, 56)
            bitmap.close()
            page.close()
    else:
        output = destination.read_bytes() if target == "pptx" else destination.read_text()
        with embedded_png(output, target) as patch:
            assert patch.size == (8, 6)
            assert patch.tobytes() == bytes([12, 34, 56, 255]) * 48
    destination.write_bytes(b"existing")
    calls.clear()
    with pytest.raises(RenderingError, match="raster fallback"):
        canvas.export(destination, policy=ExportPolicy(unsupported_motion="error"))
    assert calls == []
    assert destination.read_bytes() == b"existing"
    if target in {"html", "pptx"}:
        for document in (canvas, Deck(slides=[canvas])):
            with pytest.raises(RenderingError, match="raster fallback"):
                getattr(document, "to_" + target)(policy=ExportPolicy(unsupported_motion="error"))
    if target == "pptx":
        with pytest.raises(RenderingError, match="raster fallback"):
            canvas.export(destination, policy=ExportPolicy(pptx={"badge": "native"}))
    registry.register("badge", "1", replace=True)
    assert canvas.validate_export(target)[0].support == "fallback"
    with pytest.raises(RenderingError, match="no raster callback"):
        canvas.export(destination)
    assert destination.read_bytes() == b"existing"


def test_group_plugin_composition_timed_plan_and_inspection(tmp_path):
    """Group placement and clipping keep plugin pixels consistent through Deck timed output."""
    # Given: an explicitly registered patch inside a composed animated nested group
    registry = PluginRegistry()
    registry.register("badge", "1", raster=lambda params, context: bytes([240, 20, 10, 255]) * 24)
    child = PluginLayer(
        type="plugin",
        renderer="badge",
        version="1",
        params={},
        width=6,
        height=4,
        clip=LayerClip(position=(12, 9), width=3, height=4),
        mask=LayerMask(shape="rectangle", position=(12, 9), width=3, height=4, opacity=0.5),
        id="badge",
    )
    canvas = Canvas(96, 96, registry=registry).group(
        [child], position=(10, 7), padding=2, animation=Fade(duration=0.4), id="group"
    )
    validate(json.loads(canvas.to_json()), canvas_json_schema(registry=registry))
    validate(child.model_dump(mode="json"), plugin_layer_json_schema(registry=registry))
    deck = Deck.from_json(Deck(slides=[canvas]).to_json(), registry=registry)

    # When: the shared timed plan settles the animated group and inspection builds that plan
    frames = deck.sample(time=[0, 0.2, 0.4], hold=0).frames
    report = inspect_document(deck)
    destination = tmp_path / "badge.gif"
    deck.export(destination, animation=GifOptions(fps=10, hold=0))

    # Then: group placement and both composition boundaries apply before group animation
    settled = frames[-1].to_image()
    assert settled.getpixel((12, 9)) == (120, 10, 5, 255)
    still = canvas.sample().frames[0].to_image()
    assert still.getpixel((12, 9)) == (240, 20, 10, 128)
    assert settled.getpixel((15, 9)) == (0, 0, 0, 255)
    first = frames[0].to_image()
    assert first.getpixel((12, 9)) == (0, 0, 0, 255)
    assert report.kind == "deck"
    assert any(
        item.feature == "plugin" and item.support == "full"
        for item in deck.validate_export("video")
    )
    with Image.open(destination) as encoded:
        assert isinstance(encoded, GifImageFile)
        encoded.seek(encoded.n_frames - 1)
        assert encoded.convert("RGB").getpixel((12, 9)) == (120, 10, 5)
    destination.write_bytes(b"existing")
    with pytest.raises(ValidationError, match="workers=1"):
        deck.export(destination, animation=GifOptions(fps=10, hold=0, workers=2))
    assert destination.read_bytes() == b"existing"


@pytest.mark.parametrize("target", ["svg", "html", "pdf", "pptx"])
def test_plugin_group_backdrop_prefix_keeps_composition(tmp_path, target):
    """A clipped plugin group stays atomic when a document rasterizes a backdrop prefix."""
    from tests.test_parent_documents import embedded_png

    # Given: a clipped group underneath an effect that reads the existing backdrop
    registry = PluginRegistry()
    registry.register("badge", "1", raster=lambda params, context: bytes([240, 20, 10, 255]) * 48)
    child = PluginLayer(
        type="plugin",
        renderer="badge",
        version="1",
        params={},
        width=8,
        height=6,
        id="badge",
    )
    canvas = (
        Canvas(96, 96, registry=registry)
        .background(color="#123456")
        .group([child], position=(20, 30), clip=LayerClip(position=(20, 30), width=4, height=6))
        .shape("rectangle", (21, 31), 4, 4, "#FFFFFF", effects=[BackdropBlur(radius=2)])
    )
    expected = canvas.sample().frames[0].to_image()
    destination = tmp_path / f"composed.{target}"

    # When: a native document captures the ordered prefix through its normal raster fallback
    canvas.export(destination)

    # Then: clipping and backdrop sampling match the canonical settled composition
    if target == "pdf":
        import pypdfium2

        with pypdfium2.PdfDocument(destination) as document:
            page = document[0]
            bitmap = page.render(scale=1)
            assert bitmap.to_pil().convert("RGB").tobytes() == expected.convert("RGB").tobytes()
            bitmap.close()
            page.close()
    else:
        output = destination.read_bytes() if target == "pptx" else destination.read_text()
        with embedded_png(output, target) as image:
            assert image.size == expected.size and image.tobytes() == expected.tobytes()


def test_parent_counter_group_retains_explicit_plugin_registry():
    """A parent-linked counter group renders its static plugin using the supplied registry."""
    # Given: a dynamic counter forces a composed parent source to repaint its children
    registry = PluginRegistry()
    registry.register("badge", "1", raster=lambda params, context: bytes([240, 20, 10, 255]) * 24)
    canvas = (
        Canvas(96, 96, registry=registry)
        .null(id="root")
        .group(
            [
                PluginLayer(
                    type="plugin", renderer="badge", version="1", params={}, width=6, height=4
                ),
                TextLayer(
                    type="text",
                    content="",
                    size=12,
                    value=AnimatedTextValue.model_validate(
                        {"from": 0, "to": 10, "duration": 0.4, "style": "plain"}
                    ),
                ),
            ],
            parent="root",
            position=(10, 7),
            padding=2,
            clip=LayerClip(position=(10, 7), width=40, height=40),
        )
    )

    # When: the shared timed renderer repaints the counter and static sibling together
    frame = canvas.sample(time=0.2, hold=0).frames[0]

    # Then: no global registration is needed to preserve the plugin's placed pixels
    with frame.to_image() as image:
        assert image.getpixel((12, 9)) == (240, 20, 10, 255)


@pytest.mark.parametrize("target", ["svg", "pdf"])
def test_plugin_assets_registry_and_source_ids_survive_measured_document_export(tmp_path, target):
    """Private plugin pixels remain the reference for actual routes and prewrite comparison."""
    from tests._optional import require_cairosvg, require_pypdfium2

    if target == "svg":
        require_cairosvg()
    else:
        require_pypdfium2()
    # Given: two source occurrences use one private renderer and declared byte asset.
    raw = bytes([12, 34, 56, 255]) * 24
    asset = tmp_path / "pixels.rgba"
    asset.write_bytes(raw)
    registry = PluginRegistry()
    calls = []
    fail_reference = False

    def badge(params, context):
        calls.append(context.size)
        if fail_reference and len(calls) > 2:
            raise RuntimeError("reference callback failed after document rendering")
        return context.read_asset("pixels")

    registry.register("badge", "1", raster=badge)
    layer = PluginLayer(
        type="plugin",
        renderer="badge",
        version="1",
        params={},
        width=6,
        height=4,
        position=(4, 3),
        assets={"pixels": str(asset)},
    )
    scene = Canvas(24, 16, layers=[layer, layer], registry=registry)
    source_ids = [item.id for item in scene.inspect().layers]
    limits = ExportPolicy(
        fidelity={
            target: {
                "pixel_tolerance": 0,
                "max_different_pixel_ratio": 0,
                "min_hash_similarity": 1,
            }
        }
    )
    path = tmp_path / f"observed.{target}"

    # When: the actual document and its canonical reference render through this registry.
    result = scene.export(path, policy=limits)

    # Then: both distinct occurrences are actual PNG routes, and measured pixels match.
    routes = [row for row in result.capability_report if row.feature == "layer_representation"]
    assert [row.layer_id for row in routes] == source_ids
    assert len(set(source_ids)) == 2
    assert all(row.fallback == "rasterize" and row.native_attempt is False for row in routes)
    comparison = result.pixel_metrics.fidelity
    assert comparison is not None and comparison.verdict == "exact"
    [resolved] = [item for item in result.asset_manifest if item.asset_type == "plugin"]
    assert resolved.content_hash == hashlib.sha256(raw).hexdigest()
    assert scene.layers[0] is scene.layers[1] is layer

    # A failure while capturing reference pixels occurs after document rendering, before writing.
    path.write_bytes(b"existing")
    calls.clear()
    fail_reference = True
    with pytest.raises(RenderingError, match="reference callback failed"):
        scene.export(path, policy=limits)
    assert len(calls) == 3
    assert path.read_bytes() == b"existing"
