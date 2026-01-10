# burf

burf is a terminal user interface (TUI) for surfing **Google Cloud Storage (GCS)** and **AWS S3** buckets.

## Installation

### With uv (recommended)

Install from PyPI:

    uv tool install burf

To include dependencies for specific providers:

    # For GCS support only
    uv tool install "burf[gcs]"

    # For S3 support only
    uv tool install "burf[s3]"

    # For both
    uv tool install "burf[all]"

### With pip

You can install it directly from PyPi:

    pip install "burf[all]"

or using source code:

    git clone git@github.com:razeghi71/burf.git
    cd burf
    pip install ".[all]"

## Usage

    burf [uri]

Positional arguments:
    `uri` (optional): URI to browse (e.g., `gs://my-bucket` or `s3://my-bucket`).

If no URI is provided, you will be prompted to select a storage provider (GCS or S3).

### Examples

    # Launch selection screen
    burf

    # Browse a GCS path
    burf gs://my-bucket/data/

    # Browse an S3 path
    burf s3://my-bucket/data/

### Authentication

**Google Cloud Storage (GCS):**
This app relies on Google Application Default Credentials (ADC). A common setup is:

    gcloud auth application-default login

**AWS S3:**
This app relies on standard AWS credential resolution (environment variables, `~/.aws/credentials`, etc.). To set up your default profile:

    aws configure

Or set the environment variable:

    export AWS_PROFILE=my-profile

## Key Bindings

- `Ctrl+g`: Go to a specific address (URI)
- `Ctrl+d`: Download selected item(s)
- `Ctrl+x`: Delete selected item(s)
- `Ctrl+c`: Quit
- `/`: Search in the current list

## License

burf is released under the [MIT License](LICENSE).
