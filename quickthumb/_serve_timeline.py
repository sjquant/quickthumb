"""Bounded, reloadable canonical timeline previews for the local authoring server."""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING, cast

from quickthumb._document import Document, _contract_timeline_inputs
from quickthumb._export_video import (
    TimelineSampler,
    _canvas_has_video_captions,
    _close_video_decoders,
)
from quickthumb.errors import ValidationError

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas
    from quickthumb.deck import Deck

PROXY_MAX_EDGE = 640
HOLD = 3.0
MATTE = "#000000"


class StaleTimelineError(Exception):
    """The request refers to a source version that is no longer current."""


class TimelinePreview:
    """Own at most two reusable samplers; the source serializes every operation."""

    def __init__(self, document: Canvas | Deck):
        document._contract_validate_structure()
        self._canvases, self._transitions, self._durations = _contract_timeline_inputs(
            cast(Document, document), HOLD
        )
        first = self._canvases[0]
        self.width, self.height = first.width, first.height
        self._scale = min(1.0, PROXY_MAX_EDGE / max(self.width, self.height))
        self._samplers: dict[str, TimelineSampler] = {}

    def _sampler(self, resolution: str) -> TimelineSampler:
        if resolution not in {"proxy", "full"}:
            raise ValidationError("resolution must be proxy or full")
        key = resolution
        if key not in self._samplers:
            self._samplers[key] = TimelineSampler(
                self._canvases,
                self._transitions,
                slide_duration=HOLD,
                slide_durations=self._durations,
                matte=MATTE,
                preview_max_edge=PROXY_MAX_EDGE if key == "proxy" else None,
            )
        return self._samplers[key]

    def metadata(self, version: str) -> dict:
        sampler = self._sampler("proxy")
        warnings = [
            "Proxy pixels approximate standard-quality export; use Full for canonical pixels.",
            "Audio is not played. Export frame grids and lossy encoding "
            "can change playback samples.",
        ]
        if any(_canvas_has_video_captions(canvas) for canvas in self._canvases):
            warnings.append("Slides with video captions render at native size before reduction.")
        if any(transition and transition.effect == "morph" for transition in self._transitions):
            warnings.append("Keyed Morph transitions render at native size before reduction.")
        return {
            "version": version,
            "duration": round(sampler.duration, 9),
            "width": self.width,
            "height": self.height,
            "proxy_width": max(1, round(self.width * self._scale)),
            "proxy_height": max(1, round(self.height * self._scale)),
            "hold": HOLD,
            "matte": MATTE,
            "segments": [
                dict(
                    zip(
                        ("slide", "start", "transition_end", "animation_end", "end"),
                        (index, *(round(value, 9) for value in segment)),
                        strict=True,
                    )
                )
                for index, segment in enumerate(sampler.segments())
            ],
            "warnings": warnings,
        }

    def frame(self, time: float, resolution: str) -> tuple[bytes, int, float]:
        sampler = self._sampler(resolution)
        instant = min(time, sampler.duration)
        slide, frame = sampler.frame_at(instant)
        output = BytesIO()
        frame.save(output, format="PNG", compress_level=1)
        return output.getvalue(), slide, instant

    def close(self) -> None:
        # Both plans share the source's canvases and decoder ownership. They are
        # only closed together while the source lock is held, never per request.
        _close_video_decoders(self._canvases)
        self._samplers.clear()
