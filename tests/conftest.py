from pathlib import Path

from inline_snapshot import Format, register_format


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
