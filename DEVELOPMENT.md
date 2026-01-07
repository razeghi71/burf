## Development

### Versioning

This repo uses **git tags as the source of truth for the package version** (via `hatch-vcs`).

- Create tags like `v1.2.3`
- The published package version becomes `1.2.3`
- You do **not** manually edit versions in `pyproject.toml` or in code

### Release process (automated)

#### 1) Label PRs with the intended semver bump

Each PR must have **exactly one** of:

- `major`
- `minor`
- `patch`

Also supported: `semver:major`, `semver:minor`, `semver:patch`.

#### 2) Merge the PR

On merge, CI will:

- compute the next semver tag
- push the new `vX.Y.Z` tag
- create a GitHub Release (auto-generated notes)

If the repo has no existing `v*` tags yet, CI seeds from the last previously hardcoded version: `1.2.1`.

#### 3) Tag push publishes to PyPI

When the tag is pushed, CI will build and publish to PyPI.

### PyPI authentication (recommended: Trusted Publisher / OIDC)

The publish workflow is configured for **PyPI Trusted Publishing (OIDC)** so you don’t need a long-lived PyPI API token in GitHub secrets.

To enable it:

- In your project on PyPI, add a **Trusted Publisher**
- Point it at this GitHub repo and the workflow file: `.github/workflows/release-pypi.yml`

### Local build

Build artifacts locally using `uv`:

```bash
uv build
```

