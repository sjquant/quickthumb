"""Loaded FreeType faces are reused across canvases without sharing mutations."""

import copy
import os
import pickle
import shutil
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

import pytest
from PIL import ImageFont
from quickthumb import Canvas, _fonts
from quickthumb._fonts import FontEngine
from quickthumb.asset_cache import AssetResolver
from quickthumb.errors import RenderingError
from quickthumb.font_cache import FontCache

_FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
_REGULAR = _FONTS / "Roboto-Regular.ttf"
_VARIABLE = _FONTS / "RobotoFlex-Variable.ttf"


@pytest.fixture(autouse=True)
def isolate_loaded_fonts(monkeypatch):
    monkeypatch.setattr(_fonts, "_LOADED_FONTS", OrderedDict())
    monkeypatch.setattr(FontCache, "_instance", None)


@pytest.fixture
def getfont_calls(monkeypatch):
    calls = Mock(wraps=ImageFont.core.getfont)
    monkeypatch.setattr(ImageFont.core, "getfont", calls)
    return calls


def _load(name, size=24, **kwargs):
    return FontEngine().load_font_variant(name, size, False, False, **kwargs)


def test_reuses_unique_faces_across_canvases_and_frames(getfont_calls):
    images = []
    for _ in range(3):
        canvas = (
            Canvas(320, 180)
            .background(color="#FFFFFF")
            .text("Regular", font="Roboto", size=24, position=(10, 10))
            .text("Bold", font="Roboto", size=24, bold=True, position=(10, 50))
            .text("Large", font="Roboto", size=32, position=(10, 90))
        )
        for frame_time in (0, 0.5):
            output = BytesIO()
            canvas.render_frame(frame_time).save(output, format="PNG")
            images.append(output.getvalue())

    assert getfont_calls.call_count == 3
    assert all(image == images[0] for image in images)


def test_resolved_aliases_share_one_face(getfont_calls, tmp_path):
    alias = tmp_path / "alias.ttf"
    alias.symlink_to(_REGULAR)
    fonts = [
        _load("Roboto"),
        _load("ROBOTO"),
        _load("assets/fonts/Roboto-Regular.ttf"),
        _load(str(_REGULAR)),
        _load(str(alias)),
    ]
    assert all(font is fonts[0] for font in fonts)
    assert getfont_calls.call_count == 1


def test_sizes_and_style_faces_are_separate(getfont_calls):
    fonts = [
        FontEngine().load_font_variant("Roboto", size, bold, italic)
        for size, bold, italic in [
            (24, False, False),
            (32, False, False),
            (24, True, False),
            (24, False, True),
        ]
    ]
    assert len({id(font) for font in fonts}) == 4
    assert getfont_calls.call_count == 4


def test_variable_axes_are_applied_before_sharing(getfont_calls):
    narrow = _load(str(_VARIABLE), font_variations={"wdth": 25})
    narrow_pixels = bytes(narrow.getmask("Variable width"))
    wide = _load(str(_VARIABLE), font_variations={"wdth": 151})
    default = _load(str(_VARIABLE))

    assert narrow is _load(str(_VARIABLE), font_variations={"WDTH": 25})
    assert narrow is not wide and wide is not default
    assert bytes(narrow.getmask("Variable width")) == narrow_pixels
    assert bytes(wide.getmask("Variable width")) != narrow_pixels
    assert getfont_calls.call_count == 3


def test_normalizes_weight_names_and_axis_order(getfont_calls):
    first = _load(str(_VARIABLE), weight="semi-bold", font_variations={"WDTH": 75, "opsz": 20})
    second = _load(str(_VARIABLE), weight=600, font_variations={"opsz": 20, "wdth": 75})
    assert first is second
    assert getfont_calls.call_count == 1


def test_replays_static_variation_warning_on_new_engine(getfont_calls):
    for _ in range(2):
        with pytest.warns(UserWarning, match="selected font is not variable"):
            _load(str(_REGULAR), font_variations={"wdth": 75})
    assert getfont_calls.call_count == 1


