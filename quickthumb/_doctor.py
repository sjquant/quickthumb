"""Environment readiness checks for a requested export workflow.

`check_environment` probes the requirements of one workflow (optional Python
packages, FFmpeg tools, fonts, the remote-asset cache, plugin registrations, and
output permissions) and reports each as a `Finding`. A `required` failure
(`status="error"`) would make the workflow fail; an optional limitation
(`status="warning"`) only degrades it. Every non-ok finding carries a `remedy`.

All probes go through the injectable `Environment`, so tests never depend on
what is installed on the machine running them.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import tempfile
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from quickthumb._base import is_url
from quickthumb.asset_cache import _CACHE_DIR_ENV, _OFFLINE_ENV, _OFFLINE_VALUES

Status = Literal["ok", "warning", "error"]

WORKFLOWS = ("png", "jpeg", "webp", "gif", "svg", "html", "pdf", "pptx", "mp4", "webm", "mov")
_VIDEO_WORKFLOWS = ("mp4", "webm", "mov")
_FONT_SUFFIXES = (".ttf", ".otf", ".ttc", ".woff", ".woff2")
# module -> (name shown to the user, pip extra that installs it)
_MODULES = {
    "reportlab": ("reportlab", "pdf"),
    "fontTools": ("fonttools", "pdf"),
    "pptx": ("python-pptx", "pptx"),
    "cairosvg": ("cairosvg", "svg"),
    "rembg": ("rembg", "rembg"),
}
_WORKFLOW_MODULES = {"pdf": ("reportlab", "fontTools"), "pptx": ("pptx",)}
_FFMPEG_INSTALL = (
    "install FFmpeg (macOS: brew install ffmpeg; Debian/Ubuntu: sudo apt install ffmpeg)"
)


@dataclass(frozen=True)
class Finding:
    """One probed requirement and, when it is not met, how to fix it."""

    check: str
    category: str
    status: Status
    message: str
    remedy: str | None = None

    def to_dict(self) -> dict[str, str]:
        payload = {
            "check": self.check,
            "category": self.category,
            "status": self.status,
            "message": self.message,
        }
        if self.remedy is not None:
            payload["remedy"] = self.remedy
        return payload


@dataclass(frozen=True)
class EnvironmentReport:
    """Findings for one workflow. `ok` is False when a required check failed."""

    workflow: str
    findings: tuple[Finding, ...]

    @property
    def errors(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.status == "error")

    @property
    def warnings(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.status == "warning")

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow": self.workflow,
            "ok": self.ok,
            "findings": [finding.to_dict() for finding in self.findings],
        }

    def format(self) -> str:
        marks = {"ok": "ok   ", "warning": "warn ", "error": "FAIL "}
        lines = [f"Environment check for {self.workflow}:"]
        for finding in self.findings:
            lines.append(f"  [{marks[finding.status]}] {finding.category}: {finding.message}")
            if finding.remedy:
                lines.append(f"         fix: {finding.remedy}")
        summary = "ready" if self.ok else "NOT ready"
        lines.append(
            f"{summary}: {len(self.errors)} required failure(s), "
            f"{len(self.warnings)} optional limitation(s)"
        )
        return "\n".join(lines)


@dataclass(frozen=True)
class Requirements:
    """What a document adds to a workflow's requirements."""

    plugins: frozenset[str] = frozenset()
    fonts: frozenset[str] = frozenset()
    svg_layers: bool = False
    video_layers: bool = False
    background_removal: bool = False
    remote_assets: bool = False


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _find_font(family: str) -> str | None:
    from quickthumb.font_cache import FontCache

    return FontCache.get_instance().find_font(family)


def _registered_plugins() -> Iterable[str]:
    from quickthumb.plugins import plugin_registry

    return (definition.renderer for definition in plugin_registry.definitions())


@dataclass
class Environment:
    """The machine state the probes read; replace any field to fake it."""

    environ: Mapping[str, str] = field(default_factory=lambda: os.environ)
    which: Callable[[str], str | None] = shutil.which
    has_module: Callable[[str], bool] = _has_module
    find_font: Callable[[str], str | None] = _find_font
    registered_plugins: Callable[[], Iterable[str]] = _registered_plugins


