"""
JSON-first vertical cover example.

This script simulates the workflow where an AI agent emits a QuickThumb JSON spec
and the application renders it with `Canvas.from_json(...)`.
"""

import os

from quickthumb import Canvas

FILE_DIR = os.path.dirname(__file__)
REPO_DIR = os.path.abspath(os.path.join(FILE_DIR, ".."))
SPEC_PATH = os.path.join(FILE_DIR, "shorts_cover_agent.json")
OUTPUT_PATH = os.path.join(FILE_DIR, "shorts_cover_agent.png")

os.environ["QUICKTHUMB_FONT_DIR"] = os.path.join(REPO_DIR, "assets", "fonts")
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

with open(SPEC_PATH, encoding="utf-8") as f:
    json_spec = f.read()

previous_cwd = os.getcwd()

try:
    # The checked-in JSON spec uses repo-relative asset paths to stay easy to read.
    os.chdir(REPO_DIR)
    Canvas.from_json(json_spec).render(OUTPUT_PATH)
finally:
    os.chdir(previous_cwd)

print(f"✓ JSON-first Shorts cover created: {OUTPUT_PATH}")
print(f"  Spec source: {SPEC_PATH}")
