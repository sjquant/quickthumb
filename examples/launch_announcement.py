"""
JSON-first launch announcement card.

Exercises the quickthumb 0.5 feature set in a single themed spec:
- A top-level `theme` block with `$theme.*` token references across layers
- Auto-layout `group` layers (a column with a nested chip row) — no hand-placed
  coordinates for any text
- `star` shape primitives and decorative `svg` layers
- Film grain on the base background
- `canvas.diagnose()` before rendering, mirroring `quickthumb lint`
"""

import os

from quickthumb import Canvas

FILE_DIR = os.path.dirname(__file__)
REPO_DIR = os.path.abspath(os.path.join(FILE_DIR, ".."))
SPEC_PATH = os.path.join(FILE_DIR, "launch_announcement.json")
OUTPUT_PATH = os.path.join(FILE_DIR, "launch_announcement.png")

os.environ["QUICKTHUMB_FONT_DIR"] = os.path.join(REPO_DIR, "assets", "fonts")
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

with open(SPEC_PATH, encoding="utf-8") as f:
    json_spec = f.read()

previous_cwd = os.getcwd()

try:
    # The checked-in JSON spec uses repo-relative asset paths to stay easy to read.
    os.chdir(REPO_DIR)
    canvas = Canvas.from_json(json_spec)

    findings = canvas.diagnose()
    for finding in findings:
        print(
            f"[{finding.severity}] layer {finding.layer_index}: {finding.code} — {finding.message}"
        )
    if not findings:
        print("✓ diagnose(): no layout or legibility issues")

    canvas.render(OUTPUT_PATH)
finally:
    os.chdir(previous_cwd)

print(f"✓ Launch announcement card created: {OUTPUT_PATH}")
print(f"  Spec source: {SPEC_PATH}")