def check_environment(
    workflow: str,
    requirements: Requirements | None = None,
    *,
    output: str | os.PathLike[str] | None = None,
    env: Environment | None = None,
) -> EnvironmentReport:
    """Check that the environment can run `workflow` and return every finding.

    `workflow` is an output format from `WORKFLOWS`. `requirements` adds what the
    document being exported needs. `output` is the file that will be written;
    `env` overrides the machine probes.
    """
    workflow = workflow.lower()
    if workflow not in WORKFLOWS:
        raise ValueError(f"Unknown workflow '{workflow}'. Must be one of: {', '.join(WORKFLOWS)}")
    requirements = requirements or Requirements()
    env = env or Environment()
    findings: list[Finding] = []

    modules = dict.fromkeys(_WORKFLOW_MODULES.get(workflow, ()), f"{workflow} export")
    if requirements.svg_layers:
        modules["cairosvg"] = "SVG layers"
    if requirements.background_removal:
        modules["rembg"] = "background removal"
    findings.extend(_package(env, module, feature) for module, feature in modules.items())

    is_video = workflow in _VIDEO_WORKFLOWS
    if is_video or requirements.video_layers or workflow == "gif":
        # GIF and plain canvas video need ffmpeg only for video layers/output; ffprobe is
        # needed for video layers, audio duration inference, and Deck MP4.
        feature = workflow if is_video else "video layers"
        findings.append(
            _media_tool(
                env,
                "ffmpeg",
                "QUICKTHUMB_FFMPEG",
                required=is_video or requirements.video_layers,
                feature=feature,
            )
        )
        if is_video or requirements.video_layers:
            findings.append(
                _media_tool(
                    env,
                    "ffprobe",
                    "QUICKTHUMB_FFPROBE",
                    required=requirements.video_layers,
                    feature=feature,
                )
            )

    findings.extend(_fonts(env, requirements.fonts))
    findings.extend(_plugins(env, requirements.plugins))
    if requirements.remote_assets:
        findings.append(_asset_cache(env))
    if output is not None:
        findings.append(_output(output))
    return EnvironmentReport(workflow=workflow, findings=tuple(findings))


def _package(env: Environment, module: str, feature: str) -> Finding:
    name, extra = _MODULES[module]
    check = f"python:{name}"
    try:
        available = env.has_module(module)
    except (ImportError, ValueError):
        available = False
    if available:
        return Finding(check, "dependency", "ok", f"{name} is installed ({feature})")
    return Finding(
        check,
        "dependency",
        "error",
        f"{name} is not installed but {feature} requires it",
        f"pip install 'quickthumb[{extra}]'",
    )


def _media_tool(
    env: Environment, name: str, setting: str, *, required: bool, feature: str
) -> Finding:
    configured = env.environ.get(setting)
    path = env.which(configured or name)
    check = f"tool:{name}"
    if path:
        return Finding(check, "media-tool", "ok", f"{name} found at {path}")
    where = f"{setting}={configured!r} is not executable" if configured else f"{name} not on PATH"
    return Finding(
        check,
        "media-tool",
        "error" if required else "warning",
        f"{where}, but {feature} requires it"
        if required
        else f"{where}; it is only needed for video output and video layers, "
        "audio duration inference, and Deck MP4",
        f"{_FFMPEG_INSTALL} or set {setting} to the {name} executable",
    )


def _fonts(env: Environment, families: Iterable[str]) -> list[Finding]:
    return [
        Finding(f"font:{family}", "font", "ok", f"font '{family}' is installed")
        if env.find_font(family)
        else Finding(
            f"font:{family}",
            "font",
            "warning",
            f"font '{family}' was not found; text will fall back to a default font",
            "install the font, point QUICKTHUMB_FONT_DIR at a directory containing it, "
            "or reference the font by file path or URL",
        )
        for family in sorted(families)
    ]


