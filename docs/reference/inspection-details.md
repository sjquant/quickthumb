---
description: Detailed inspection behavior for parent-linked scenes and complex layouts.
---

# Inspecting complex layouts

For the basic API, see [Canvas inspection](../api/canvas.md#inspect).

For supported parent-linked scenes, bounds describe the **authored-static** world
layout, not the state at animation time zero. They conservatively enclose each
existing measured local body after its ancestor transforms and can extend outside
the canvas. Transparent corners can make these boxes looser than painted pixels.
Text sizes/wrapping remain authored-local; intrinsic counters use their settled
formatted text for these measurements, without sampling the timeline. Nulls have
no visible body or bbox.
`canvas.render("debug.png", debug=True)` overlays the same authored-static boxes.
`diagnose()` uses the same authored-static world layout, with transformed painted
alpha for overlap/occlusion and transformed glyph/background pixels for contrast.
Parent opacity is not inherited. Geometry animation on an ancestor prevents a
static footprint from being reported as permanently hiding another layer.
Repair suggestions describe parent-local positions or containing group layout;
world coordinates must not be copied directly into those local fields.
A top-level group's own clip/mask restricts its complete painted source,
including sampled counters in settled group slots.
Inspection reports the boundary-intersected group box and keeps conservative
laid-out child boxes. Each layer or group box intersects only its own finite
boundary before applying world transforms; enclosing group boundaries do not
cut descendant inspection boxes. Static leaves and nested
structural groups can have their own clips and masks at several depths, using
the top-level group's shared parent-local plane and original canvas dimensions
for percentages. Inverted masks retain conservative boxes around their cutouts.
Child transforms still use the full authored group body;
the boundary does not clip independently linked children. Counter observations
use settled text, including glyph backgrounds and preceding group content.
Groups with descendant boundaries support `plain`, `odometer` and `flip` text
counters in settled layout slots. Each counter's fragments are combined before
its own boundary, and each nested group's children before that group's boundary;
changing counter paint does not move siblings, pivots or independently linked
children. Other intrinsic dynamic sources and authored stagger on any structural
descendant remain guarded. The participating top-level group's own
animation may override other authored descendant animations; an external
ancestor's animation or only an inner group's animation does not qualify.
Static inspection and diagnostics retain the authored layout and composition;
HTML, SVG, PDF and PPTX retain whole-scene authored-static fallback for overridden
descendant motion. Intrinsic counter clocks continue through that override;
counter-group stagger remains guarded. Static graph-leaf groups with their own
or descendant clip/mask boundaries can use root stagger through the existing
partial horizontal-band adapter; it does not establish which child owns a band. See
[parent adapter boundaries](../api/video.md#current-adapters-and-boundaries).
