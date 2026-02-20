# QuickThumb TODO

## ✅ Completed

### Core API & Models

- ✅ Canvas creation (explicit dimensions, aspect ratios)
- ✅ Background layers (solid colors, linear/radial gradients, images, blend modes, opacity, brightness adjustment)
- ✅ Text layers (fonts, positioning, alignment, bold/italic, letter spacing, line height, word wrapping, auto-scale)
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
- ✅ Rotation support for text layers (simple and rich text)

### Font System

- ✅ CSS-style `font-weight` support (100-900 numeric, "thin"/"bold"/"black" named)
- ✅ Automatic font file mapping with fallback to closest weight
- ✅ WebFont support (load from URLs, cached to /tmp)

### Image Layers

- ✅ Image overlay with position (pixels/percentages), sizing (aspect ratio preserved), opacity, rotation, and alignment
- ✅ URL and local path support, JSON serialization, method chaining
- ✅ Background removal for image layers via `remove_background=True` (requires `quickthumb[rembg]`)

---

## 🚧 TODO

### High Priority

- ✅ Shape layers — Rectangle and ellipse primitives with fill color, stroke, border radius, opacity, rotation, and alignment. API: `canvas.shape(shape="rectangle", position=(x, y), width=300, height=200, color="#FF5733", stroke_color="#000000", stroke_width=2, border_radius=10)`
- ✅ Blur/filter effects on background layers — `blur` (Gaussian blur radius), `contrast`, and `saturation` adjustments. API: `canvas.background(image="...", blur=10, contrast=1.2, saturation=0.8)`

### Medium Priority

- [ ] Rounded corners on image layers — Clip image to rounded rectangle mask. API: `canvas.image(..., border_radius=20)`
- [ ] Drop shadow on image layers — Cast shadow from image alpha shape. API: `canvas.image(..., shadow=Shadow(offset_x=5, offset_y=5, color="#000000", blur_radius=10))`

### Low Priority

- [ ] Custom layer hook — Let users inject arbitrary Pillow drawing logic as a layer. API: `canvas.custom(fn)` where `fn` receives the `PIL.Image.Image` and draws onto it directly, e.g. `canvas.custom(lambda img: ImageDraw.Draw(img).polygon([...], fill="#FF0000"))`
- [ ] Extended documentation/examples
