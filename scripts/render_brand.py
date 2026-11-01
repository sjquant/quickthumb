# /// script
# requires-python = ">=3.11"
# dependencies = ["resvg-py>=0.2,<1", "pillow>=13,<14"]
# ///
"""Render the brand SVG to the PNG and ICO sizes used by the project.

Run with: uv run scripts/render_brand.py
"""

import shutil
from io import BytesIO
from pathlib import Path

import resvg_py
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "assets" / "brand"
DOCS_BRAND = ROOT / "docs" / "assets" / "brand"


def main() -> None:
    png = resvg_py.svg_to_bytes(
        svg_path=str(BRAND / "quickthumb-icon.svg"), width=2048, height=2048
    )
    master = Image.open(BytesIO(png)).convert("RGBA")
    master.save(BRAND / "quickthumb-icon-master-transparent.png")
    opaque = Image.new("RGBA", master.size, "white")
    opaque.alpha_composite(master)
    opaque.convert("RGB").save(BRAND / "quickthumb-icon-master.png")

    for size in (16, 32, 48, 64, 152, 167, 180, 192, 256, 512, 1024):
        master.resize((size, size), Image.Resampling.LANCZOS).save(
            BRAND / f"quickthumb-icon-{size}.png"
        )
    shutil.copyfile(BRAND / "quickthumb-icon-32.png", BRAND / "favicon.png")
    shutil.copyfile(BRAND / "quickthumb-icon-180.png", BRAND / "apple-touch-icon.png")
    master.save(BRAND / "favicon.ico", sizes=[(size, size) for size in (16, 32, 48, 64)])

    for name in (
        "quickthumb-icon-192.png",
        "quickthumb-icon-512.png",
        "favicon.png",
        "favicon.ico",
        "apple-touch-icon.png",
        "quickthumb-icon.svg",
    ):
        shutil.copyfile(BRAND / name, DOCS_BRAND / name)
    shutil.copyfile(BRAND / "quickthumb-icon-512.png", DOCS_BRAND / "quickthumb-icon.png")
    shutil.copyfile(BRAND / "favicon.ico", ROOT / "docs" / "favicon.ico")
    shutil.copyfile(
        BRAND / "quickthumb-icon-192.png", ROOT / "quickthumb" / "html" / "quickthumb-icon.png"
    )


if __name__ == "__main__":
    main()
