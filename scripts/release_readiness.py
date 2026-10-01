"""Validate the checked-in v1 decision record; never infer readiness from green CI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED = {
    "static-conformance",
    "motion-conformance",
    "asset-plugin-regressions",
    "api-format-documentation",
    "dependency-baseline",
    "support-decisions",
    "changelog",
}


def evaluate(record: Any) -> list[str]:
    """Return unresolved requirements, rejecting incomplete or malformed records."""
    if not isinstance(record, dict) or record.get("target") != "1.0.0":
        raise ValueError("The release record must target 1.0.0")
    entries = record.get("requirements")
    if not isinstance(entries, list):
        raise ValueError("requirements must be a list")
    seen: set[str] = set()
    blockers: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Each requirement must be an object")
        name = entry.get("id")
        if not isinstance(name, str) or name not in REQUIRED or name in seen:
            raise ValueError(f"Unknown or duplicate requirement: {name!r}")
        seen.add(name)
        status = entry.get("status")
        if not isinstance(status, str) or status not in {"pending", "accepted"}:
            raise ValueError(f"Invalid status for {name}")
        evidence = entry.get("evidence")
        if not isinstance(evidence, str) or not evidence.strip():
            raise ValueError(f"Missing evidence or blocker explanation for {name}")
        if status != "accepted":
            blockers.append(f"{name}: {evidence}")
    if missing := REQUIRED - seen:
        raise ValueError(f"Missing requirements: {', '.join(sorted(missing))}")
    return blockers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args()
    try:
        blockers = evaluate(json.loads(args.record.read_text(encoding="utf-8")))
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Invalid release record: {exc}\n")
    print(json.dumps({"target": "1.0.0", "ready": not blockers, "blockers": blockers}, indent=2))
    return 1 if args.require_ready and blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
