"""Black-box checks for generic inspection and canonical sample consumers."""

import hashlib
import json
from pathlib import Path

import jsonschema
import pytest
from PIL import Image
from quickthumb import (
    AnimationSpec,
    BlurTrack,
    Canvas,
    CanvasInspection,
    Deck,
    DeckInspection,
    DocumentInspection,
    ExportPolicy,
    FrameSequence,
    KeyframeSpec,
    MissingAssetError,
    RenderingError,
    ValidationError,
    inspect_document,
)


def _canvas() -> Canvas:
    return Canvas(48, 32).shape(
        shape="rectangle", position=(4, 5), width=8, height=6, color="#FF0000"
    )


@pytest.mark.parametrize("kind", ["canvas", "deck"])
def test_common_report_matches_existing_public_contracts(kind: str):
    canvas = _canvas()
    source = canvas if kind == "canvas" else Deck(slides=[canvas])
    original = source.to_json()

    report = inspect_document(source, target="video", fps=4, max_samples=8)

    assert report.kind == kind
    assert (report.width, report.height) == (48, 32)
    assert report.pages == [canvas.inspect()]
    assert report.motion == source.inspect_motion(target="video", fps=4, max_samples=8)
    assert report.diagnostics == source.diagnose()
    assert report.asset_manifest == []
    assert source.to_json() == original
    # Existing consumers keep their discriminator and variant-specific fields.
    layout = source.inspect()
    if kind == "canvas":
        assert isinstance(layout, CanvasInspection)
        assert set(layout.model_dump()) == {"kind", "width", "height", "layers"}
    else:
        assert isinstance(layout, DeckInspection)
        assert set(layout.model_dump()) == {"kind", "width", "height", "slides"}


@pytest.mark.parametrize("kind", ["canvas", "deck"])
def test_json_round_trip_preserves_common_fields_and_variant_details(kind: str):
    first = _canvas()
    source = first if kind == "canvas" else Deck(slides=[first, Canvas(60, 40)])
    report = inspect_document(source, fps=2)
    payload = json.loads(report.model_dump_json())

    jsonschema.validate(payload, DocumentInspection.model_json_schema())
    restored = DocumentInspection.model_validate_json(json.dumps(payload))
    assert restored.model_dump(mode="json") == payload
    assert payload["version"] == "1"
    assert payload["pages"][0]["layers"][0]["bbox"] == {
        "x": 4,
        "y": 5,
        "width": 8,
        "height": 6,
    }
    assert payload["motion"]["slides"][0]["layers"][0]["layer_id"] == "layer:0"
    if kind == "deck":
        assert payload["pages"][1]["width"] == 60
        assert any(
            finding["code"] == "mixed-slide-size" for finding in payload["diagnostics"]["findings"]
        )


@pytest.mark.parametrize("kind", ["canvas", "deck"])
def test_generic_consumer_joins_sample_frames_to_inspected_pages(kind: str):
    canvas = _canvas()
    source = canvas if kind == "canvas" else Deck(slides=[canvas, Canvas(60, 40)])
    layout = json.loads(inspect_document(source).model_dump_json())
    sequence = FrameSequence.model_validate_json(source.sample().model_dump_json())

    # No document-kind branch is needed to read a sample and its layout.
    assert sequence.kind == layout["kind"]
    assert [frame.index for frame in sequence.frames] == list(range(len(layout["pages"])))
    for frame in sequence.frames:
        page = layout["pages"][frame.slide]
        assert (frame.width, frame.height) == (page["width"], page["height"])
        assert frame.mode == "RGBA"
        assert frame.time is None
    assert sequence.capture == "still"
    assert sequence.duration == 0


def test_first_page_dimensions_are_unambiguous_for_mixed_size_decks():
    deck = Deck(100, 80).slide(Canvas(48, 32)).slide(Canvas(60, 40))
    report = inspect_document(deck)

    assert (report.width, report.height) == (48, 32)
    assert [(page.width, page.height) for page in report.pages] == [(48, 32), (60, 40)]
    # The old report still preserves the authored deck default size.
    assert (deck.inspect().width, deck.inspect().height) == (100, 80)


@pytest.mark.parametrize("kind", ["canvas", "deck"])
def test_observed_asset_manifest_matches_public_resolution(kind: str, tmp_path: Path):
    asset = tmp_path / "image.png"
    Image.new("RGBA", (2, 3), (255, 0, 0, 255)).save(asset)
    canvas = Canvas(48, 32).image(str(asset), position=(0, 0), width=2, height=3)
    source = canvas if kind == "canvas" else Deck(slides=[canvas])

    report = inspect_document(source)

    assert report.asset_manifest == source.prefetch_assets().asset_manifest
    assert report.asset_manifest[0].content_hash == hashlib.sha256(asset.read_bytes()).hexdigest()
    assert report.asset_manifest[0].status == "local"
    assert report.asset_manifest[0].source == str(asset)


def test_capabilities_and_fallbacks_are_retained_with_requested_policy():
    canvas = Canvas(48, 32).shape(
        shape="rectangle",
        position=(4, 5),
        width=8,
        height=6,
        color="#FF0000",
        animation=AnimationSpec.timeline(
            BlurTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=4)])
        ),
    )
    report = inspect_document(canvas, target=["pptx", "video"], fps=4, max_samples=3)

    assert {row.target for row in report.motion.capabilities} == {"pptx", "video"}
    assert any(row.fallback for row in report.motion.diagnostics if row.target == "pptx")
    assert len(report.motion.sample_times) <= 3
    reduced = inspect_document(canvas, policy=ExportPolicy(reduced_motion=True))
    assert reduced.motion.reduced_motion.enabled
    assert reduced.motion.duration == 0


def test_sample_duration_keeps_capture_semantics_separate_from_motion_inspection():
    canvas = _canvas()
    report = inspect_document(canvas)
    sequence = canvas.sample(time=[0, 0.5], hold=2)

    assert report.motion.duration == 0  # no authored motion
    assert sequence.duration == 2  # canonical capture includes the settled hold
    assert [frame.time for frame in sequence.frames] == [0, 0.5]
    assert sequence.timeline[0].slide == 0
    assert sequence.timeline[0].end == 2


def test_deck_diagnostics_keep_their_page_locations():
    outside = Canvas(48, 32).shape(
        shape="rectangle", position=(-5, -5), width=8, height=6, color="#FF0000"
    )
    report = inspect_document(Deck(slides=[Canvas(48, 32), outside]))
    payload = report.model_dump(mode="json")
    findings = payload["diagnostics"]["findings"]

    assert findings
    assert all(finding["slide_index"] == 1 for finding in findings)
    assert all(finding["layer_id"] == "layer:0" for finding in findings)


@pytest.mark.parametrize(
    "options",
    [{"fps": 0}, {"fps": float("nan")}, {"max_samples": 1}, {"target": "unknown"}],
)
def test_invalid_inspection_options_preserve_structured_errors(options: dict):
    with pytest.raises(ValidationError):
        inspect_document(_canvas(), **options)


def test_empty_deck_and_missing_assets_preserve_actionable_errors(tmp_path: Path):
    with pytest.raises(RenderingError, match="empty deck"):
        inspect_document(Deck())
    canvas = Canvas(48, 32).image(str(tmp_path / "missing.png"), position=(0, 0))
    with pytest.raises(MissingAssetError) as caught:
        inspect_document(canvas)
    assert caught.value.details[0].code == "asset_missing"
