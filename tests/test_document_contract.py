"""Black-box specifications for the shared document contract."""

import json
from pathlib import Path

from PIL import Image
from quickthumb import (
    CanonicalFrame,
    Canvas,
    Deck,
    DeckInspection,
    DiagnosticReport,
    ExportResult,
    FrameSequence,
    ResolvedDocument,
    ValidationReport,
)


def test_canvas_and_deck_expose_the_same_document_methods():
    """Given either document kind, the stable document methods are available."""
    # Given: a canvas and a deck containing that canvas
    canvas = Canvas(32, 24).background(color="#FFFFFF")
    deck = Deck(slides=[canvas])

    # When: the public method set is inspected
    method_names = ("validate", "inspect", "diagnose", "resolve_assets", "sample", "export")

    # Then: both document types expose the same contract entry points
    assert all(callable(getattr(canvas, name)) for name in method_names)
    assert all(callable(getattr(deck, name)) for name in method_names)


def test_diagnose_keeps_list_behavior_with_a_shared_json_envelope():
    """Given a clean document, diagnose remains iterable and gains stable serialization."""
    # Given: a clean canvas and deck
    canvas = Canvas(32, 24).background(color="#FFFFFF")
    deck = Deck(slides=[canvas])

    # When: diagnostics are requested from both document kinds
    canvas_report = canvas.diagnose()
    deck_report = deck.diagnose()

    # Then: legacy list consumers and JSON consumers see the same findings
    assert isinstance(canvas_report, DiagnosticReport)
    assert isinstance(deck_report, DiagnosticReport)
    assert canvas_report == [] and deck_report == []
    assert json.loads(canvas_report.model_dump_json())["findings"] == []


def test_export_result_is_json_serializable_for_canvas_and_deck(tmp_path: Path):
    """Given static documents, export returns one stable result envelope."""
    # Given: one canvas and a two-slide deck
    canvas = Canvas(32, 24).background(color="#FFFFFF")
    deck = Deck(slides=[canvas, Canvas(32, 24).background(color="#000000")])

    # When: both documents use the canonical export entry point
    canvas_result = canvas.export(tmp_path / "canvas.png")
    deck_result = deck.export(str(tmp_path / "slides.png"))

    # Then: both results expose the same JSON-safe fields and written paths
    assert isinstance(canvas_result, ExportResult)
    assert isinstance(deck_result, ExportResult)
    for result in (canvas_result, deck_result):
        payload = json.loads(result.model_dump_json())
        assert {
            "written_paths",
            "capability_report",
            "fallback_diagnostics",
            "pixel_metrics",
            "timing_metrics",
            "asset_manifest",
        } <= payload.keys()
        assert result.written_paths
        assert all(Path(path).exists() for path in result.written_paths)

    assert canvas_result.kind == "canvas"
    assert deck_result.kind == "deck"
    assert len(deck_result.written_paths) == 2


def test_animated_export_uses_the_existing_renderer_and_shared_result(tmp_path: Path):
    """Given a canvas with a GIF target, export preserves the animated path."""
    # Given: a valid canvas with no special exporter configuration
    canvas = Canvas(16, 16).background(color="#FF0000")
    output = tmp_path / "canvas.gif"

    # When: the GIF is exported through the shared contract
    result = canvas.export(str(output))

    # Then: the existing animated exporter writes the requested file
    assert result.written_paths == [str(output)]
    assert output.exists()
    assert result.target == "video"


def test_validation_inspection_and_asset_resolution_are_document_level_results(tmp_path: Path):
    """Given a valid image asset, the shared pre-export methods return stable models."""
    # Given: a canvas referencing a local image and a deck containing it
    asset = tmp_path / "asset.png"
    Image.new("RGBA", (3, 2), (1, 2, 3, 255)).save(asset)
    canvas = Canvas(20, 20).image(str(asset), position=(0, 0), width=3, height=2)
    deck = Deck(slides=[canvas])

    # When: validation, inspection, and resolution are requested
    canvas_validation = canvas.validate()
    deck_validation = deck.validate()
    canvas_resolution = canvas.resolve_assets()
    deck_resolution = deck.resolve_assets()

    # Then: both documents report valid state and serializable asset metadata
    assert isinstance(canvas_validation, ValidationReport)
    assert isinstance(deck_validation, ValidationReport)
    assert canvas_validation.valid and deck_validation.valid
    assert isinstance(deck.inspect(), DeckInspection)
    assert isinstance(canvas_resolution, ResolvedDocument)
    assert canvas_resolution.asset_manifest[0].content_hash
    assert deck_resolution.asset_manifest == canvas_resolution.asset_manifest
    json.dumps(deck_resolution.model_dump(mode="json"))


def test_sample_returns_canonical_rgba_payloads_without_timeline_objects():
    """Given static documents, sample exposes pixels through the canonical frame models."""
    # Given: a canvas and a one-slide deck with a known color
    canvas = Canvas(4, 3).background(color="#112233")
    deck = Deck(slides=[canvas])

    # When: canonical samples are requested
    canvas_sample = canvas.sample()
    deck_sample = deck.sample()

    # Then: samples contain deterministic RGBA bytes and no compiler state
    assert isinstance(canvas_sample, CanonicalFrame)
    assert isinstance(deck_sample, FrameSequence)
    assert canvas_sample.mode == "RGBA"
    assert len(canvas_sample.to_bytes()) == 4 * 3 * 4
    assert deck_sample.frames[0].to_bytes() == canvas_sample.to_bytes()
    assert "events" not in canvas_sample.model_dump(mode="json")
