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

Status = Literal["ok", "warning", "error"]

WORKFLOWS = ("png", "jpeg", "webp", "gif", "svg", "html", "pdf", "pptx", "mp4", "webm")
_FFMPEG_TOOLS = (("ffmpeg", "QUICKTHUMB_FFMPEG"), ("ffprobe", "QUICKTHUMB_FFPROBE"))
_PACKAGES: dict[str, tuple[tuple[str, str], ...]] = {
    "pdf": (("reportlab", "pdf"), ("fontTools", "pdf")),
    "pptx": (("pptx", "pptx"),),
}
_MODULE_EXTRAS = {
    "reportlab": "reportlab",
    "fontTools": "fonttools",
    "pptx": "python-pptx",
    "cairosvg": "cairosvg",
    "rembg": "rembg",
}


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


@dataclass
class Environment:
    """The machine state the probes read; replace any field to fake it."""

    environ: Mapping[str, str] = field(default_factory=lambda: os.environ)
    which: Callable[[str], str | None] = shutil.which
    has_module: Callable[[str], bool] = lambda name: importlib.util.find_spec(name) is not None
    find_font: Callable[[str], str | None] | None = None
    registered_plugins: Callable[[], Iterable[str]] | None = None

    def font_lookup(self) -> Callable[[str], str | None]:
        if self.find_font is not None:
            return self.find_font
        from quickthumb.font_cache import FontCache

        return FontCache.get_instance().find_font

    def plugin_names(self) -> set[str]:
        if self.registered_plugins is not None:
            return set(self.registered_plugins())
        from quickthumb.plugins import plugin_registry

        return {definition.renderer for definition in plugin_registry.definitions()}


def check_environment(
    workflow: str,
    *,
    output: str | os.PathLike[str] | None = None,
    plugins: Iterable[str] = (),
    fonts: Iterable[str] = (),
    svg_layers: bool = False,
    video_layers: bool = False,
    background_removal: bool = False,
    remote_assets: bool = False,
    env: Environment | None = None,
) -> EnvironmentReport:
    """Check that the environment can run `workflow` and return every finding.

    `workflow` is an output format from `WORKFLOWS`. The keyword flags add the
    requirements of the document being exported (`plugins` and `fonts` list the
    renderer names and font families it uses). `output` is the file that will be
    written; `env` overrides the machine probes.
    """
    workflow = workflow.lower()
    if workflow not in WORKFLOWS:
        raise ValueError(f"Unknown workflow '{workflow}'. Must be one of: {', '.join(WORKFLOWS)}")
    env = env or Environment()
    findings: list[Finding] = []

    for module, extra in _PACKAGES.get(workflow, ()):
        findings.append(_package(env, module, extra, required=True, feature=f"{workflow} export"))
    if svg_layers:
        findings.append(_package(env, "cairosvg", "svg", required=True, feature="SVG layers"))
    if background_removal:
        findings.append(
            _package(env, "rembg", "rembg", required=True, feature="background removal")
        )
    if workflow in {"mp4", "webm"} or video_layers:
        findings.extend(
            _ffmpeg(
                env,
                workflow if workflow in {"mp4", "webm"} else "video layers",
                probe_required=video_layers,
            )
        )
    elif workflow == "gif":
        findings.append(_ffmpeg_optional(env))

    findings.extend(_fonts(env, fonts))
    findings.extend(_plugins(env, plugins))
    if remote_assets:
        findings.append(_asset_cache(env))
    if output is not None:
        findings.append(_output(output))
    return EnvironmentReport(workflow=workflow, findings=tuple(findings))


def _package(env: Environment, module: str, extra: str, *, required: bool, feature: str) -> Finding:
    name = _MODULE_EXTRAS.get(module, module)
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
        "error" if required else "warning",
        f"{name} is not installed but {feature} requires it",
        f"pip install 'quickthumb[{extra}]'",
    )


def _tool(env: Environment, name: str, setting: str) -> str | None:
    configured = env.environ.get(setting)
    return env.which(configured or name)


def _ffmpeg(env: Environment, feature: str, *, probe_required: bool) -> list[Finding]:
    findings = []
    for name, setting in _FFMPEG_TOOLS:
        path = _tool(env, name, setting)
        check = f"tool:{name}"
        if path:
            findings.append(Finding(check, "media-tool", "ok", f"{name} found at {path}"))
        else:
            configured = env.environ.get(setting)
            where = (
                f"{setting}={configured!r} is not executable"
                if configured
                else f"{name} not on PATH"
            )
            required = name == "ffmpeg" or probe_required
            findings.append(
                Finding(
                    check,
                    "media-tool",
                    "error" if required else "warning",
                    f"{where}, but {feature} requires it"
                    if required
                    else f"{where}; it is only needed for video layers, audio duration "
                    "inference, and Deck MP4",
                    f"install FFmpeg (macOS: brew install ffmpeg; Debian/Ubuntu: "
                    f"sudo apt install ffmpeg) or set {setting} to the {name} executable",
                )
            )
    return findings


