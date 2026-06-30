"""Generate reference PNGs and normalized IR from the fixtures.

For each test/fixtures/*.json:
  * load it through quickthumb (Canvas.from_json) and render the ground-truth PNG
    to test/refs/<name>.png
  * write the fully-defaulted IR (Canvas.to_json) to test/normalized/<name>.json

The renderer-under-test consumes the normalized IR, so both sides see byte
identical fields and the only differences measured are rendering differences.

Run via `npm run refs` (which wraps `uv run --project ..`).
"""

from __future__ import annotations

import json
from pathlib import Path

from quickthumb.canvas import Canvas

HERE = Path(__file__).parent
FIXTURES = HERE / "fixtures"
REFS = HERE / "refs"
NORMALIZED = HERE / "normalized"


def main() -> None:
    REFS.mkdir(exist_ok=True)
    NORMALIZED.mkdir(exist_ok=True)

    fixtures = sorted(FIXTURES.glob("*.json"))
    if not fixtures:
        raise SystemExit("no fixtures found")

    for fixture in fixtures:
        name = fixture.stem
        source = fixture.read_text()
        canvas = Canvas.from_json(source)

        # Re-serialize so the JS side consumes the same defaulted IR we render.
        normalized = canvas.to_json()
        (NORMALIZED / f"{name}.json").write_text(
            json.dumps(json.loads(normalized), indent=2)
        )

        canvas.render(str(REFS / f"{name}.png"))
        print(f"  {name}: {canvas.width}x{canvas.height} -> refs/{name}.png")

    print(f"generated {len(fixtures)} references")


if __name__ == "__main__":
    main()
