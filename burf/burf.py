import sys
import re

from textual._path import CSSPathType
from textual.app import App, CSSPathType, ComposeResult
from textual.driver import Driver
from textual.widgets import Header, Footer, Input
from textual.binding import Binding

from burf.file_list_view import FileListView
from burf.service_account import ServiceAccountSelectScreen
from burf.storage import GCS


class GSUtilUIApp(App):
    BINDINGS = [
        Binding("d", "toggle_dark", "Toggle dark mode"),
        Binding("/", "search", "Search"),
        Binding("escape", "escape", "Cancel search", show=False),
        Binding("ctrl+s", "service_account_select", "Select service account"),
    ]

    def __init__(
        self,
        start_bucket,
        start_subdir,
        driver_class: type[Driver] | None = None,
        css_path: CSSPathType | None = None,
        watch_css: bool = False,
    ):
        super().__init__(driver_class, css_path, watch_css)
        self.start_bucket = start_bucket
        self.start_subdir = start_subdir

    def compose(self) -> ComposeResult:
        yield Header()
        yield FileListView(
            storage=GCS(),
            start_bucket=self.start_bucket,
            start_subdir=self.start_subdir,
            id="file_list",
        )
        yield Input(id="search_box")
        yield Footer()

    def change_service_account(self, service_account):
        pass
        # self.query_one("#file_list").change_service_account(service_account)

    def action_service_account_select(self):
        self.push_screen(
            ServiceAccountSelectScreen(), lambda x: self.change_service_account
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
    bucket_name, subdir = "", ""
    if len(sys.argv) > 1:
        bucket_name, subdir = get_gcs_bucket_and_subdir(sys.argv[1])

    app = GSUtilUIApp(start_bucket=bucket_name, start_subdir=subdir)
    app.run()


if __name__ == "__main__":
    main()
