# Release gate

The **Release gate** workflow verifies an exact candidate before publication.
It runs for every pull request (including non-`main` bases), manually, and as a
required job of the existing automated release workflow on `main`. It does not
publish packages or deploy documentation itself.

The publishing job pins each new release tag to the triggering commit that
passed the gate, even if `main` advances while verification is running.

For merge protection, require the aggregate **Release validation result** check
in the repository's branch rules. Existing required-check names may need to be
updated when adopting the reusable workflows. This change does not edit branch
rules or grant merge/release permissions.

**A green verification run is not a v1 support declaration.** The separate
`release-readiness.json` decision record currently reports v1 as blocked by
unfinished conformance and support decisions. When the package version leaves
`0.x`, pending requirements fail the gate and prevent the publish job from
starting. Prerelease versions such as `1.0.0rc1` are gated too.

## Candidate verification matrix

These are proposed v1 verification profiles, not a claim that every platform
and optional feature is already supported. Maintainers must approve the final
support policy in the decision record.

| Profile | Python | Runner | Required checks |
| --- | --- | --- | --- |
| Core wheel | 3.10, 3.11, 3.12 | Ubuntu 24.04, Windows Server 2022, macOS 14 | Clean locked runtime install, Canvas/Deck core smoke, absent-extra guidance |
| Full export wheel rebuilt from sdist | 3.10, 3.11, 3.12 | Ubuntu 24.04 | Locked `cli`, `svg`, `pdf`, `pptx` extras, Cairo, FFmpeg/ffprobe, real export smoke |
| Quality and regression suite | 3.10 | Ubuntu | Format, lint, types, pre-commit, build, HTML size, tests and coverage |
| Security | 3.10 | Ubuntu | Secrets, locked dependencies, code and workflow scanning |
| Documentation | 3.10 | Ubuntu | Locked documentation install and strict MkDocs build |

The matrix deliberately does not imply coverage for newer Python versions,
Linux distributions other than the named runner, Intel macOS, ARM Windows,
all optional extras on Windows/macOS, or the model-downloading `rembg` extra.
Core metadata still allows Python 3.10+; the tested subset above is narrower.
Changing that metadata or making additional support promises requires a
reviewed support decision, not just another green cell.

## What the gate proves

- Runtime dependencies come from `uv.lock` via `uv export --locked`, installed
  with `uv pip sync` into a new virtual environment. The wheel is then installed
  with `--no-deps`, so dependency resolution cannot silently replace the lock
- The smoke process runs outside the source checkout. It imports the installed
  package, including packaged HTML assets, rather than an editable source tree
- Core jobs omit every extra and development dependency. Missing optional
  features must produce actionable installation guidance, while core exports
  continue to work
- Full jobs rebuild a wheel from the sdist, validate distribution metadata, and
  require actual native tools. A missing required tool fails instead of skipping
- Every aggregate dependency must finish successfully. Failure, cancellation,
  or a skipped job is not a successful release result
- Logs and job summaries contain structured smoke results and the separate v1
  decision with explicit blockers

Build tooling is isolated by `uv build --no-sources`; runtime and documentation
dependencies are locked. This is not a byte-reproducible distribution claim:
the build backend is currently specified by the project's build-system range.

## Smoke coverage is not full conformance

The geometry-only smoke fixtures exercise installed public APIs without
network assets or host fonts. They check static outputs and basic animation,
output dimensions, selected pixels/timing, package resources and actionable
absence behavior. Structural PDF/PPTX checks do not establish editability or
visual parity in office applications. A real MP4/WebM encode is not proof of
caption, narration or reduced-motion correctness.

Absence checks cover the four declared release extras and FFmpeg. They do not
simulate a broken Cairo shared-library installation or `rembg` model downloads;
those remain support/conformance decisions rather than implied passing checks.

The following work therefore remains a v1 requirement:

- [#129](https://github.com/sjquant/quickthumb/issues/129): static fidelity,
  capability and fallback conformance, including its own prerequisite policies
- [#130](https://github.com/sjquant/quickthumb/issues/130): end-to-end motion,
  Deck, narration, audio, caption and reduced-motion behavior
- [#131](https://github.com/sjquant/quickthumb/issues/131): asset, font and plugin
  lifecycle regression fixtures
- [#132](https://github.com/sjquant/quickthumb/issues/132): final public API,
  canonical JSON and export support documentation

[#134](https://github.com/sjquant/quickthumb/issues/134) is already completed;
that historical completion does not waive candidate-specific install, test or
security checks. Byte-exact `tests/test_rendering.py` snapshots remain excluded
from CI because they depend on the font/FreeType environment. Existing optional
snapshot tests may also skip LibreOffice rasterization. Review these limitations
explicitly rather than interpreting the regression job as complete conformance.

## Reproduce a clean core-wheel check

Use a fresh checkout and a Python version from the matrix. On POSIX systems:

```bash
uv build --no-sources
uv export --locked --no-dev --no-emit-project --no-editable --output-file core-requirements.txt
uv venv /tmp/quickthumb-release-env
uv pip sync --python /tmp/quickthumb-release-env/bin/python core-requirements.txt
uv pip install --python /tmp/quickthumb-release-env/bin/python --no-deps dist/*.whl
script="$PWD/scripts/release_smoke.py"
cd /tmp
/tmp/quickthumb-release-env/bin/python "$script" --profile core --output /tmp/quickthumb-core-smoke
```

Use a new environment for each run. On Windows use the environment's
`Scripts/python.exe`. For the full profile, export requirements with
`--extra cli --extra svg --extra pdf --extra pptx`, install Cairo and
FFmpeg/ffprobe, and pass `--profile full`. Match the sdist round-trip steps in
the workflow when checking packaging changes. See [Installation](installation.md)
for optional-tool setup and [Diagnostics](diagnostics.md) for `quickthumb doctor`.

## Release decision checklist

Review `release-readiness.json` in the same PR as the candidate. Each required
entry stays `pending` until its evidence has been reviewed; acceptance needs a
specific issue, test artifact, document or decision, not an empty value.

- [ ] Record the candidate commit and the complete successful workflow run
- [ ] Review the proposed Python/platform matrix and all exclusions above
- [ ] Complete the static, motion, asset/plugin and documentation requirements
- [ ] Record known limitations, unsupported features and fallback decisions
- [ ] Review changelog entries and compatibility changes for the target version
- [ ] Confirm package version, classifiers, license, links and support claims
- [ ] Confirm each accepted requirement still applies to the candidate commit
- [ ] Run `python scripts/release_readiness.py release-readiness.json --require-ready`

The record is a human-reviewed decision, not an automatic issue-closure bot.
Do not mark an issue accepted simply because it is closed. Keep evidence in
version control and revalidate it when the candidate changes. The automated
publish job only proceeds after both verification and this decision pass for
stable-version candidates; merging a draft PR is a separate maintainer action.
