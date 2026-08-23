"""Black-box specifications for the shared document contract."""

import json
from pathlib import Path

import pytest
from PIL import Image
from quickthumb import (
    AnimationSpec,
    BlurTrack,
    CanonicalFrame,
    Canvas,
    Deck,
    DeckInspection,
    DiagnosticReport,
    ExportPolicy,
    ExportResult,
    FrameSequence,
    GifOptions,
    ResolvedDocument,
    TextFillImage,
    TextPart,
    ValidationReport,
)
from quickthumb.errors import RenderingError


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


def test_stable_root_api_hides_timeline_compiler_internals():
    """Given the stable package root, timeline/compiler implementation symbols are absent."""
    # Given: the package root used by document authors
    import quickthumb

    # Then: low-level motion internals remain available only from their module
    assert not hasattr(quickthumb, "Timeline")
    assert not hasattr(quickthumb, "compile_timeline")
    assert not hasattr(quickthumb, "sample_frames")


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
    assert canvas_result.output_format == "png"
    assert deck_result.pixel_metrics.frame_count == 2


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
    assert result.output_format == "gif"
    assert result.pixel_metrics.frame_count == 1


def test_export_reports_effective_format_and_animation_timing(tmp_path: Path):
    """Given export options, the result describes the effective output format and timing."""
    # Given: a canvas and an explicit GIF sampling rate
    canvas = Canvas(16, 16).background(color="#FF0000")

    # When: the canvas is exported with a non-default frame rate
    result = canvas.export(tmp_path / "timed.gif", animation=GifOptions(fps=7))

    # Then: timing metadata follows the actual option and the encoded frames
    assert result.output_format == "gif"
    assert result.timing_metrics.fps == 7
    assert result.timing_metrics.frame_count == result.pixel_metrics.frame_count == 1


def test_export_uses_html_aliases_and_explicit_raster_format(tmp_path: Path):
    """Given supported aliases or an explicit format, target metadata remains normalized."""
    # Given: a canvas with two valid output configurations
    canvas = Canvas(16, 16).background(color="#FFFFFF")

    # When: both configurations are exported
    html_result = canvas.export(tmp_path / "canvas.htm")
    raster_result = canvas.export(tmp_path / "canvas.bin", format="PNG")

    # Then: the capability family and effective format are both unambiguous
    assert html_result.target == "html"
    assert html_result.output_format == "html"
    assert raster_result.target == "raster"
    assert raster_result.output_format == "png"


def test_policy_errors_fail_before_writing_output(tmp_path: Path):
    """Given an error export policy, unsupported motion fails before an output exists."""
    # Given: motion that PPTX cannot represent natively
    canvas = Canvas(100, 100).text(
        "Motion",
        position=(0, 0),
        animation=AnimationSpec.timeline(
            BlurTrack(keyframes=[{"time": 0, "value": 0}, {"time": 1, "value": 4}])
        ),
    )
    output = tmp_path / "motion.pptx"

    # When / Then: the shared export path honors the policy before rendering
    with pytest.raises(RenderingError):
        canvas.export(output, policy=ExportPolicy(unsupported_motion="error"))
    assert not output.exists()


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


def test_invalid_documents_and_audio_assets_are_reported_at_document_level(tmp_path: Path):
    """Given invalid documents, validation reports actionable paths without rendering."""
    # Given: an empty deck and a deck with a missing narration asset
    empty = Deck()
    narrated = (
        Deck().slide(Canvas(20, 20)).slide(Canvas(20, 20), audio=str(tmp_path / "missing.wav"))
    )

    # When: document validation runs
    empty_report = empty.validate()
    narrated_report = narrated.validate()

    # Then: both failures are represented in the stable report
    assert not empty_report.valid
    assert empty_report.errors[0].code == "invalid_document"
    assert not narrated_report.valid
    assert narrated_report.errors[0].code == "asset_missing"
    assert narrated_report.errors[0].path == "/slides/1/audio"


def test_text_part_assets_and_audio_are_included_in_manifests(tmp_path: Path):
    """Given rich text and narration assets, resolution returns every dependency."""
    # Given: one local text-fill image and one local audio path
    image_path = tmp_path / "fill.png"
    audio_path = tmp_path / "narration.wav"
    Image.new("RGBA", (3, 2), (1, 2, 3, 255)).save(image_path)
    audio_path.write_bytes(b"audio")
    canvas = Canvas(20, 20).text(
        [TextPart(text="filled", fill=TextFillImage(path=str(image_path)))],
        position=(0, 0),
    )
    deck = Deck().slide(canvas, audio=str(audio_path))

    # When: assets are resolved
    manifest = deck.resolve_assets().asset_manifest

    # Then: both rich text and narration dependencies are represented
    assert {(entry.asset_type, entry.source) for entry in manifest} == {
        ("text-fill", str(image_path)),
        ("audio", str(audio_path)),
    }
    assert all(entry.content_hash for entry in manifest)


def test_inspection_and_diagnostics_have_common_json_discriminators():
    """Given both document kinds, inspection and diagnostics serialize consistently."""
    # Given: a canvas finding and a deck-wide mixed-size finding
    canvas = Canvas(1280, 720).text("fine print", size=14, position=(10, 10))
    deck = Deck(slides=[Canvas(100, 100), Canvas(120, 100)])

    # When: public reports are serialized
    canvas_inspection = canvas.inspect().model_dump(mode="json")
    deck_inspection = deck.inspect().model_dump(mode="json")
    canvas_diagnostics = canvas.diagnose()
    deck_diagnostics = deck.diagnose()

    # Then: discriminators and non-empty finding fields survive the envelope
    assert canvas_inspection["kind"] == "canvas"
    assert deck_inspection["kind"] == "deck"
    assert canvas_diagnostics
    assert deck_diagnostics
    canvas_codes = {
        finding["code"] for finding in json.loads(canvas_diagnostics.model_dump_json())["findings"]
    }
    assert "tiny-text" in canvas_codes
    deck_payload = json.loads(deck_diagnostics.model_dump_json())
    assert deck_payload["findings"][0]["code"] == "mixed-slide-size"


def test_diagnostic_serialization_honors_exclude_none():
    """Given a diagnostic envelope, serialization options control optional fields."""
    # Given: a deck-level finding with optional fields omitted
    report = Deck(slides=[Canvas(100, 100), Canvas(120, 100)]).diagnose()

    # When: the report is dumped with and without optional values
    compact = report.model_dump(mode="json", exclude_none=True)
    expanded = report.model_dump(mode="json", exclude_none=False)

    # Then: the option is observable in the JSON-safe result
    assert "slide_index" not in compact["findings"][0]
    assert "slide_index" in expanded["findings"][0]


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