def test_reloads_replaced_local_font(getfont_calls, tmp_path):
    path = tmp_path / "font.ttf"
    shutil.copyfile(_REGULAR, path)
    first = _load(str(path))
    replacement = tmp_path / "replacement.ttf"
    shutil.copyfile(_FONTS / "Roboto-Bold.ttf", replacement)
    original_stat = path.stat()
    os.utime(replacement, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
    replacement.replace(path)
    second = _load(str(path))

    assert second is not first
    assert first.getname() != second.getname()
    assert getfont_calls.call_count == 2


def test_fallback_does_not_hide_new_file_or_default(monkeypatch, tmp_path):
    missing = tmp_path / "NewFont.ttf"
    fallback = _load(str(missing))
    shutil.copyfile(_REGULAR, missing)
    assert _load(str(missing)).getname() != fallback.getname()

    monkeypatch.setenv("QUICKTHUMB_DEFAULT_FONT", "Roboto")
    assert _load(None).getname() != fallback.getname()


def test_pillow_filename_precedes_discovered_family(monkeypatch, tmp_path, getfont_calls):
    system_fonts = tmp_path / "fonts"
    system_fonts.mkdir()
    shutil.copyfile(_FONTS / "Roboto-Bold.ttf", system_fonts / "Roboto.ttf")
    monkeypatch.setattr(_fonts.sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_DIRS", str(tmp_path / "absent"))

    by_filename = _load("Roboto")
    assert by_filename.getname()[1] == "Bold"
    assert by_filename is _load("missing/path/Roboto.ttf")
    assert getfont_calls.call_count == 1


def test_corrupt_direct_path_can_fall_back_to_pillow_filename(monkeypatch, tmp_path):
    system_fonts = tmp_path / "fonts"
    system_fonts.mkdir()
    shutil.copyfile(_REGULAR, system_fonts / "Roboto.ttf")
    broken = tmp_path / "Roboto.ttf"
    broken.write_bytes(b"invalid font")
    monkeypatch.setattr(_fonts.sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_DIRS", str(tmp_path / "absent"))

    assert _load(str(broken)).getname() == ("Roboto", "Regular")


def test_builtin_default_is_cached_by_size(monkeypatch, getfont_calls):
    monkeypatch.delenv("QUICKTHUMB_DEFAULT_FONT")
    first = _load(None)
    assert first is _load(None)
    assert first is not _load(None, size=32)
    assert getfont_calls.call_count == 2


def test_cached_remote_font_still_respects_resolver_policy(monkeypatch, tmp_path):
    url = "https://example.com/font.ttf"
    online = FontEngine(AssetResolver(cache_dir=tmp_path / "online"))
    monkeypatch.setattr(online, "_download_and_cache_font", lambda _: str(_REGULAR))
    online.load_font_variant(url, 24, False, False)

    offline = FontEngine(AssetResolver(cache_dir=tmp_path / "offline", offline=True))
    with pytest.raises(RenderingError, match="offline mode is enabled"):
        offline.load_font_variant(url, 24, False, False)


def test_failed_font_load_can_be_retried(monkeypatch, tmp_path):
    path = tmp_path / "font.ttf"
    path.write_bytes(b"invalid font")
    engine = FontEngine()
    monkeypatch.setattr(engine, "_download_and_cache_font", lambda _: str(path))
    with pytest.raises(RenderingError, match="Could not load font"):
        engine.load_font_variant("https://example.com/font.ttf", 24, False, False)
    shutil.copyfile(_REGULAR, path)
    font = engine.load_font_variant("https://example.com/font.ttf", 24, False, False)
    assert isinstance(font, ImageFont.FreeTypeFont)
    assert font.getname() == ("Roboto", "Regular")


def test_loaded_face_cache_is_bounded_lru(monkeypatch, getfont_calls):
    monkeypatch.setattr(_fonts, "_MAX_LOADED_FONTS", 2)
    first = _load(str(_REGULAR), 24)
    evicted = _load(str(_REGULAR), 25)
    assert first is _load(str(_REGULAR), 24)
    _load(str(_REGULAR), 26)
    assert first is _load(str(_REGULAR), 24)
    assert evicted is not _load(str(_REGULAR), 25)
    assert len(_fonts._LOADED_FONTS) == 2
    assert getfont_calls.call_count == 4


def test_concurrent_loads_publish_only_one_configured_face(monkeypatch):
    original_getfont = ImageFont.core.getfont
    start = threading.Barrier(4)

    def slow_getfont(*args, **kwargs):
        time.sleep(0.01)
        return original_getfont(*args, **kwargs)

    calls = Mock(side_effect=slow_getfont)
    monkeypatch.setattr(ImageFont.core, "getfont", calls)

    def load_and_render(_):
        start.wait(timeout=5)
        font = _load(str(_VARIABLE), font_variations={"wdth": 75})
        return font, bytes(font.getmask("Shared variable font"))

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(load_and_render, range(4)))
    assert all(font is results[0][0] and pixels == results[0][1] for font, pixels in results)
    assert calls.call_count == 1


def test_reloads_actual_pillow_fallback_when_requested_file_is_corrupt(monkeypatch, tmp_path):
    system_fonts = tmp_path / "fonts"
    system_fonts.mkdir()
    fallback = system_fonts / "Collision.ttf"
    shutil.copyfile(_REGULAR, fallback)
    broken = tmp_path / "Collision.ttf"
    broken.write_bytes(b"invalid font")
    monkeypatch.setattr(_fonts.sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_DIRS", str(tmp_path / "absent"))

    first = _load(str(broken))
    replacement = system_fonts / "replacement.ttf"
    shutil.copyfile(_FONTS / "Roboto-Bold.ttf", replacement)
    replacement.replace(fallback)
    second = _load(str(broken))

    assert first.getname()[1] == "Regular"
    assert second.getname()[1] == "Bold"
    assert second is not first


def test_corrupt_symlink_uses_requested_filename_for_pillow_fallback(monkeypatch, tmp_path):
    system_fonts = tmp_path / "fonts"
    system_fonts.mkdir()
    shutil.copyfile(_REGULAR, system_fonts / "Alias.ttf")
    broken = tmp_path / "Broken.ttf"
    broken.write_bytes(b"invalid font")
    alias = tmp_path / "Alias.ttf"
    alias.symlink_to(broken)
    monkeypatch.setattr(_fonts.sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_DIRS", str(tmp_path / "absent"))

    assert _load(str(alias)).getname() == ("Roboto", "Regular")


def test_corrupt_filename_aliases_do_not_recurse(monkeypatch, tmp_path):
    system_fonts = tmp_path / "fonts"
    system_fonts.mkdir()
    first = tmp_path / "First.ttf"
    second = tmp_path / "Second.ttf"
    first.write_bytes(b"invalid font")
    second.write_bytes(b"invalid font")
    (system_fonts / first.name).symlink_to(second)
    (system_fonts / second.name).symlink_to(first)
    monkeypatch.setattr(_fonts.sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_DIRS", str(tmp_path / "absent"))

    assert _load(str(first)) is _load(None)


@pytest.mark.parametrize(
    ("platform", "expected"),
    [
        ("win32", ["/windows/fonts"]),
        (
            "darwin",
            ["/Library/Fonts", "/System/Library/Fonts", os.path.expanduser("~/Library/Fonts")],
        ),
        (
            "linux",
            [
                os.path.expanduser("~/.local/share/fonts"),
                "/usr/local/share/fonts",
                "/usr/share/fonts",
            ],
        ),
        ("other", []),
    ],
)
def test_pillow_filename_search_uses_platform_directories(monkeypatch, platform, expected):
    visited = []

    def empty_walk(directory):
        visited.append(directory)
        return []

    monkeypatch.setattr(_fonts.sys, "platform", platform)
    monkeypatch.setattr(_fonts.os, "walk", empty_walk)
    monkeypatch.setenv("WINDIR", "/windows")
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.delenv("XDG_DATA_DIRS", raising=False)
    assert FontEngine._find_pillow_font("Missing") is None
    assert visited == expected


@pytest.mark.parametrize(
    ("font_name", "filenames", "expected"),
    [
        ("Font", ["Font.otf", "Font.ttf"], "Font.ttf"),
        ("Font", ["Font.otf"], "Font.otf"),
        ("Font.otf", ["Font.ttf", "Font.otf"], "Font.otf"),
    ],
)
def test_pillow_filename_search_preserves_extension_precedence(
    monkeypatch, font_name, filenames, expected
):
    monkeypatch.setattr(_fonts.sys, "platform", "win32")
    monkeypatch.setenv("WINDIR", "/windows")
    monkeypatch.setattr(_fonts.os, "walk", lambda _: [("/windows/fonts", [], filenames)])
    assert FontEngine._find_pillow_font(font_name) == f"/windows/fonts/{expected}"


def test_simultaneous_canvases_render_shared_faces_identically(getfont_calls):
    def render(index):
        canvas = (
            Canvas(320, 120)
            .background(color="#FFFFFF")
            .text(
                f"Shared face {index}",
                font=str(_VARIABLE),
                font_variations={"wdth": 75},
                size=24,
                position=(10, 20),
            )
        )
        output = BytesIO()
        canvas.render_frame().save(output, format="PNG")
        return output.getvalue()

    expected = [render(index) for index in range(4)]
    indices = list(range(4)) * 5
    with ThreadPoolExecutor(max_workers=4) as pool:
        images = list(pool.map(render, indices))
    assert all(image == expected[index] for image, index in zip(images, indices, strict=True))
    assert getfont_calls.call_count == 1


def test_concurrent_color_font_renders_keep_their_foreground_palette(monkeypatch, tmp_path):
    from fontTools.colorLib.builder import buildCOLR, buildCPAL
    from fontTools.ttLib import TTFont
    from PIL import Image

    # Add a COLR foreground-color glyph to a bundled font instead of relying on
    # an installed emoji font or a network fixture.
    path = tmp_path / "color.ttf"
    with TTFont(_REGULAR) as source:
        cmap = source.getBestCmap()
        assert cmap is not None
        glyph = cmap[ord("A")]
        source["COLR"] = buildCOLR(
            {glyph: [(glyph, 0xFFFF)]}, version=0, glyphMap=source.getReverseGlyphMap()
        )
        source["CPAL"] = buildCPAL([[(0, 0, 0, 1)]])
        source.save(path)
    font = _load(str(path))
    assert isinstance(font, ImageFont.FreeTypeFont)

    def render(ink):
        mask, offset = font.getmask2("A", mode="RGBA", ink=ink)
        return Image.Image()._new(mask).tobytes(), offset

    red, blue = 0xFF0000FF, 0xFFFF0000
    expected_red, expected_blue = render(red), render(blue)
    assert expected_red != expected_blue
    red_paused = threading.Event()
    release_red = threading.Event()
    blue_started = threading.Event()
    blue_finished = threading.Event()
    first_thread = None
    original_check = Image._decompression_bomb_check

    def pause_red(size):
        original_check(size)
        if threading.get_ident() == first_thread:
            red_paused.set()
            assert release_red.wait(timeout=5)

    def render_red():
        nonlocal first_thread
        first_thread = threading.get_ident()
        return render(red)

    def render_blue():
        blue_started.set()
        result = render(blue)
        blue_finished.set()
        return result

    monkeypatch.setattr(Image, "_decompression_bomb_check", pause_red)
    with ThreadPoolExecutor(max_workers=2) as pool:
        red_future = pool.submit(render_red)
        try:
            assert red_paused.wait(timeout=5)
            blue_future = pool.submit(render_blue)
            assert blue_started.wait(timeout=5)
            # The second render must wait while the first is inside Pillow's
            # Python allocation callback with its foreground palette selected.
            assert not blue_finished.wait(timeout=0.05)
        finally:
            release_red.set()
        assert red_future.result(timeout=5) == expected_red
        assert blue_future.result(timeout=5) == expected_blue


@pytest.mark.parametrize("name", [None, str(_REGULAR)])
def test_cached_faces_preserve_pillow_font_variant(monkeypatch, name):
    monkeypatch.delenv("QUICKTHUMB_DEFAULT_FONT", raising=False)
    font = _load(name)
    assert isinstance(font, ImageFont.FreeTypeFont)
    assert isinstance(font, _fonts._CachedFreeTypeFont)
    variant = font.font_variant(size=32)
    assert isinstance(variant, _fonts._CachedFreeTypeFont)
    assert variant is not font
    assert variant.size == 32
    assert font.size == 24
    assert variant.getname() == font.getname()
    assert variant.getbbox("Clone") != font.getbbox("Clone")


@pytest.mark.parametrize("use_pickle", [False, True])
def test_cached_file_faces_preserve_copy_and_pickle(use_pickle):
    font = _load(str(_REGULAR))
    cloned = pickle.loads(pickle.dumps(font)) if use_pickle else copy.copy(font)
    assert isinstance(cloned, _fonts._CachedFreeTypeFont)
    assert cloned is not font
    assert cloned.getname() == font.getname()
    assert bytes(cloned.getmask("Copy")) == bytes(font.getmask("Copy"))


def test_cached_font_constructor_accepts_pillow_options():
    font = _fonts._CachedFreeTypeFont(
        font=str(_REGULAR), size=24, index=0, encoding="", layout_engine=ImageFont.Layout.BASIC
    )
    assert font.layout_engine == ImageFont.Layout.BASIC
    assert font.getname() == ("Roboto", "Regular")
    assert font.font_variant(size=32).layout_engine == ImageFont.Layout.BASIC
