# quickthumb Design

## Direction

quickthumb helps Python users create recurring thumbnails and social graphics.
The website should show compelling outputs, lead readers to a runnable recipe,
and make installation and API documentation easy to use.

Use a vivid blue homepage with a large white headline and overlapping image
examples. Keep the existing blue, ice, and navy palette. The hero examples show
people and visually rich artwork; the three episode cards appear only in the
lower reusable-layout example. Documentation uses a quieter reading layout.
On mobile, navigation opens in a white drawer from the right.

Approved previews:

- [Desktop home](design/previews/home-desktop.png)
- [Desktop getting-started guide](design/previews/guide-desktop.png)
- [Mobile home](design/previews/home-mobile.png)
- [Mobile navigation drawer](design/previews/menu-mobile.png)

These generated previews establish composition and hierarchy. Use the existing
source assets, navigation routes, and runnable code when implementing them.
The home preview contains an invented `thumbnail` API, and the guide preview
contains invented sidebar entries; neither is an implementation specification.

## Visual rules

The dimensions below are implementation starting values. Adjust within these
rules when real text, images, or responsive checks require it.

| Area | Roles and values or source | Usage rules |
| --- | --- | --- |
| Typography | Inter and JetBrains Mono, already configured in [mkdocs.yml](mkdocs.yml). Home heading: 96px/1.05, weight 800 on wide screens; 48px/1.05 on mobile. Guide title: 40px/1.15. Body: 17px/1.6; hero description: 26px desktop, 18px mobile. | Preserve the confident homepage headline. Keep navigation, prose, and code at ordinary reading sizes. Use fluid sizing between endpoints. |
| Color | Existing tokens in [extra.css](docs/stylesheets/extra.css): blue `#1F56C5`, brighter blue `#287CF4`, ice `#FBFDFF`, pale blue `#E4EEFF`, navy `#0A1730`. | Blue hero and header with white text; ice documentation and drawer with navy text. Bright colors inside output images belong to the artwork. No additional brand palette. |
| Spacing | 4, 8, 12, 16, 24, 32, 48, 64px. | Use 48px desktop and 24px mobile outer padding. Prioritize a visible primary action over decorative spacing. |
| Layout | Maximum content width 1280px. Desktop hero uses two columns: copy left, output composition right. Guide reading column approximately 720–800px. | Align header and body to the same container. Documentation gets its own sidebar and optional page outline. |
| Shape and elevation | Buttons and code strips: 8px radius. Output images: 4px radius and original aspect ratios. Fine pale-blue dividers. | Modest shadows may separate overlapping hero images. Avoid decorative containers around prose. Only hero artwork tilts; text and controls remain level. |

## Flow and components

**Home → guide → local output:** users inspect example artwork, select Get
started, copy the install command and Python example, then run the example
locally. It produces three 1280 × 720 PNGs. Environment problems lead to the
existing Installation guide. The website does not render images in-browser.

**Home → recipe:** each hero image links to its actual cookbook recipe.
Browse recipes opens the cookbook gallery.

- **Header:** existing SVG/PNG brand mark, wordmark, Recipes, Docs, GitHub,
  and documentation search. The logo returns home. Retain the existing theme
  control and search behavior through the site navigation.
- **Hero artwork:** use the original `youtube_reaction.png`,
  `youtube_talking_head.png`, and `podcast_interview_promo.png` from
  `docs/assets/examples/`. Preserve faces, text, and each image's 16:9 ratio.
  Overlap may obscure secondary artwork edges, not every face or link target.
- **Reusable example:** show `episode-12.png`, `episode-13.png`, and
  `episode-14.png` once on the home page, with code from
  [episode_cards.py](examples/episode_cards.py). Keep the original stroke
  settings and the function's real API. Do not copy generated code from images.
- **Guide:** follow [getting-started.md](docs/getting-started.md), including
  requirements, copyable code, execution instructions, and resulting files.
  Use the real navigation tree from `mkdocs.yml`.
- **Mobile drawer:** white panel from the right; target width
  `min(320px, calc(100vw - 56px))`. A dimmed strip of the current page stays
  visible to the left. Put branding and Close at the top, then search,
  a blue Get started action, Recipes, Docs, GitHub, and smaller documentation
  shortcuts: Installation, Core Concepts, API Reference. The logo supplies the
  Home link. Use fewer repeated chevrons and clear primary/secondary hierarchy.
- **Drawer behavior:** retain page position, prevent background interaction
  while open, close on X, Escape, or backdrop, and restore focus to the trigger.
  Do not focus the search input automatically on touch devices. The panel
  scrolls if viewport height or the on-screen keyboard reduces available space.
- **Search and copy:** reuse existing search results, empty-result feedback,
  and code-copy behavior. Show copied feedback only after clipboard success;
  retain selectable text when clipboard access fails.

Reuse the MkDocs Material foundations and the existing
[home override](docs/overrides/home.html) and
[main override](docs/overrides/main.html). No separate UI framework is needed
for the requested navigation and documentation screens.

## Responsive behavior and accessibility

| Viewport width | Change |
| --- | --- |
| 1280px and above | Documentation can display a left navigation tree, reading column, and right page outline. |
| Below 1280px | Hide the right page outline when needed to preserve code and prose width. |
| Below 1024px | Replace desktop navigation with search and a menu trigger; move the documentation tree into mobile navigation. Use the approved right drawer. |
| Below 768px | Stack hero copy, actions, installation command, and artwork. Show the main portrait thumbnail prominently with secondary images behind it. Stack episode examples at readable 16:9 sizes. Use 24px outer padding. |
| Below 360px | Reduce the home heading toward 40px and stack actions if needed. Keep the install command copyable without page overflow. |

At 390 × 844, the primary action appears before the hero artwork. Keep all
controls reachable without relying on artwork overlap. Code blocks may scroll
horizontally; the page itself must not overflow.

Use semantic navigation, meaningful link names, visible keyboard focus, and
at least 44 × 44px touch targets. Keep white-on-blue and navy-on-ice text
readable in both theme settings. Honor reduced motion; no animation is needed
to understand or use the menu. Static visual approval does not validate focus,
clipboard behavior, search, or keyboard/viewport resizing.

## Open decisions

- Implementation has not been requested. When authorized, verify the primary
  flows at 390px and 1440px and around the recorded breakpoints, including
  dark-mode contrast, keyboard navigation, search, and code copying.
