import argparse
from typing import Any, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center
from textual.timer import Timer
from textual.widgets import Footer, Header, Label

from burf.downloader_screen import DownloaderScreen
from burf.deleter_screen import DeleterScreen
from burf.error_screen import ErrorScreen
from burf.file_list_view import FileListView
from burf.search_box import SearchBox
from burf.storage.ds import BucketWithPrefix
from burf.storage.storage import GCS
from burf.string_getter import StringGetter
from burf.util import get_gcs_bucket_and_prefix


class GSUtilUIApp(App[Any]):
    BINDINGS = [
        Binding("ctrl+p", "project_select", "select gcp project"),
        Binding("ctrl+g", "go_to", "go to address"),
        Binding("ctrl+d", "download", "download selected"),
        Binding("ctrl+x", "delete", "delete selected"),
        Binding("ctrl+c", "quit", "Quit"),
    ]

    file_list_view: FileListView
    search_box: SearchBox
    loading_spinner: Label

    def __init__(self, uri: BucketWithPrefix, gcp_project: Optional[str]):
        super().__init__()
        self.storage = GCS(project=gcp_project)
        self.uri = uri
        self._spinner_timer: Timer | None = None
        self._spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._spinner_idx = 0

    def compose(self) -> ComposeResult:
        self.loading_spinner = Label("", id="loading_spinner")
        self.loading_spinner.styles.display = "none"

        self.file_list_view = FileListView(
            storage=self.storage,
            uri=self.uri,
            id="file_list",
        )
        self.search_box = SearchBox(id="search_box")

        yield Header()
        with Center():
            yield self.loading_spinner
        yield self.file_list_view
        yield self.search_box
        yield Footer()

    def on_mount(self) -> None:
        # Make the file list the default focus target so selection is visible
        # and arrow keys behave as expected.
        self.file_list_view.focus()

    def set_loading(self, is_loading: bool) -> None:
        if is_loading:
            self._spinner_idx = 0
            self.loading_spinner.update(f"{self._spinner_frames[self._spinner_idx]} Loading…")
            self.loading_spinner.styles.display = "block"

            if self._spinner_timer is None:
                self._spinner_timer = self.set_interval(0.08, self._tick_spinner)
            else:
                self._spinner_timer.resume()
        else:
            if self._spinner_timer is not None:
                self._spinner_timer.pause()
            self.loading_spinner.styles.display = "none"

    def _tick_spinner(self) -> None:
        self._spinner_idx = (self._spinner_idx + 1) % len(self._spinner_frames)
        self.loading_spinner.update(f"{self._spinner_frames[self._spinner_idx]} Loading…")

    # screen call-backs
    def change_project(self, project: Optional[str]) -> None:
        if project is not None:
            self.storage.set_project(project)
            self.file_list_view.clear_cache()
            self.file_list_view.refresh_contents()

    def change_addr(self, new_addr: Optional[str]) -> None:
        if new_addr is not None:
            uri = get_gcs_bucket_and_prefix(new_addr)
            self.file_list_view.uri = uri
            self.file_list_view.refresh_contents()

    # actions
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

    def action_delete(self) -> None:
        selected = self.file_list_view.get_selected_uri()
        if selected is None:
            return
        if selected.is_bucket:
            self.push_screen(
                ErrorScreen(
                    title="Delete not supported",
                    message="Deleting buckets is not supported from this UI.",
                )
            )
            return
        self.push_screen(DeleterScreen(selected, self.storage))

    # message handlers
    def on_input_submitted(self, value: SearchBox.Submitted) -> None:
        self.file_list_view.search_and_highlight(value.input.value)

    def on_file_list_view_access_forbidden(
        self, af: FileListView.AccessForbidden
    ) -> None:
        self.push_screen(
            ErrorScreen(
                title="Access forbidden",
                message=(
                    f"Forbidden to access: {af.path}\n\n"
                    "This app relies on Application Default Credentials (ADC).\n"
                    "Authenticate and/or switch identity outside the app (e.g. with gcloud),\n"
                    "then re-run burf.\n\n"
                    "Common fix:\n"
                    "  gcloud auth application-default login\n"
                ),
            )
        )

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
    parser.add_argument("-p", "--project", help="gcp project to use")

    args = parser.parse_args()

    if args.gcs_uri:
        uri = get_gcs_bucket_and_prefix(args.gcs_uri)
    else:
        uri = BucketWithPrefix("", [])

    gcp_project = args.project

    app = GSUtilUIApp(
        uri=uri,
        gcp_project=gcp_project,
    )

    return app.run()


if __name__ == "__main__":
    main()