def _plugins(env: Environment, renderers: Iterable[str]) -> list[Finding]:
    registered = set(env.registered_plugins()) if renderers else set()
    return [
        Finding(f"plugin:{renderer}", "plugin", "ok", f"plugin '{renderer}' is registered")
        if renderer in registered
        else Finding(
            f"plugin:{renderer}",
            "plugin",
            "error",
            f"plugin renderer '{renderer}' is not registered",
            "call quickthumb.plugin_registry.register(...) for it before loading "
            "or exporting the document",
        )
        for renderer in sorted(renderers)
    ]


def _asset_cache(env: Environment) -> Finding:
    check = "asset-cache"
    directory = Path(
        env.environ.get(_CACHE_DIR_ENV)
        or env.environ.get("QUICKTHUMB_FONT_CACHE_DIR")
        or tempfile.gettempdir()
    ).expanduser()
    problem, _ = _cannot_write_under(directory)
    if problem is not None:
        return Finding(
            check,
            "asset-cache",
            "warning",
            f"asset cache directory '{directory}' is not usable: {problem}; "
            "remote assets cannot be cached or reused offline",
            f"set {_CACHE_DIR_ENV} to a writable directory",
        )
    offline = env.environ.get(_OFFLINE_ENV, "").strip().lower()
    if offline not in _OFFLINE_VALUES:
        allowed = ", ".join(sorted(repr(key) for key in _OFFLINE_VALUES))
        return Finding(
            check,
            "asset-cache",
            "warning",
            f"{_OFFLINE_ENV}={offline!r} is not a valid setting; asset resolution will fail",
            f"set {_OFFLINE_ENV} to one of {allowed}, or unset it",
        )
    suffix = "; offline mode is on, so only already-cached assets resolve"
    return Finding(
        check,
        "asset-cache",
        "ok",
        f"asset cache '{directory}' is writable{suffix if _OFFLINE_VALUES[offline] else ''}",
    )


def _output(output: str | os.PathLike[str]) -> Finding:
    path = Path(output).expanduser()
    check = "output"
    if path.is_dir():
        return Finding(
            check,
            "output",
            "error",
            f"output path '{path}' is a directory",
            "choose a file path, for example --output out/thumbnail.png",
        )
    problem, existing = _cannot_write_under(path.parent)
    if problem is not None:
        return Finding(
            check,
            "output",
            "error",
            f"cannot write to '{path}': {problem}",
            "choose a writable location or fix the directory permissions",
        )
    note = "" if existing == path.parent else " (its directory will be created)"
    return Finding(check, "output", "ok", f"output '{path}' is writable{note}")


def _cannot_write_under(directory: Path) -> tuple[str | None, Path]:
    """Return why files cannot be created in `directory` (None when they can).

    A directory that does not exist yet is judged by its nearest existing ancestor,
    which is returned too. Nothing is created; a scratch file is opened and removed
    to test real access.
    """
    existing = directory
    while not existing.exists() and existing != existing.parent:
        existing = existing.parent
    try:
        if not existing.is_dir():
            return f"'{existing}' is not a directory", existing
        with tempfile.TemporaryFile(dir=existing):
            pass
    except OSError as error:
        return error.strerror or str(error), existing
    return None, existing


def requirements_from_document(payload: object) -> Requirements:
    """Scan document JSON for the layers that add requirements to an export."""
    plugins: set[str] = set()
    fonts: set[str] = set()
    flags = {"svg_layers": False, "video_layers": False, "background_removal": False}
    remote = False

    def walk(node: Any) -> None:
        nonlocal remote
        if isinstance(node, dict):
            kind = node.get("type")
            if kind == "plugin" and isinstance(node.get("renderer"), str):
                plugins.add(node["renderer"])
            elif kind in {"svg", "video"}:
                flags[f"{kind}_layers"] = True
            if node.get("remove_background") is True:
                flags["background_removal"] = True
            font = node.get("font")
            if (
                isinstance(font, str)
                and font
                and not is_url(font)
                and not any(sep in font for sep in "/\\")
                and not font.lower().endswith(_FONT_SUFFIXES)
            ):
                fonts.add(font)
            for value in node.values():
                if isinstance(value, str) and is_url(value):
                    remote = True
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return Requirements(
        plugins=frozenset(plugins), fonts=frozenset(fonts), remote_assets=remote, **flags
    )
