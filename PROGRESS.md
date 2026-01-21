# QuickThumb TODO

**Status**: Core rendering complete (53/53 tests, 94% coverage)

---

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
- ✅ Text rendering (bold, italic, unicode, emojis)
- ✅ Text alignment (horizontal: left/center/right, vertical: top/middle/bottom)
- ✅ Text positioning with percentages (e.g., position=("50%", "50%"))
- ✅ Alpha compositing with opacity
- ✅ System font loading (Arial on macOS, DejaVu on Linux)
- ✅ Error handling (RenderingError for unsupported formats)

---

## 🚧 TODO

### High Priority
- [ ] Gradient rendering (linear + radial)
- [ ] Text stroke rendering
- [ ] Blend mode compositing (multiply, overlay)
- [ ] Image background rendering
- [ ] Outline decoration rendering

### Medium Priority
- [ ] Font loading and caching
- [ ] Image fit modes (cover, contain, fill)
- [ ] Image brightness adjustment

### Low Priority
- [ ] Text word wrapping (`max_width` parameter)
- [ ] Performance optimizations
- [ ] Extended documentation/examples