def _ffmpeg_optional(env: Environment) -> Finding:
    if _tool(env, "ffmpeg", "QUICKTHUMB_FFMPEG"):
        return Finding("tool:ffmpeg", "media-tool", "ok", "ffmpeg is available")
    return Finding(
        "tool:ffmpeg",
        "media-tool",
        "warning",
        "ffmpeg is not available; GIF export still works, but video layers and MP4/WebM do not",
        "install FFmpeg or set QUICKTHUMB_FFMPEG if you need video output or video layers",
    )


def _fonts(env: Environment, families: Iterable[str]) -> list[Finding]:
    findings = []
    find = env.font_lookup()
    for family in sorted(set(families)):
        if find(family):
            findings.append(
                Finding(f"font:{family}", "font", "ok", f"font '{family}' is installed")
            )
            continue
        findings.append(
            Finding(
                f"font:{family}",
                "font",
                "warning",
                f"font '{family}' was not found; text will fall back to a default font",
                "install the font, point QUICKTHUMB_FONT_DIR at a directory containing it, "
                "or reference the font by file path or URL",
            )
        )
    return findings


def _plugins(env: Environment, renderers: Iterable[str]) -> list[Finding]:
    wanted = sorted(set(renderers))
    if not wanted:
        return []
    registered = env.plugin_names()
    findings = []
    for renderer in wanted:
        if renderer in registered:
            findings.append(
                Finding(f"plugin:{renderer}", "plugin", "ok", f"plugin '{renderer}' is registered")
            )
        else:
            findings.append(
                Finding(
                    f"plugin:{renderer}",
                    "plugin",
                    "error",
                    f"plugin renderer '{renderer}' is not registered",
                    "call quickthumb.plugin_registry.register(...) for it before loading "
                    "or exporting the document",
                )
            )
    return findings


def _asset_cache(env: Environment) -> Finding:
    check = "asset-cache"
    directory = Path(
        env.environ.get("QUICKTHUMB_ASSET_CACHE_DIR")
        or env.environ.get("QUICKTHUMB_FONT_CACHE_DIR")
        or tempfile.gettempdir()
    ).expanduser()
    problem = _cannot_write_under(directory)
    if problem is not None:
        return Finding(
            check,
            "asset-cache",
            "warning",
            f"asset cache directory '{directory}' is not usable: {problem}; "
            "remote assets cannot be cached or reused offline",
            "set QUICKTHUMB_ASSET_CACHE_DIR to a writable directory",
        )
    offline = env.environ.get("QUICKTHUMB_ASSET_OFFLINE", "").lower() in {"1", "true", "yes", "on"}
    suffix = "; offline mode is on, so only already-cached assets resolve" if offline else ""
    return Finding(check, "asset-cache", "ok", f"asset cache '{directory}' is writable{suffix}")


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
    problem = _cannot_write_under(path.parent)
    if problem is not None:
        return Finding(
            check,
            "output",
            "error",
            f"cannot write to '{path}': {problem}",
            "choose a writable location or fix the directory permissions",
        )
    note = "" if path.parent.exists() else " (its directory will be created)"
    return Finding(check, "output", "ok", f"output '{path}' is writable{note}")


def _cannot_write_under(directory: Path) -> str | None:
    """Return why files cannot be created in `directory`, or None when they can.

    A directory that does not exist yet is judged by its nearest existing ancestor.
    Nothing is created; a scratch file is opened and removed to test real access.
    """
    existing = directory
    while not existing.exists() and existing != existing.parent:
        existing = existing.parent
    try:
        if not existing.is_dir():
            return f"'{existing}' is not a directory"
        with tempfile.TemporaryFile(dir=existing):
            pass
    except OSError as error:
        return error.strerror or str(error)
    return None


def requirements_from_document(payload: object) -> dict[str, Any]:
    """Scan document JSON for the layers that add requirements to an export."""
    found: dict[str, Any] = {
        "plugins": set(),
        "fonts": set(),
        "svg_layers": False,
        "video_layers": False,
        "background_removal": False,
        "remote_assets": False,
    }

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            kind = node.get("type")
            if kind == "plugin" and isinstance(node.get("renderer"), str):
                found["plugins"].add(node["renderer"])
            elif kind == "svg":
                found["svg_layers"] = True
            elif kind == "video":
                found["video_layers"] = True
            if node.get("remove_background") is True:
                found["background_removal"] = True
            font = node.get("font")
            if isinstance(font, str) and font:
                if font.startswith(("http://", "https://")):
                    found["remote_assets"] = True
                elif not any(sep in font for sep in "/\\") and not font.lower().endswith(
                    (".ttf", ".otf", ".ttc", ".woff", ".woff2")
                ):
                    found["fonts"].add(font)
            for value in node.values():
                if isinstance(value, str) and value.startswith(("http://", "https://")):
                    found["remote_assets"] = True
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return found
