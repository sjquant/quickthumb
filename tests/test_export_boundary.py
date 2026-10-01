"""Public compatibility checks for shared and specialist export entry points."""

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from PIL.GifImagePlugin import GifImageFile
from quickthumb import Canvas, Deck, ExportResult


@pytest.fixture(params=["canvas", "deck"])
def document(request):
    canvas = Canvas(32, 24).background(color="#123456")
    if request.param == "canvas":
        return canvas
    return Deck(slides=[canvas, Canvas(32, 24).background(color="#654321")])


def test_shared_export_preserves_specialist_raster_output(document, tmp_path: Path):
    """Both document kinds keep their render returns and produce the same pixels."""
    specialist_path = tmp_path / "specialist.png"
    rendered = document.render(str(specialist_path))
    result = document.export(tmp_path / "shared.png")

    assert isinstance(result, ExportResult)
    assert ExportResult.model_validate_json(result.model_dump_json()) == result
    if isinstance(document, Canvas):
        assert rendered is None
        paths = [str(specialist_path)]
        assert result.kind == "canvas"
        assert result.written_paths == [str(tmp_path / "shared.png")]
    else:
        assert rendered == [str(tmp_path / f"specialist_{index:02}.png") for index in (1, 2)]
        paths = rendered
        assert result.kind == "deck"
        assert result.written_paths == [
            str(tmp_path / f"shared_{index:02}.png") for index in (1, 2)
        ]
    assert result.pixel_metrics.frame_count == len(paths)
    for specialist, shared in zip(paths, result.written_paths, strict=True):
        with Image.open(specialist) as expected, Image.open(shared) as actual:
            assert expected.size == actual.size == (32, 24)
            assert expected.convert("RGBA").tobytes() == actual.convert("RGBA").tobytes()


def test_shared_html_preserves_in_memory_specialist_output(document, tmp_path: Path):
    """The shared writer preserves HTML while the specialist returns markup."""
    markup = document.to_html()
    result = document.export(tmp_path / "shared.html")

    assert isinstance(markup, str)
    assert result.output_format == "html"
    assert result.written_paths == [str(tmp_path / "shared.html")]
    assert Path(result.written_paths[0]).read_text(encoding="utf-8") == markup


def test_shared_gif_preserves_in_memory_specialist_output(document, tmp_path: Path):
    """GIF bytes retain frame pixels and timing through the shared entry point."""
    payload = document.to_gif()
    result = document.export(tmp_path / "shared.gif")

    assert isinstance(payload, bytes)
    assert result.output_format == "gif"
    with Image.open(BytesIO(payload)) as expected, Image.open(result.written_paths[0]) as actual:
        assert isinstance(expected, GifImageFile)
        assert isinstance(actual, GifImageFile)
        assert expected.n_frames == actual.n_frames == result.pixel_metrics.frame_count
        for index in range(expected.n_frames):
            expected.seek(index)
            actual.seek(index)
            assert expected.convert("RGBA").tobytes() == actual.convert("RGBA").tobytes()
            assert expected.info.get("duration") == actual.info.get("duration")
        assert expected.info.get("loop") == actual.info.get("loop")


def test_specialist_svg_remains_available_for_individual_deck_slides(tmp_path: Path):
    """Deck consumers can explicitly export each canvas through the SVG control."""
    deck = Deck(slides=[Canvas(32, 24).background(color="#123456")])
    for index, canvas in enumerate(deck):
        result = canvas.export(tmp_path / f"slide-{index}.svg")
        assert Path(result.written_paths[0]).read_text(encoding="utf-8") == canvas.to_svg()
