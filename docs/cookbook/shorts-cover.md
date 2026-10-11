---
description: A 1080×1920 Shorts cover rendered from a JSON spec with quickthumb, shown with the exact spec that produced it.
---

# Shorts / Vertical Cover

![Vertical cover reading "Turn long videos into Shorts" with a tilted phone showing a cropped photo](../assets/examples/shorts_cover_agent.png)

A 1080×1920 cover where the whole design is a JSON file. The Python side only
loads it and renders it, which is how you would use quickthumb when an LLM or
a template system writes the layout.

```bash
git clone https://github.com/sjquant/quickthumb
cd quickthumb
uv run python examples/shorts_cover_agent.py
```

## How it's built

- **One photo, used twice.** The same image appears as a wide 16:9 crop and
  inside the phone. `"fit": "cover"` crops it to each frame's shape.
- **The phone is two layers.** A dark rounded rectangle is the body and the
  photo on top is the screen. Both have `"rotation": 3`, as do the three
  labels on the screen, so they tilt together.
- **Paths are relative to the repository root**, such as
  `assets/images/denise-jans-WIRvXd1PYlg-unsplash.jpg`. The script changes
  into the repository root before rendering, so it runs from any directory.
- **The background has a little grain.** A `grain` effect with a fixed `seed`
  gives the same texture on every render.

## The spec

```json
--8<-- "examples/shorts_cover_agent.json"
```

## The script

```python
--8<-- "examples/shorts_cover_agent.py"
```

`Canvas.from_json()` validates the spec before drawing anything, so a
malformed spec raises a `ValidationError` that points at the bad field. See
[JSON Schema & AI Workflow](../json-schema.md) for every field the spec can
use.
