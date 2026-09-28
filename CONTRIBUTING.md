# Contributing

## Local checks

CI installs exactly what `uv.lock` records. Run the same commands locally
(uv 0.10.12 or newer, Python 3.10+):

```bash
uv sync --locked --extra cli --extra svg --extra pptx --extra pdf --dev
uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked ty check quickthumb tests --output-format concise
uv run --locked pre-commit run --all-files
uv run --locked pytest tests/ --ignore=tests/test_rendering.py
```

Video and SVG tests need `ffmpeg` and `libcairo2` from the system package
manager. `tests/test_rendering.py` holds byte-exact PNG snapshots, which
depend on the local font and FreeType setup, and is not part of CI.

## Dependency baseline

- `pyproject.toml` declares supported ranges, bounded below the next major
  version (`add-bounds = "major"`). `uv.lock` pins the versions CI tests.
- `uv lock --check` must pass: any change to a range ships with its lockfile.
- uv only resolves releases at least 14 days old (`exclude-newer = "P14D"`),
  and Dependabot waits 7 days before proposing an update.
- Dependabot opens weekly `uv` updates (range and lockfile together) and
  weekly GitHub Actions updates pinned to commit SHAs. Merge them only when
  Quality, Test, and Security CI pass.
- To refresh everything at once, run `uv lock --upgrade` and the checks above.
- Ruff runs from the lockfile in pre-commit too, so format and lint results
  do not depend on a separately pinned hook version.
