import re
import os
import argparse

from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from textual.binding import Binding

from burf.file_list_view import FileListView
from burf.search_box import SearchBox
from burf.credentials_selector import CredentialsSelector
from burf.credentials_provider import CredentialsProvider
from burf.project_selector import ProjectSelector
from burf.storage import GCS

from google.oauth2 import service_account

from typing import Any, Optional


DEFAULT_CONFIG_FILE = "~/.config/burf/burf.conf"
DEFAULT_CONFIG_FILE_WINDOWS = "~\\AppData\\Local\\burf\\burf.conf"


class GSUtilUIApp(App[Any]):
    BINDINGS = [
        Binding("ctrl+s", "service_account_select", "select service account"),
        Binding("ctrl+p", "project_select", "select gcp project"),
    ]

    file_list_view: FileListView
    search_box: SearchBox

    def __init__(
        self,
        start_bucket: str,
        start_subdir: str,
        config_file: str,
    ):
        super().__init__()
        self.storage = GCS()
        self.start_bucket = start_bucket
        self.start_subdir = start_subdir

        self.config_file = config_file

        if not config_file:
            if os.name == "nt":
                self.config_file = DEFAULT_CONFIG_FILE_WINDOWS
            else:
                self.config_file = DEFAULT_CONFIG_FILE  # What if file doesn't exist

    def compose(self) -> ComposeResult:
        self.file_list_view = FileListView(
            storage=self.storage,
            start_bucket=self.start_bucket,
            start_subdir=self.start_subdir,
            id="file_list",
        )
        self.search_box = SearchBox(id="search_box")

        yield Header()
        yield self.file_list_view
        yield self.search_box
        yield Footer()

    def change_service_account(
        self, service_account: Optional[service_account.Credentials]
    ) -> None:
        if service_account is not None:
            self.storage.set_credentials(service_account)
            self.file_list_view.refresh_contents()

    def change_project(self, project: Optional[str]) -> None:
        if project is not None:
            self.storage.set_project(project)
            self.file_list_view.refresh_contents()

    def action_service_account_select(self, error: Optional[str] = None) -> None:
        self.push_screen(
            CredentialsSelector(CredentialsProvider(self.config_file), error),
            self.change_service_account,
        )

    def action_project_select(self) -> None:
        self.push_screen(
            ProjectSelector(),
            self.change_project,
        )

    def on_input_submitted(self, value: SearchBox.Submitted) -> None:
        self.file_list_view.search_and_highlight(value.input.value)

    def on_file_list_view_access_forbidden(
        self, af: FileListView.AccessForbidden
    ) -> None:
        self.action_service_account_select(f"Forbidden to get {af.path}")


def get_gcs_bucket_and_subdir(gcs_uri: str) -> tuple[str, str]:
    match = re.match(r"(gs://)?(?P<bucket>[^/]+)/*(?P<subdir>.*)", gcs_uri)
    if match:
        bucket = match.group("bucket")
        subdir = match.group("subdir")
    else:
        bucket = gcs_uri
        subdir = ""

    return bucket, subdir


def main() -> Any | None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "gcs_uri",
        nargs="?",
        help="gcs uri to browse: gs://<bucket>/<subdir1>/<subdir2>",
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

    return app.run()


if __name__ == "__main__":
    main()
