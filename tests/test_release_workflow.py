"""Keep publication tied to the candidate that passed the release gate."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_publication_requires_gate_and_tags_verified_commit():
    workflow = yaml.safe_load((ROOT / ".github/workflows/publish.yaml").read_text())
    assert workflow["jobs"]["gate"]["uses"] == "./.github/workflows/release-gate.yml"
    publish = workflow["jobs"]["publish"]
    assert publish["needs"] == "gate"
    release = next(
        step
        for step in publish["steps"]
        if step.get("uses", "").startswith("softprops/action-gh-release@")
    )
    assert release["with"]["target_commitish"] == "${{ github.sha }}"
