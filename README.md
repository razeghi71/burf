# burf

burf is a terminal user interface (TUI) for surfing Google Cloud Storage (GCS) buckets.

## Installation

### With uv (recommended)

Install from PyPI:

    uv tool install burf

Or run from source:

    git clone git@github.com:razeghi71/burf.git
    cd burf
    uv sync

### With pip

You can install it directly from PyPi:

    pip install burf

or using source code:

    git clone git@github.com:razeghi71/burf.git
    cd burf
    pip install .

## Usage

Run via uv from source:

    uv run burf --help

CLI:

    usage: burf [-h] [-p PROJECT] [gcs_uri]

    positional arguments:
        gcs_uri               gcs uri to browse: gs://<bucket>/<subdir1>/<subdir2>

    options:
        -h, --help            show this help message and exit
        -p PROJECT, --project PROJECT
                                gcp project to use

### Authentication

This app relies on Google Application Default Credentials (ADC). A common setup is:

    gcloud auth application-default login

## License

burf is released under the [MIT License](LICENSE).

## Releases

This repo uses **git tags as the source of truth for the package version** (via `hatch-vcs`). You do not need to edit versions in files.

### How a release is cut

- Add exactly one label to each PR: **`major`**, **`minor`**, or **`patch`** (also supported: `semver:major`, `semver:minor`, `semver:patch`).
- When the PR is merged, CI creates and pushes the next `vX.Y.Z` tag and creates a GitHub release automatically.
- Pushing the tag triggers the PyPI publish workflow.

If this repo has no `v*` tags yet, the first automated tag will be based off the last previously hardcoded version (`1.2.1`).

### PyPI authentication (recommended)

The PyPI publish workflow is configured for **PyPI Trusted Publishing (OIDC)**, which avoids storing a long-lived PyPI API token in GitHub secrets.

To enable it on PyPI:

- In your project on PyPI, configure a **Trusted Publisher** pointing at this GitHub repo and the workflow file `.github/workflows/release-pypi.yml`.
