---
description: Review quickthumb release notes and follow version changes, fixes, and new features through GitHub Releases.
---

# Changelog

Release notes are published on GitHub Releases:

[View all releases on GitHub](https://github.com/sjquant/quickthumb/releases){ .md-button .md-button--primary }

## Unreleased

- Text using `QUICKTHUMB_DEFAULT_FONT` now honors `weight`, `bold`, and `italic`,
  matching the same family selected explicitly. Styled text that previously used
  the regular default face may change appearance and layout.
- Canonical samples and shared exports report actual selected font identities
  and rendering-library versions. Remote fonts use content-addressed copies so
  refreshing another document does not change a prefetched face.
