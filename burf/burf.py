import argparse
import os
from typing import Any, Optional

from google.oauth2 import service_account
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from burf.credentials_provider import CredentialsProvider
from burf.credentials_selector import CredentialsSelector
from burf.downloader_screen import DownloaderScreen
from burf.file_list_view import FileListView
from burf.search_box import SearchBox
from burf.storage.ds import BucketWithPrefix
from burf.storage.storage import GCS
from burf.string_getter import StringGetter
from burf.util import get_gcs_bucket_and_prefix


DEFAULT_CONFIG_FILE = "~/.config/burf/burf.conf"
DEFAULT_CONFIG_FILE_WINDOWS = "~\\AppData\\Local\\burf\\burf.conf"


class GSUtilUIApp(App[Any]):
    BINDINGS = [
        Binding("ctrl+s", "service_account_select", "select service account"),
        Binding("ctrl+p", "project_select", "select gcp project"),
        Binding("ctrl+g", "go_to", "go to address"),
        Binding("ctrl+d", "download", "download selected"),
        Binding("ctrl+c", "quit", "Quit"),
    ]

    file_list_view: FileListView
    search_box: SearchBox

    def __init__(self, uri: BucketWithPrefix, config_file: str, gcp_project: str):
        super().__init__()
        self.storage = GCS(project=gcp_project)
        self.uri = uri

        self.config_file = config_file

        if not config_file:
            if os.name == "nt":
                self.config_file = DEFAULT_CONFIG_FILE_WINDOWS
            else:
                self.config_file = DEFAULT_CONFIG_FILE

        config_file_path = os.path.expanduser(self.config_file)
        config_dir = os.path.dirname(config_file_path)
        os.makedirs(config_dir, exist_ok=True)

        if not os.path.exists(config_file_path):
            # Create an empty config file if it doesn't exist
            open(config_file_path, "a").close()

    def compose(self) -> ComposeResult:
        self.file_list_view = FileListView(
            storage=self.storage,
            uri=self.uri,
            id="file_list",
        )
        self.search_box = SearchBox(id="search_box")

        yield Header()
        yield self.file_list_view
        yield self.search_box
        yield Footer()

    # screen call-backs
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

    def change_addr(self, new_addr: Optional[str]) -> None:
        if new_addr is not None:
            uri = get_gcs_bucket_and_prefix(new_addr)
            self.file_list_view.uri = uri
            self.file_list_view.refresh_contents()

    # actions
    def action_service_account_select(self, error: Optional[str] = None) -> None:
        self.push_screen(
            CredentialsSelector(CredentialsProvider(self.config_file), error),
            self.change_service_account,
        )

    def action_project_select(self, error: Optional[str] = None) -> None:
        self.push_screen(
            StringGetter(place_holder="gcp project name", error=error),
            self.change_project,
        )

    def action_go_to(self) -> None:
        self.push_screen(
            StringGetter(place_holder="gs://bucket_name/subdir1/subdir2"),
            self.change_addr,
        )

    def action_download(self) -> None:
        selected = self.file_list_view.get_selected_uri()

        if selected is not None:
            self.push_screen(DownloaderScreen(selected, self.storage))

    # message handlers
    def on_input_submitted(self, value: SearchBox.Submitted) -> None:
        self.file_list_view.search_and_highlight(value.input.value)

    def on_file_list_view_access_forbidden(
        self, af: FileListView.AccessForbidden
    ) -> None:
        self.action_service_account_select(f"Forbidden to get {af.path}")

    def on_file_list_view_invalid_project(
        self, ip: FileListView.InvalidProject
    ) -> None:
        self.action_project_select(
            f"Invalid Project Name: {ip.project}, please enter a valid project name:"
        )


def main() -> Any | None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "gcs_uri",
        nargs="?",
        help="gcs uri to browse: gs://<bucket>/<subdir1>/<subdir2>",
    )
    parser.add_argument("-c", "--config", help="path to config file")
    parser.add_argument("-p", "--project", help="gcp project to use")

    args = parser.parse_args()

    if args.gcs_uri:
        uri = get_gcs_bucket_and_prefix(args.gcs_uri)
    else:
        uri = BucketWithPrefix("", "")

    config_file = args.config
    gcp_project = args.project

    app = GSUtilUIApp(
        config_file=config_file,
        uri=uri,
        gcp_project=gcp_project,
    )

    return app.run()


if __name__ == "__main__":
    main()
