# burf

burf is a terminal user interface (TUI) for surfing Google Cloud Storage (GCS) buckets.

## Installation

    git clone git@github.com:razeghi71/burf.git
    cd burf
    pip install .

## Usage

    usage: burf.py [-h] [-c CONFIG] [-p PROJECT] [gcs_uri]

    positional arguments:
        gcs_uri               gcs uri to browse: gs://<bucket>/<subdir1>/<subdir2>

    options:
        -h, --help            show this help message and exit
        -c CONFIG, --config CONFIG
                                path to config file
        -p PROJECT, --project PROJECT
                                gcp project to use

## License

burf is released under the [MIT License](LICENSE).
