# QuickThumb TODO

## ✅ Completed

### Core API & Models

- ✅ Canvas creation (explicit dimensions, aspect ratios)
- ✅ Background layers (solid colors, linear/radial gradients, images, blend modes, opacity, brightness adjustment)
- ✅ Text layers (fonts, positioning, alignment, bold/italic, letter spacing, line height, word wrapping)
- ✅ Outline decoration layer
- ✅ JSON serialization/deserialization
- ✅ Method chaining API

### Rendering Engine

- ✅ Output formats: PNG, JPEG, WebP (with quality parameter)
- ✅ Gradients: Linear (angle-based, multi-stop) and Radial (configurable center)
- ✅ Image backgrounds (URL support, fit modes: cover/contain/fill)
- ✅ Blend modes: MULTIPLY, OVERLAY, SCREEN, DARKEN, LIGHTEN, NORMAL
- ✅ Text positioning with percentages (e.g., `position=("50%", "50%")`)
- ✅ Base64 encoding and data URL generation

### Text Effects

- ✅ Stroke, Shadow (with blur), Glow (outer glow), Background (with padding and border radius)
- ✅ Rich text with `TextPart` (per-segment styling)

### Font System

- ✅ CSS-style `font-weight` support (100-900 numeric, "thin"/"bold"/"black" named)
- ✅ Automatic font file mapping with fallback to closest weight
- ✅ WebFont support (load from URLs, cached to /tmp)

### Text Alignment

- ✅ `TextAlign` enum (9 values: CENTER, TOP_LEFT, etc.)
- ✅ Accepts enum, string shortcuts (`"center"`, `"top-left"`), or tuples (`("center", "middle")`)

### Auto-scaling

- ✅ Auto-scale text to fit within `max_width` (simple text and rich text with proportional scaling)

---

## 🚧 TODO

### Planned Features (High Priority)

- [ ] Image Layer (placing images at specific coordinates)
- [ ] Rotation support for images and texts

### Medium Priority

### Low Priority

- [ ] Extended documentation/examples
- [ ] Background Removal for image
