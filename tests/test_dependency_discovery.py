"""Contracts shared by dependency validation and manifest discovery."""

import json

import pytest
from quickthumb import Canvas, Deck, PluginRegistry
from quickthumb.errors import MissingAssetError


@pytest.mark.parametrize("kind", ["canvas", "deck"])
@pytest.mark.parametrize(
    ("layer", "suffix", "nested"),
    [
        ({"type": "background", "image": "missing"}, "/image", False),
        ({"type": "image", "path": "missing"}, "/path", True),
        ({"type": "svg", "path": "missing"}, "/path", True),
        (
            {"type": "video", "source": "missing", "position": [0, 0], "width": 4, "height": 4},
            "/source",
            False,
        ),
        (
            {"type": "text", "content": "fill", "fill": {"type": "image", "path": "missing"}},
            "/fill/path",
            True,
        ),
        (
            {
                "type": "text",
                "content": [{"text": "fill", "fill": {"type": "image", "path": "missing"}}],
            },
            "/content/0/fill/path",
            True,
        ),
        (
            {
                "type": "plugin",
                "renderer": "input",
                "version": "1",
                "params": {},
                "width": 4,
                "height": 4,
                "assets": {"a/~b": "missing"},
            },
            "/assets/a~1~0b",
            True,
        ),
    ],
)
def test_missing_declared_files_share_validation_and_prefetch_paths(
    tmp_path, monkeypatch, kind, layer, suffix, nested
):
    registry = PluginRegistry()
    registry.register("input", "1", raster=lambda *_: pytest.fail("must fail before rendering"))
    monkeypatch.chdir(tmp_path)
    layer = {**layer, "id": "input"}
    layers = [{"type": "group", "children": [layer]}] if nested else [layer]
    canvas = Canvas.from_json(
        json.dumps({"kind": "canvas", "width": 4, "height": 4, "layers": layers}),
        registry=registry,
    )
    document = canvas if kind == "canvas" else Deck(slides=[Canvas(4, 4), canvas])
    expected = ("/slides/1" if kind == "deck" else "") + "/layers/0"
    expected += ("/children/0" if nested else "") + suffix

    [reported] = document.validate().errors
    with pytest.raises(MissingAssetError) as caught:
        document.prefetch_assets()

    [raised] = caught.value.details
    assert reported.path == raised.path == expected
    assert reported.layer_id == raised.layer_id == "input"
    assert reported.code == raised.code == "asset_missing"


def test_undeclared_strings_and_system_font_names_are_not_file_dependencies():
    source = "https://example.invalid/not-an-input.png"
    registry = PluginRegistry()
    registry.register("params", "1", raster=lambda *_: pytest.fail("prefetch must not render"))
    canvas = (
        Canvas(4, 4, registry=registry)
        .text(source, font="Definitely Not A Local File")
        .plugin("params", version="1", params={"path": source}, width=4, height=4)
        .custom(lambda *_: pytest.fail("prefetch must not render"), kwargs={"path": source})
    )

    assert canvas.prefetch_assets().asset_manifest == []
    assert Deck(slides=[canvas]).prefetch_assets().asset_manifest == []
