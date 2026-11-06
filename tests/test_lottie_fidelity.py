"""The reference-player gate must reject empty, frozen and locally broken output."""

import json

from PIL import Image, ImageDraw
from scripts.check_lottie_fidelity import assess, prepare_cases


def test_reference_gate_checks_ink_regions_and_dimensions(tmp_path):
    reference = Image.new("RGBA", (200, 200))
    ImageDraw.Draw(reference).rectangle((40, 40, 60, 60), fill="#159A8C")
    path = tmp_path / "reference.png"
    reference.save(path)
    case = {
        "reference": str(path),
        "limits": {
            "pixel_tolerance": 32,
            "max_different_pixel_ratio": 0.08,
            "min_hash_similarity": 0.93,
        },
        "regions": [[40, 40, 61, 61]],
        "control": None,
    }
    assert assess(case, reference)["passed"]
    damaged = reference.copy()
    ImageDraw.Draw(damaged).rectangle((40, 40, 60, 60), fill="#E75A40")
    result = assess(case, damaged)
    assert result["verdict"] != "out_of_policy"  # Full-frame tolerance hides this damage.
    assert not result["passed"]
    assert not assess(case, reference.resize((100, 100)))["passed"]
    assert not assess(case, Image.new("RGBA", reference.size))["passed"]
    assert assess({**case, "control": "blank"}, Image.new("RGBA", reference.size))["passed"]
    assert not assess({**case, "control": "frozen"}, reference)["passed"]


def test_reference_fixtures_validate_and_include_integrated_motion(tmp_path):
    cases = prepare_cases(tmp_path)
    assert {case["renderer"] for case in cases} == {"svg"}
    assert {case["control"] for case in cases} == {None, "blank", "frozen"}
    payload = json.loads((tmp_path / "intro.lot").read_text())
    assert payload["assets"] == []
    assert payload["op"] == 60
    layers = {layer["nm"]: layer for layer in payload["layers"]}
    assert layers["badge"]["parent"] == layers["badge-pivot"]["ind"]
    assert layers["title"]["ty"] == 4  # Self-contained outlines, without viewer fonts.
    assert any(case["name"].startswith("intro-") and case["control"] == "frozen" for case in cases)
