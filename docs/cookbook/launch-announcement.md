---
description: A 1280×720 release card rendered from a themed JSON spec with auto-layout groups, shown with the exact spec that produced it.
---

# Launch Announcement (Auto Layout)

![Release card reading "Layouts that build themselves." with a blue circle on the right](../assets/examples/launch_announcement.png)

A release card whose text has no hand-placed coordinates. The headline column
and the feature row are auto-layout groups, and every color and font size
comes from a `theme` block, so changing the copy or the brand doesn't mean
re-measuring anything.

```bash
git clone https://github.com/sjquant/quickthumb
cd quickthumb
uv run --extra svg python examples/launch_announcement.py
```

The `svg` extra is needed for the sparkle, which is an SVG file.

## How it's built

- **Theme tokens.** Colors and sizes are defined once under `theme` and used
  as `"$theme.colors.blue"` or `"$theme.sizes.title"`. A token that is the
  whole value keeps its JSON type, so `"$theme.sizes.title"` becomes the
  number `116`, not a string.
- **A column group for the text.** The release label, headline, and subtitle
  are children of one `group` with `"direction": "column"` and `"gap": 22`.
  The group is placed once, at `["7%", "44%"]`; the children have no
  `position`. Add a line to the subtitle and the column re-flows around it.
- **A row group for the features.** "01 GROUPS" through "04 DIAGNOSTICS" are a
  second group with `"direction": "row"`, so the spacing between them stays
  even when you rename one.
- **Simple shapes for the art.** The circle, the four bars, and the star are
  ordinary `ellipse`, `rectangle`, and `star` shapes. The sparkle is
  `assets/images/spark.svg`, turned white with
  `Filter(saturation=0, brightness=3)`.
- **Checked before rendering.** The script calls `canvas.diagnose()` and
  prints any findings before it renders. The same check is available from the
  terminal as `quickthumb lint examples/launch_announcement.json`.

## The spec

```json
--8<-- "examples/launch_announcement.json"
```

## The script

```python
--8<-- "examples/launch_announcement.py"
```
