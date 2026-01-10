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

    usage: burf [-h] [gcs_uri]

    positional arguments:
        gcs_uri               gcs uri to browse: gs://<bucket>/<subdir1>/<subdir2>

    options:
        -h, --help            show this help message and exit

### Authentication

This app relies on Google Application Default Credentials (ADC). A common setup is:

    gcloud auth application-default login

To choose which GCP project is used for listing buckets, configure it outside the app, e.g.:

    gcloud config set project YOUR_PROJECT_ID
    export GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID

## License

burf is released under the [MIT License](LICENSE).
