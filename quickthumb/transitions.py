"""Slide transitions for PowerPoint (PPTX), HTML, and animated GIF/MP4/WebM export.

In PPTX they map to native PowerPoint transitions; in the HTML slideshow they
animate the change into each slide (the incoming stage), with effects that need
to move the stage composed with the responsive fit-to-viewport scale. A few
exotic effects (wheel, wedge, checker, comb, dissolve) fall back to the closest
CSS analogue there. Animated GIF/MP4/WebM export renders every effect as real
raster frames (``random`` plays as a cross-fade -- there is no viewer to
randomize per playback). Still renderers (raster, SVG, PDF) ignore transitions.

Each transition effect is its own class so it only exposes the options that
effect actually supports — directional effects (``Push``, ``Wipe``, ``Cover``,
``Uncover``, ``Zoom``) take a ``direction``; ``Split`` and the blind-style
effects take an ``orientation``; ``Wheel`` takes ``spokes``; the rest take
nothing. Every effect shares the timing fields ``duration``,
``advance_on_click``, and ``advance_after``.

Transitions live in this namespace (``quickthumb.transitions``) because several
effect names — ``Fade``, ``Wipe``, ``Wheel``, … — also exist as layer
animations (``quickthumb.Fade`` and friends), which are a different thing.

    from quickthumb import Deck
    from quickthumb.transitions import Fade, Push

    Deck(1280, 720).transition(Fade()).slide(cover, transition=Push(direction="left"))
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    Discriminator,
    Field,
    NonNegativeFloat,
    PositiveFloat,
    PositiveInt,
    TypeAdapter,
)
from pydantic import ValidationError as PydanticValidationError

from quickthumb.errors import ValidationError
from quickthumb.models import quickthumbModel


class _TransitionBase(quickthumbModel):
    """Shared timing fields for every slide transition."""

    duration: PositiveFloat = 1.0
    advance_on_click: bool = True
    advance_after: NonNegativeFloat | None = None


class Cut(_TransitionBase):
    """Hard cut straight to the slide (no animation)."""

    effect: Literal["cut"] = "cut"


class Fade(_TransitionBase):
    """Cross-fade into the slide."""

    effect: Literal["fade"] = "fade"


class Morph(_TransitionBase):
    """Move uniquely keyed layers between adjacent scenes."""

    effect: Literal["morph"] = "morph"


class Dissolve(_TransitionBase):
    """Dissolve into the slide through a speckled mask."""

    effect: Literal["dissolve"] = "dissolve"


class Newsflash(_TransitionBase):
    """Spin the slide in like a newsreel flash."""

    effect: Literal["newsflash"] = "newsflash"


class Wedge(_TransitionBase):
    """Sweep the slide in with two clock hands."""

    effect: Literal["wedge"] = "wedge"


class Circle(_TransitionBase):
    """Reveal the slide through an expanding circle."""

    effect: Literal["circle"] = "circle"


class Diamond(_TransitionBase):
    """Reveal the slide through an expanding diamond."""

    effect: Literal["diamond"] = "diamond"


class Random(_TransitionBase):
    """Let PowerPoint pick a random transition."""

    effect: Literal["random"] = "random"


class Wheel(_TransitionBase):
    """Sweep the slide in like a clock hand, using ``spokes`` arms."""

    effect: Literal["wheel"] = "wheel"
    spokes: Annotated[PositiveInt, Field(le=64)] = 1


class Push(_TransitionBase):
    """Push the previous slide out while the new one slides in."""

    effect: Literal["push"] = "push"
    direction: Literal["left", "right", "up", "down"] = "left"


class Wipe(_TransitionBase):
    """Wipe the slide in from one edge."""

    effect: Literal["wipe"] = "wipe"
    direction: Literal["left", "right", "up", "down"] = "up"


class Cover(_TransitionBase):
    """Slide the new slide in over the previous one."""

    effect: Literal["cover"] = "cover"
    direction: Literal["left", "right", "up", "down"] = "down"


class Uncover(_TransitionBase):
    """Slide the previous slide away to reveal the new one."""

    effect: Literal["uncover"] = "uncover"
    direction: Literal["left", "right", "up", "down"] = "down"


class Zoom(_TransitionBase):
    """Zoom the slide in or out."""

    effect: Literal["zoom"] = "zoom"
    direction: Literal["in", "out"] = "in"


class Split(_TransitionBase):
    """Split the slide open or closed along an axis."""

    effect: Literal["split"] = "split"
    orientation: Literal["horizontal", "vertical"] = "horizontal"
    direction: Literal["in", "out"] = "out"


class Blinds(_TransitionBase):
    """Reveal the slide through horizontal or vertical blinds."""

    effect: Literal["blinds"] = "blinds"
    orientation: Literal["horizontal", "vertical"] = "horizontal"


class Checker(_TransitionBase):
    """Reveal the slide through a sweeping checkerboard."""

    effect: Literal["checker"] = "checker"
    orientation: Literal["horizontal", "vertical"] = "horizontal"


class Comb(_TransitionBase):
    """Reveal the slide through interleaving comb strips."""

    effect: Literal["comb"] = "comb"
    orientation: Literal["horizontal", "vertical"] = "horizontal"


# Discriminated union of every transition: validates a dict (e.g. from JSON) into
# the right class by its ``effect`` tag.
Transition = Annotated[
    Cut
    | Fade
    | Morph
    | Dissolve
    | Newsflash
    | Wedge
    | Circle
    | Diamond
    | Random
    | Wheel
    | Push
    | Wipe
    | Cover
    | Uncover
    | Zoom
    | Split
    | Blinds
    | Checker
    | Comb,
    Discriminator("effect"),
]

_EFFECT_CLASSES = (
    Cut, Fade, Morph, Dissolve, Newsflash, Wedge, Circle, Diamond, Random, Wheel,
    Push, Wipe, Cover, Uncover, Zoom, Split, Blinds, Checker, Comb,
)  # fmt: skip
_EFFECT_NAMES = ", ".join(cls.model_fields["effect"].default for cls in _EFFECT_CLASSES)
_ADAPTER = TypeAdapter(Transition)


def coerce_transition(value: Transition | dict | str | None) -> Transition | None:
    """Normalise a transition given as a model, a dict, an effect string, or None."""
    if value is None:
        return None
    # An effect string is shorthand for that effect with default options.
    payload = {"effect": value} if isinstance(value, str) else value
    try:
        return _ADAPTER.validate_python(payload)
    except PydanticValidationError as e:
        # A bad/missing effect tag (or a non-mapping value) fails at the union
        # level, which pydantic reports with an opaque tagged-union message;
        # surface a clean quickthumb error instead. Per-effect field errors
        # already raise quickthumbModel's formatted ValidationError.
        raise ValidationError(
            f"Invalid transition {value!r}: pass a transitions effect object, a dict "
            f"with a valid 'effect', or one of these effect names: {_EFFECT_NAMES}."
        ) from e
