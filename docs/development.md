# Development

Branch and release conventions, how the README images are made, continuous integration.

Part of the [Quincaillerie](../README.md) documentation.

## Development

The project follows **GitHub Flow**:

1. `main` is always releasable and protected: changes reach it only through
   pull requests, nobody pushes to it directly.
2. Every change starts on a short-lived branch from `main`, named after its
   type: `feat/<name>`, `fix/<name>`, `docs/<name>`, `ci/<name>`, …
3. Push the branch and open a pull request into `main`; CI runs on it.
4. Merge when CI is green, then delete the branch.

Releasing is a change like any other: on a `chore/release-X.Y.Z` branch, bump
`version` in `pyproject.toml` and move the `Unreleased` entries of
`CHANGELOG.md` under the new version; merge the pull request, then tag
`vX.Y.Z` on `main`. The release workflow builds the packages and attaches
them, with the Blender add-on, to the GitHub release.

A versioned `pre-push` hook refuses direct pushes to `main`. Enable it once per
clone with `git config core.hooksPath .githooks` (emergency override:
`ALLOW_MAIN_PUSH=1 git push`).

The README images are made by [`scripts/`](https://github.com/drscaon/quincaillerie/blob/main/scripts/): `make_logo.py` (logo),
`readme_images.py` (Blender renders and the GitHub social preview
`docs/images/social_preview.png`, to upload in the repository's Settings >
General > Social preview), `physics_gifs.py` (the animations).

### Reproducibility references

`tests/test_golden.py` (shared, byte for byte, by the four generators of the
suite) runs each case of `tests/golden/cases.json` through the command line
and compares every pack table it writes (`instances.csv`: the drawn and the
measured values) with the reference stored in `tests/golden/<case>.json`. It
runs on every Python and platform of the CI, so the same version, preset,
seed and options must give the same values on Linux, macOS and Windows.
Numbers agree to a relative 1e-7; text exactly. The generator's version is
the only column left out.

A failure means the values changed. When the change is wanted, regenerate the
references and say so in the changelog, under *Changed values*:

```bash
PRIMVARIA_GOLDEN_UPDATE=1 pytest tests/test_golden.py
```

### Continuous integration

CI runs at two levels. On every commit (push to `main`, pull request), the fast level: the tests not marked `slow` (`pytest -m "not slow"`), on Linux and Python 3.12 only, and the engine checks on the varied batches only. Before a release, and with **Run workflow** on the Actions page, the full level: every test on Python 3.11–3.13 (Linux) and 3.12 (macOS, Windows), the oldest supported OpenUSD, and the engine checks on the whole catalogue as well. `release.yml` runs the full level first and releases nothing unless it passes. A test is marked `slow` when it takes 8 s or more; run them locally with plain `pytest`.

| Workflow | When | What |
|---|---|---|
| `ci.yml` | every push to `main` and pull request (fast level); before a release and on **Run workflow** (full level) | `ruff check` and `ruff format --check`; `pytest` on Python 3.11–3.13 (Linux) and 3.12 (macOS, Windows) at the full level; a command-line smoke test; **the MuJoCo checks of the whole catalogue** and an M8 screwing, then **varied batches** (screws and nuts with crushed threads that must jam, cells and holders with drawn tolerances and springs); **the Blender checks** of the catalogue and of varied batches through the add-on (and, for comparison, by hand); reports kept as run artifacts; build the wheel and sdist, `twine check`, install the wheel in a clean environment. |
| `release.yml` | a pushed tag `v*` | runs `ci.yml` at its full level, checks the tag matches the version in `pyproject.toml`, builds, then creates the GitHub release with the packages and the Blender add-on attached and the notes taken from `CHANGELOG.md`. Versions with `a`, `b` or `rc` are marked as pre-releases. |
| Dependabot | monthly | pull requests to update the GitHub Actions and the Python dependencies. |
