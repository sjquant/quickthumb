"""Shared identity constraints for the plugin JSON contract."""

from __future__ import annotations

import re

PLUGIN_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]*$")
PLUGIN_VERSION_PATTERN = re.compile(r"^\S(?:.*\S)?$")
