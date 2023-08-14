import re
import os
import argparse


from textual._path import CSSPathType
from textual.app import App, CSSPathType, ComposeResult
from textual.driver import Driver
from textual.widgets import Header, Footer, Input
from textual.binding import Binding

from burf.file_list_view import FileListView
from burf.credentials_selector import CredentialsSelector
from burf.credentials_provider import CredentialsProvider
from burf.storage import GCS


DEFAULT_CONFIG_FILE = "~/.config/burf/burf.conf"
DEFAULT_CONFIG_FILE_WINDOWS = "~\\AppData\\Local\\burf\\burf.conf"


class GSUtilUIApp(App):
    BINDINGS = [
        Binding("d", "toggle_dark", "toggle dark mode"),
        Binding("/", "search", "search"),
        Binding("escape", "escape", "cancel search", show=False),
        Binding("ctrl+s", "service_account_select", "select service account"),
    ]

    def __init__(
        self,
        start_bucket,
        start_subdir,
        config_file,
        driver_class: type[Driver] | None = None,
        css_path: CSSPathType | None = None,
        watch_css: bool = False,
    ):
        super().__init__(driver_class, css_path, watch_css)
        self.storage = GCS()
        self.start_bucket = start_bucket
        self.start_subdir = start_subdir

        self.config_file = config_file

        if not config_file:
            if os.name == "nt":
                self.config_file = DEFAULT_CONFIG_FILE_WINDOWS
            else:
                self.config_file = DEFAULT_CONFIG_FILE

    def compose(self) -> ComposeResult:
        yield Header()
        yield FileListView(
            storage=self.storage,
            start_bucket=self.start_bucket,
            start_subdir=self.start_subdir,
            id="file_list",
        )
        yield Input(id="search_box")
        yield Footer()

    def change_service_account(self, service_account):
        if service_account is not None:
            self.storage.set_credentials(service_account)
            self.query_one("#file_list").refresh_contents()

    def action_service_account_select(self, error=None):
        self.push_screen(
            CredentialsSelector(CredentialsProvider(self.config_file), error),
            self.change_service_account,
        )

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    def action_search(self):
        self.query_one("#search_box").focus()

    def on_input_submitted(self, value):
        self.query_one("#file_list").search_and_highlight(value.input.value)

    def action_escape(self):
        self.query_one("#search_box").value = ""
        self.query_one("#file_list").focus()


def get_gcs_bucket_and_subdir(gcs_uri):
    match = re.match(r"gs://(?P<bucket>[^/]+)/*(?P<subdir>.*)", gcs_uri)
    if match:
        bucket = match.group("bucket")
        subdir = match.group("subdir")
    else:
        bucket = gcs_uri
        subdir = ""

    return bucket, subdir


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "gcs_uri",
        nargs="?",
        help="GCS URI of bucket and subdirectory in format gs://<bucket>/<subdir>",
    )
    parser.add_argument("-c", "--config", help="path to config file")

    args = parser.parse_args()

    if args.gcs_uri:
        bucket_name, subdir = get_gcs_bucket_and_subdir(args.gcs_uri)
    else:
        bucket_name, subdir = "", ""

    config_file = args.config

    app = GSUtilUIApp(
        config_file=config_file, start_bucket=bucket_name, start_subdir=subdir
    )

    app.run()


if __name__ == "__main__":
    main()
