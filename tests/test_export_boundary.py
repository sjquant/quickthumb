"""Public compatibility checks for shared and specialist export entry points."""

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from PIL.GifImagePlugin import GifImageFile
from quickthumb import Canvas, Deck


@pytest.fixture(params=["canvas", "deck"])
def document(request):
    canvas = Canvas(32, 24).background(color="#123456")
    if request.param == "canvas":
        return canvas
    return Deck(slides=[canvas, Canvas(32, 24).background(color="#654321")])


def test_canvas_png_export_matches_render(tmp_path: Path):
    """
    A canvas exported to PNG through export() reports the one written file, and that
    file has the same pixels as the canvas's render() output, which returns None.
    """
    # Given
    canvas = Canvas(32, 24).background(color="#123456")

    # When
    rendered = canvas.render(str(tmp_path / "specialist.png"))
    result = canvas.export(tmp_path / "shared.png")

    # Then
    assert rendered is None
    assert result.kind == "canvas"
    assert result.written_paths == [str(tmp_path / "shared.png")]
    assert result.pixel_metrics.frame_count == 1
    assert_same_pixels(str(tmp_path / "specialist.png"), result.written_paths[0])


def test_deck_png_export_matches_render(tmp_path: Path):
    """
    A two-slide deck exported to PNG through export() reports two numbered slide
    files, each with the same pixels as the matching file listed by render().
    """
    # Given
    deck = Deck(
        slides=[
            Canvas(32, 24).background(color="#123456"),
            Canvas(32, 24).background(color="#654321"),
        ]
    )

    # When
    rendered = deck.render(str(tmp_path / "specialist.png"))
    result = deck.export(tmp_path / "shared.png")

    # Then
    assert rendered == [str(tmp_path / f"specialist_{index:02}.png") for index in (1, 2)]
    assert result.kind == "deck"
    assert result.written_paths == [str(tmp_path / f"shared_{index:02}.png") for index in (1, 2)]
    assert result.pixel_metrics.frame_count == 2
    for specialist, shared in zip(rendered, result.written_paths, strict=True):
        assert_same_pixels(specialist, shared)


def test_html_export_writes_to_html_markup(document, tmp_path: Path):
    """
    Exporting a canvas or deck to an .html path writes exactly the markup that
    to_html() returns in memory.
    """
    # Given
    markup = document.to_html()

    # When
    result = document.export(tmp_path / "shared.html")

    # Then
    assert result.output_format == "html"
    assert result.written_paths == [str(tmp_path / "shared.html")]
    assert Path(result.written_paths[0]).read_text(encoding="utf-8") == markup


def test_gif_export_matches_to_gif_frames_and_timing(document, tmp_path: Path):
    """
    Exporting a canvas or deck to a .gif path writes the same frames, frame
    durations, and loop count as to_gif(), and reports that frame count.
    """
    # Given
    payload = document.to_gif()

    # When
    result = document.export(tmp_path / "shared.gif")

    # Then
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


def test_canvas_svg_export_writes_to_svg_markup(tmp_path: Path):
    """
    Exporting a canvas to an .svg path writes exactly the markup that to_svg()
    returns in memory.
    """
    # Given
    canvas = Canvas(32, 24).background(color="#123456")

    # When
    result = canvas.export(tmp_path / "card.svg")

    # Then
    assert result.output_format == "svg"
    assert Path(result.written_paths[0]).read_text(encoding="utf-8") == canvas.to_svg()


def assert_same_pixels(expected_path: str, actual_path: str) -> None:
    with Image.open(expected_path) as expected, Image.open(actual_path) as actual:
        assert expected.size == actual.size
        assert expected.convert("RGBA").tobytes() == actual.convert("RGBA").tobytes()
