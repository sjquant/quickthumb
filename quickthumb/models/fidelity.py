"""Fidelity policy and comparison results for canonical-sample checks."""

from typing import Annotated, Literal, cast, get_args

from pydantic import ConfigDict, Field, NonNegativeInt

from quickthumb.errors import InputError

from .common import quickthumbModel

FidelityFormat = Literal["png", "jpg", "webp", "svg", "pdf", "html", "pptx", "gif", "mp4", "webm"]
FidelityCriterion = Literal[
    "dimensions", "different_pixel_ratio", "mean_absolute_error", "hash_similarity"
]
_UnitFloat = Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]

_FORMAT_ALIASES = {"jpeg": "jpg"}


class FidelityTolerance(quickthumbModel):
    """Limits an output may reach and still count as a faithful rendering.

    A pixel counts as different when any of its R, G, B, or A channels differs
    from the canonical sample by more than `pixel_tolerance`. The output stays
    within policy while the share of different pixels is at most
    `max_different_pixel_ratio`, the average-hash similarity is at least
    `min_hash_similarity`, and, when set, the normalized mean channel error is
    at most `max_mean_absolute_error`.
    """

    model_config = ConfigDict(extra="forbid")

    pixel_tolerance: Annotated[int, Field(ge=0, le=255)] = 2
    max_different_pixel_ratio: _UnitFloat = 0.0
    min_hash_similarity: _UnitFloat = 0.95
    max_mean_absolute_error: _UnitFloat | None = None


class FidelityPolicy(quickthumbModel):
    """Format-aware fidelity expectations, independent of the sample format.

    `default` applies to every output; `formats` overrides it for specific
    export formats (for example looser limits for browser-rendered SVG or
    lossy JPEG) without changing the canonical sample being compared against.
    """

    model_config = ConfigDict(extra="forbid")

    version: Literal["1"] = "1"
    default: FidelityTolerance = Field(default_factory=FidelityTolerance)
    formats: dict[FidelityFormat, FidelityTolerance] = Field(default_factory=dict)

    def tolerance_for(self, output_format: str | None = None) -> FidelityTolerance:
        """Return the tolerance that applies to `output_format`.

        Raises `InputError` for a format the policy cannot describe, so a
        misspelled format never falls back to the default tolerance silently.
        """
        if output_format is None:
            return self.default
        key = _normalize_output_format(output_format)
        return self.formats.get(key, self.default)


def _normalize_output_format(output_format: str) -> FidelityFormat:
    """Normalize a format name or file suffix such as `.JPEG` to `jpg`."""
    key = output_format.strip().lower().lstrip(".")
    key = _FORMAT_ALIASES.get(key, key)
    supported = get_args(FidelityFormat)
    if key not in supported:
        raise InputError(
            f"unsupported output format '{output_format}' for fidelity comparison",
            code="unsupported_output_format",
            suggestion=f"use one of: {', '.join(supported)}",
        )
    return cast(FidelityFormat, key)


class FidelityMeasurements(quickthumbModel):
    """Pixel and perceptual measurements of an output against its sample.

    Pixel measurements compare straight RGBA channels, treating every fully
    transparent pixel as transparent black so hidden color does not count.
    They are `None` when the dimensions differ. `mean_absolute_error` is the
    mean channel delta divided by 255. The hashes are average hashes of each
    image composited onto white, and `hash_similarity` is the share of
    matching hash bits.
    """

    model_config = ConfigDict(extra="forbid")

    expected_size: tuple[int, int]
    actual_size: tuple[int, int]
    pixel_count: NonNegativeInt | None = None
    different_pixels: NonNegativeInt | None = None
    different_pixel_ratio: float | None = None
    mean_absolute_error: float | None = None
    max_channel_delta: Annotated[int, Field(ge=0, le=255)] | None = None
    expected_hash: str
    actual_hash: str
    hash_distance: NonNegativeInt
    hash_similarity: float


class FidelityViolation(quickthumbModel):
    """One policy criterion that the output failed."""

    model_config = ConfigDict(extra="forbid")

    criterion: FidelityCriterion
    measured: float | tuple[int, int]
    limit: float | tuple[int, int]
    message: str


class FidelityComparison(quickthumbModel):
    """Verdict of comparing an output against a canonical sample under a policy.

    `verdict` is `exact` when every visible RGBA channel matches, `tolerated`
    when the output differs but satisfies the tolerance, and `out_of_policy`
    when any criterion in `violations` fails.
    """

    model_config = ConfigDict(extra="forbid")

    version: Literal["1"] = "1"
    output_format: str | None = None
    verdict: Literal["exact", "tolerated", "out_of_policy"]
    tolerance: FidelityTolerance
    measurements: FidelityMeasurements
    violations: list[FidelityViolation] = Field(default_factory=list)

    @property
    def within_policy(self) -> bool:
        """Whether the output is acceptable under the applied tolerance."""
        return self.verdict != "out_of_policy"
