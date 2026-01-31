from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass


@dataclass
class FontVariant:
    path: str
    weight: int
    italic: bool


class FontCache:
    _instance: FontCache | None = None
    _fonts: dict[str, list[FontVariant]]
    _initialized: bool

    WEIGHT_MAPPING = [
        ("extralight", 200),
        ("ultralight", 200),
        ("extrabold", 800),
        ("ultrabold", 800),
        ("semibold", 600),
        ("demibold", 600),
        ("hairline", 100),
        ("thin", 100),
        ("light", 300),
        ("regular", 400),
        ("normal", 400),
        ("medium", 500),
        ("bold", 700),
        ("black", 900),
        ("heavy", 900),
    ]

    ITALIC_PATTERNS = ["italic", "oblique", "it"]

    def __init__(self) -> None:
        self._fonts = {}
        self._initialized = False

    @classmethod
    def get_instance(cls) -> FontCache:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def default_font(self) -> str | None:
        font_name = os.environ.get("QUICKTHUMB_DEFAULT_FONT")
        if not font_name:
            return None
        return self.find_font(font_name, bold=False, italic=False)

    def find_font(self, family: str, bold: bool = False, italic: bool = False) -> str | None:
        if not self._initialized:
            self._discover_fonts()
            self._initialized = True

        family_lower = family.lower()
        if family_lower not in self._fonts:
            return None

        variants = self._fonts[family_lower]
        if not variants:
            return None

        target_weight = 700 if bold else 400
        candidates = [v for v in variants if v.italic == italic]

        if not candidates:
            candidates = variants

        exact_match = next((v for v in candidates if v.weight == target_weight), None)
        if exact_match:
            return exact_match.path

        best = min(candidates, key=lambda v: abs(v.weight - target_weight))
        return best.path

    def _discover_fonts(self) -> None:
        font_dirs = self._get_font_directories()

        for font_dir in font_dirs:
            if not os.path.exists(font_dir):
                continue

            self._scan_directory(font_dir)

    def _get_font_directories(self) -> list[str]:
        dirs = []

        custom_dir = os.environ.get("QUICKTHUMB_FONT_DIR")
        if custom_dir:
            dirs.append(custom_dir)
            return dirs

        if sys.platform == "darwin":
            dirs.extend(
                [
                    "/System/Library/Fonts",
                    "/System/Library/Fonts/Supplemental",
                    "/Library/Fonts",
                    os.path.expanduser("~/Library/Fonts"),
                ]
            )
        elif sys.platform == "win32":
            dirs.extend(
                [
                    os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts"),
                    os.path.expandvars("%LOCALAPPDATA%\\Microsoft\\Windows\\Fonts"),
                ]
            )
        else:
            dirs.extend(
                [
                    "/usr/share/fonts",
                    "/usr/local/share/fonts",
                    os.path.expanduser("~/.fonts"),
                    os.path.expanduser("~/.local/share/fonts"),
                ]
            )

        return dirs

    def _scan_directory(self, directory: str) -> None:
        try:
            for root, _, files in os.walk(directory):
                for filename in files:
                    if filename.lower().endswith((".ttf", ".otf")):
                        font_path = os.path.join(root, filename)
                        result = self._parse_font_filename(font_path)
                        if result:
                            family, variant = result
                            family_lower = family.lower()
                            if family_lower not in self._fonts:
                                self._fonts[family_lower] = []
                            self._fonts[family_lower].append(variant)
        except (OSError, PermissionError):
            pass

    def _parse_font_filename(self, font_path: str) -> tuple[str, FontVariant] | None:
        filename = os.path.basename(font_path)
        name_without_ext = os.path.splitext(filename)[0]

        family, variant_part = self._split_family_and_variant(name_without_ext)
        if not family:
            return None

        weight, is_italic = self._extract_weight_and_italic(variant_part)

        variant = FontVariant(path=font_path, weight=weight, italic=is_italic)
        return family, variant

    def _split_family_and_variant(self, name: str) -> tuple[str, str]:
        hyphen_match = re.match(r"^(.+?)[-_](.+)$", name)
        if hyphen_match:
            family, variant = hyphen_match.groups()
            return family, variant

        space_match = re.match(r"^(.+?)\s+(.*?)$", name)
        if space_match:
            family, variant = space_match.groups()
            weight, is_italic = self._extract_weight_and_italic(variant)
            if weight != 400 or is_italic:
                return family, variant

        return name, ""

    def _extract_weight_and_italic(self, variant_text: str) -> tuple[int, bool]:
        if not variant_text:
            return 400, False

        variant_lower = variant_text.lower()
        is_italic = any(pattern in variant_lower for pattern in self.ITALIC_PATTERNS)

        for pattern in self.ITALIC_PATTERNS:
            variant_lower = variant_lower.replace(pattern, "")

        variant_lower = variant_lower.strip("_- ")

        for weight_name, weight_value in self.WEIGHT_MAPPING:
            if weight_name in variant_lower:
                return weight_value, is_italic

        return 400, is_italic
