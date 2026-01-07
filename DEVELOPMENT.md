## Development (for contributors)

### Local setup

```bash
uv sync
uv run burf --help
```

### Versioning + releases

- Versions come from **git tags** (`vX.Y.Z`) via `hatch-vcs`. Don’t edit versions in files.
- On **merge**, CI bumps the tag based on PR labels:
  - `major` / `minor` / `patch` (or `semver:*`)
  - **No label = no release**
- The pushed tag triggers the PyPI publish workflow (using PyPI Trusted Publishing / OIDC).

