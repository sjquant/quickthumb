import importlib

import pytest


def require_cairosvg():
    try:
        cairosvg = importlib.import_module("cairosvg")
        cairosvg.svg2png(
            bytestring=b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'
        )
    except (ImportError, OSError) as e:
        pytest.skip(f"CairoSVG is unavailable: {e}")
    return cairosvg


def require_pypdfium2():
    try:
        return importlib.import_module("pypdfium2")
    except (ImportError, OSError) as e:
        pytest.skip(f"pypdfium2 is unavailable: {e}")


def _has_video_tool(name: str, setting: str) -> bool:
    from quickthumb._video import _tool
    from quickthumb.errors import RenderingError

    try:
        _tool(name, setting)
    except RenderingError:
        return False
    return True


requires_ffprobe = pytest.mark.skipif(
    not _has_video_tool("ffprobe", "QUICKTHUMB_FFPROBE"),
    reason="ffprobe is required (install FFmpeg or set QUICKTHUMB_FFPROBE)",
)
