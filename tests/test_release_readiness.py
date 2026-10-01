"""The release decision fails closed when evidence is missing."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from scripts.release_readiness import REQUIRED, evaluate

ROOT = Path(__file__).resolve().parents[1]


def record(status="accepted"):
    return {
        "target": "1.0.0",
        "requirements": [
            {"id": name, "status": status, "evidence": "Reviewed fixture result"}
            for name in sorted(REQUIRED)
        ],
    }


def test_accepted_evidence_is_ready():
    assert evaluate(record()) == []


def test_pending_evidence_is_not_ready():
    assert len(evaluate(record("pending"))) == len(REQUIRED)


@pytest.mark.parametrize("bad", [None, {}, {"target": "2.0.0"}, {"target": "1.0.0"}])
def test_invalid_record_is_rejected(bad):
    with pytest.raises(ValueError):
        evaluate(bad)


@pytest.mark.parametrize("change", ["missing", "duplicate", "unknown", "status", "evidence"])
def test_incomplete_or_invalid_requirement_is_rejected(change):
    data = record()
    entries = data["requirements"]
    if change == "missing":
        entries.pop()
    elif change == "duplicate":
        entries.append(entries[0])
    elif change == "unknown":
        entries[0]["id"] = "unrecognized"
    elif change == "status":
        entries[0]["status"] = "skipped"
    else:
        entries[0]["evidence"] = " "
    with pytest.raises(ValueError):
        evaluate(data)


def test_checked_in_record_reports_blockers_but_cannot_approve_v1(tmp_path):
    # Exercise a known blocked fixture, not the evolving project's release decision.
    path = tmp_path / "record.json"
    path.write_text(json.dumps(record("pending")))
    command = [sys.executable, str(ROOT / "scripts/release_readiness.py"), str(path)]
    informational = subprocess.run(command, capture_output=True, text=True, check=False)
    required = subprocess.run(
        [*command, "--require-ready"], capture_output=True, text=True, check=False
    )
    assert informational.returncode == 0
    assert json.loads(informational.stdout)["ready"] is False
    assert required.returncode == 1


def test_actual_release_record_has_complete_requirements():
    evaluate(json.loads((ROOT / "release-readiness.json").read_text()))
