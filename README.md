# burf

burf is a terminal user interface (TUI) for surfing Google Cloud Storage (GCS) buckets.

## Installation

You can install it directly from PyPi:

    pip install burf

or using source code:

    git clone git@github.com:razeghi71/burf.git
    cd burf
    pip install .

## Usage

    usage: burf.py [-h] [-p PROJECT] [gcs_uri]

    positional arguments:
        gcs_uri               gcs uri to browse: gs://<bucket>/<subdir1>/<subdir2>

    options:
        -h, --help            show this help message and exit
        -p PROJECT, --project PROJECT
                                gcp project to use

## License

burf is released under the [MIT License](LICENSE).
