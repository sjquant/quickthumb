---
description: Inspection behavior and bounding box measurements for parent-linked scenes and complex layouts.
---

# Inspecting complex layouts

For the standard inspection API, see [Canvas inspection](../api/canvas.md#inspect) and [Document inspection](../api/inspection.md).

## Parent-linked scenes

When inspecting parent-linked hierarchies or running `canvas.diagnose()`:

- **Authored-static bounds**: Layer bounding boxes describe their static layout coordinates in world space.
- **Null controllers**: Null controller layers (`Canvas.null()`) act as invisible transformation points and do not produce visual bounding boxes.
- **Visual debug overlay**: Use `canvas.render("debug.png", debug=True)` to visualize the exact bounding boxes measured for each layer.

## Groups and clipped boundaries

- **Group bounding boxes**: A group's measured bounding box encloses all of its children, accounting for gaps, padding, and any attached clips or masks.
- **Nested clips and masks**: Clips and masks applied to parent groups or descendant layers constrain their visible area without altering relative layout coordinates.
- **Animated counters**: Intrinsic counter text layers (`Canvas.counter()`) calculate bounding boxes based on their settled final value, ensuring layout stability throughout playback.
