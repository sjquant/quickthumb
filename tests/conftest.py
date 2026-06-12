import os
import tempfile
from pathlib import Path

import pytest
from inline_snapshot import Format, register_format

# Pin fontconfig (used by cairosvg) to the repo fonts so SVG rasterization in
# snapshot tests resolves the same font files as the PIL pipeline, independent
# of fonts installed on the host machine. Must be set before cairo first loads
# fontconfig, hence at conftest import time.
_REPO_FONTS_DIR = (Path(__file__).parent / ".." / "assets" / "fonts").resolve()
_FONTCONFIG_DIR = Path(tempfile.mkdtemp(prefix="quickthumb_fontconfig_"))
(_FONTCONFIG_DIR / "fonts.conf").write_text(
    f"""<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <dir>{_REPO_FONTS_DIR}</dir>
  <cachedir>{_FONTCONFIG_DIR / "cache"}</cachedir>
</fontconfig>
"""
)
os.environ["FONTCONFIG_FILE"] = str(_FONTCONFIG_DIR / "fonts.conf")


class ImageFormat(Format):
    suffix = ".png"

    def decode(self, path: Path) -> bytes:
        return path.read_bytes()

    def encode(
        self,
        value: bytes,
        path: Path,
    ) -> None:
        path.write_bytes(value)

    def is_format_for(self, value: object) -> bool:
        return isinstance(value, bytes)

    def rich_show(self, path: Path) -> str:
        return f"ImageFormat: {path!r}"

    def rich_diff(self, original: Path, new: Path) -> str:
        return f"ImageChanged. See snapshot {original} for details."


@register_format
class PNGFormat(ImageFormat):
    suffix = ".png"


@register_format
class JPGFormat(ImageFormat):
    suffix = ".jpg"


@register_format
class WebPFormat(ImageFormat):
    suffix = ".webp"


@pytest.fixture(autouse=True)
def setup_font_dir(monkeypatch):
    from pathlib import Path

    fixtures_dir = Path(__file__).parent / ".." / "assets" / "fonts"
    monkeypatch.setenv("QUICKTHUMB_FONT_DIR", str(fixtures_dir))
    yield
    monkeypatch.delenv("QUICKTHUMB_FONT_DIR", raising=False)


@pytest.fixture(autouse=True)
def setup_default_font(monkeypatch):
    monkeypatch.setenv("QUICKTHUMB_DEFAULT_FONT", "NotoSans")
    yield
    monkeypatch.delenv("QUICKTHUMB_DEFAULT_FONT", raising=False)
