# QuickThumb TODO

## ✅ Completed

### Core API & Models

- ✅ Canvas creation (explicit dimensions, aspect ratios)
- ✅ Background layers (solid colors, linear/radial gradients, images, blend modes, opacity)
- ✅ Text layers (content, fonts, stroke, positioning, alignment, bold/italic)
- ✅ Outline decoration layer
- ✅ JSON serialization/deserialization (perfect round-trip)
- ✅ Pydantic validation with custom error handling
- ✅ Method chaining API

### Rendering Engine

- ✅ PNG output with Pillow/PIL
- ✅ JPEG output (with quality parameter)
- ✅ WebP output (with quality parameter)
- ✅ Solid color background rendering
- ✅ Linear gradient rendering (angle-based with multi-stop color interpolation)
- ✅ Radial gradient rendering (centered with configurable center point)
- ✅ Image background rendering (auto-resize to canvas dimensions)
- ✅ Blend mode compositing (multiply for darkening, overlay for contrast)
- ✅ Text rendering (bold, italic, unicode, emojis)
- ✅ Text alignment (horizontal: left/center/right, vertical: top/middle/bottom)
- ✅ Text positioning with percentages (e.g., position=("50%", "50%"))
- ✅ Outline decoration rendering (border with width and offset support)
- ✅ Alpha compositing with opacity
- ✅ System font loading (Arial on macOS, DejaVu on Linux)
- ✅ Error handling (RenderingError for unsupported formats)
- ✅ Add missing blend modes (SCREEN, DARKEN, LIGHTEN, NORMAL)
- ✅ Image fit modes (cover, contain, fill)
- ✅ Font loading and caching
- ✅ Brightness adjustment (for solid colors, gradients, and images)
- ✅ Text word wrapping (max_width parameter with alignment preservation)
- ✅ URL support for images (backgrounds with http/https URLs)
- ✅ WebFont support (load fonts from http/https URLs, cached to /tmp)
- ✅ WebFont bold/italic warning (user warning when bold/italic used with webfonts)

### Text Effects

- ✅ Effect classes API (extensible effects list with Stroke, Shadow, Glow)
- ✅ Text stroke rendering (configurable width and color)
- ✅ Drop shadow (offset_x, offset_y, color, blur_radius)
- ✅ Glow/outer glow (color, radius, opacity)
- ✅ Letter spacing (`letter_spacing` parameter)
- ✅ Line height (`line_height` parameter)
- ✅ Rich text with `TextPart` (partial text styling: color, effects per segment)

### Font System

- ✅ Smart Font Loading with CSS-style `font-weight` support (numeric 100-900 and named weights like "thin", "bold", "black")
- ✅ Automatic font weight mapping to font file variants (e.g., weight=700 → Roboto-Bold.ttf)
- ✅ Font weight fallback mechanism (finds closest available weight when exact match unavailable)
- ✅ Mutual exclusivity validation (`weight` and `bold` parameters cannot be used together)

### Bug Fixes

- ✅ Fix inability to load non-system fonts by family name

---

## 🚧 TODO

### Planned Features (High Priority)

- [ ] Auto-scale Text and TextPart to fit within max-width
- [ ] Introduce a LineBreak object to insert vertical spacing between TextParts
- [ ] Image Layer (placing images at specific coordinates)
- [ ] Rotation support for images and texts
- [ ] Text background effect support (labels/badges with padding/rounded corners)
- [ ] Implement `to_base64` and `to_data_url`

### Medium Priorty

- [ ] Support enum and shortcut string for text align

### Low Priority

- [ ] Extended documentation/examples
- [ ] Background Removal for image
