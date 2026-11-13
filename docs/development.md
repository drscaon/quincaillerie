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

### Continuous integration

| Workflow | When | What |
|---|---|---|
| `ci.yml` | every push to `main`, every pull request | `ruff check` and `ruff format --check`; `pytest` on Python 3.11–3.13 (Linux) and 3.12 (macOS, Windows); a command-line smoke test; **the MuJoCo checks of the whole catalogue** and an M8 screwing, then **varied batches** (screws and nuts with crushed threads that must jam, cells and holders with drawn tolerances and springs); **the Blender checks** of the catalogue and of varied batches through the add-on (and, for comparison, by hand); reports kept as run artifacts; build the wheel and sdist, `twine check`, install the wheel in a clean environment. |
| `release.yml` | a pushed tag `v*` | checks the tag matches the version in `pyproject.toml`, tests, builds, then creates the GitHub release with the packages and the Blender add-on attached and the notes taken from `CHANGELOG.md`. Versions with `a`, `b` or `rc` are marked as pre-releases. |
| Dependabot | monthly | pull requests to update the GitHub Actions and the Python dependencies. |
