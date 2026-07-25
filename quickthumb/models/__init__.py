"""Public model compatibility surface.

The concrete model definitions remain in the private migration module while the
domain modules expose stable, discoverable import paths. Existing imports such
as ``quickthumb.models.TextLayer`` continue to resolve unchanged.
"""

from . import _legacy as _legacy
from ._legacy import *  # noqa: F401,F403

__all__ = [name for name in vars(_legacy) if not name.startswith("_")]
