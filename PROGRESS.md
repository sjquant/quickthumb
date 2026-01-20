# QuickThumb TODO

**Status**: Core API complete (44/44 tests, 98% coverage) | Rendering engine missing

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

---

## 🚧 TODO

### Critical (MVP)
- [ ] Implement rendering engine
  - [ ] PNG output with Pillow/PIL
  - [ ] Solid color background rendering
  - [ ] Basic text rendering (without stroke)
  - [ ] Alpha compositing

### High Priority
- [ ] Gradient rendering (linear + radial)
- [ ] Text stroke rendering
- [ ] Blend mode compositing (6 modes)
- [ ] Image background rendering
- [ ] Outline decoration rendering

### Medium Priority
- [ ] JPEG/WebP output formats
- [ ] Quality parameter for render
- [ ] Font loading and caching
- [ ] Image fit modes (cover, contain, fill)
- [ ] Image brightness adjustment

### Low Priority
- [ ] Text word wrapping (`max_width` parameter)
- [ ] Performance optimizations
- [ ] Extended documentation/examples
