"""Smoke tests for the runnable example entrypoints."""

import runpy
from pathlib import Path

from quickthumb import Canvas, Deck
from quickthumb.models import DiagnosticReport

EXAMPLES_DIR = Path(__file__).parents[1] / "examples"


def test_launch_announcement_entrypoint_consumes_the_diagnostic_report(monkeypatch):
    """Given an empty report, when the card runs, then diagnosis does not abort rendering."""
    # Given: the public rendering entrypoints with external image work disabled
    monkeypatch.setattr(Canvas, "diagnose", lambda self: DiagnosticReport(findings=[]))
    monkeypatch.setattr(Canvas, "render", lambda self, *args, **kwargs: None)

    # When: the checked-in example is run as a script
    runpy.run_path(str(EXAMPLES_DIR / "launch_announcement.py"), run_name="__main__")


def test_product_hype_reel_entrypoint_consumes_the_diagnostic_report(monkeypatch):
    """Given an empty report, when the reel runs, then diagnosis reaches export."""
    # Given: the public rendering entrypoints with external encoding disabled
    monkeypatch.setattr(Deck, "diagnose", lambda self: DiagnosticReport(findings=[]))
    monkeypatch.setattr(Deck, "render", lambda self, *args, **kwargs: None)

    # When: the checked-in example is run as a script
    runpy.run_path(str(EXAMPLES_DIR / "product_hype_reel.py"), run_name="__main__")


def test_ordinary_moments_entrypoint_consumes_the_diagnostic_report(monkeypatch):
    """Given an empty report, when the film runs, then diagnosis reaches export."""
    # Given: the public encoding entrypoints with external encoding and file writes disabled
    monkeypatch.setattr(Deck, "diagnose", lambda self: DiagnosticReport(findings=[]))
    monkeypatch.setattr(Deck, "to_animated_mp4", lambda self, *args, **kwargs: b"")
    monkeypatch.setattr(Deck, "to_webm", lambda self, *args, **kwargs: b"")
    monkeypatch.setattr(Canvas, "to_gif", lambda self, *args, **kwargs: b"")
    monkeypatch.setattr(Path, "write_bytes", lambda self, data: len(data))

    # When: the checked-in example is run as a script
    runpy.run_path(str(EXAMPLES_DIR / "ordinary_moments.py"), run_name="__main__")
