import argparse
import sys
from typing import Any, Optional, Union

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center
from textual.timer import Timer
from textual.widgets import Footer, Header, Label

from burf.downloader_screen import DownloaderScreen
from burf.deleter_screen import DeleterScreen
from burf.error_screen import ErrorScreen
from burf.factory import StorageFactory
from burf.file_list_view import FileListView
from burf.scheme import StorageScheme
from burf.search_box import SearchBox
from burf.storage import HAS_GCS, HAS_S3
from burf.storage.ds import CloudPath
from burf.storage.storage import Storage
from burf.storage_selection_app import StorageSelectionApp, StorageSelectionScreen
from burf.string_getter import StringGetter
from burf.util import parse_uri


class BurfApp(App[Any]):
    BINDINGS = [
        Binding("ctrl+s", "select_storage", "select storage provider"),
        Binding("ctrl+g", "go_to", "go to address"),
        Binding("ctrl+d", "download", "download selected"),
        Binding("ctrl+x", "delete", "delete selected"),
        Binding("ctrl+c", "quit", "Quit"),
    ]

    file_list_view: FileListView
    search_box: SearchBox
    loading_spinner: Label

    def __init__(self, uri: CloudPath, storage: Storage):
        super().__init__()
        self.storage = storage
        self.uri = uri
        self._spinner_timer: Timer | None = None
        self._spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._spinner_idx = 0

    @property
    def current_scheme(self) -> StorageScheme:
        return self.storage.scheme

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
    def change_addr(self, new_addr: Optional[str]) -> None:
        if new_addr is not None:
            scheme, uri = parse_uri(new_addr)
            
            # Check if we need to switch storage backend
            if scheme != self.current_scheme:
                try:
                    self.storage = StorageFactory.create_storage(scheme)
                    self.file_list_view.storage = self.storage
                    # Clear stale items immediately when switching storage
                    self.file_list_view.showing_elems = []
                except ImportError as e:
                    self.push_screen(
                        ErrorScreen(
                            title=f"{scheme.value.upper()} Not Installed",
                            message=str(e)
                        )
                    )
                    return
                except ValueError as e:
                     self.push_screen(
                        ErrorScreen(
                            title="Invalid Scheme",
                            message=str(e)
                        )
                    )
                     return

            self.file_list_view.uri = uri
            self.file_list_view.refresh_contents()

    def change_scheme(self, scheme: Optional[Union[str, StorageScheme]]) -> None:
        if scheme is not None:
            if isinstance(scheme, str):
                try:
                    scheme = StorageScheme(scheme)
                except ValueError:
                     self.push_screen(
                        ErrorScreen(title="Invalid Scheme", message=f"Unknown scheme: {scheme}")
                    )
                     return

            if scheme == self.current_scheme:
                # If same scheme, just go to root
                self.file_list_view.uri = CloudPath(scheme, "", [])
                self.file_list_view.refresh_contents()
                return
            
            try:
                self.storage = StorageFactory.create_storage(scheme)
                self.file_list_view.storage = self.storage
                # Clear stale items immediately when switching storage
                self.file_list_view.showing_elems = []
                # Reset to root of that storage
                self.file_list_view.uri = CloudPath(scheme, "", [])
                self.file_list_view.refresh_contents()
            except ImportError as e:
                self.push_screen(
                    ErrorScreen(
                        title=f"{scheme.value.upper()} Not Installed",
                        message=str(e)
                    )
                )
            except ValueError as e:
                self.push_screen(
                    ErrorScreen(
                        title="Invalid Scheme",
                        message=str(e)
                    )
                )

    # actions
    def action_select_storage(self) -> None:
        def handle_selection(scheme: str | None) -> None:
            if scheme:
                self.change_scheme(scheme)

        self.push_screen(StorageSelectionScreen(), handle_selection)

    def action_go_to(self) -> None:
        self.push_screen(
            StringGetter(place_holder="gs://bucket/path or s3://bucket/path"),
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
        message = f"Forbidden to access: {af.path}\n\n"
        
        if self.current_scheme == StorageScheme.GCS:
            message += (
                "This app relies on Application Default Credentials (ADC).\n"
                "Authenticate and/or switch identity outside the app (e.g. with gcloud),\n"
                "then re-run burf.\n\n"
                "Common fix:\n"
                "  gcloud auth application-default login\n"
            )
        elif self.current_scheme == StorageScheme.S3:
             message += (
                "Check your AWS credentials/profile.\n"
                "You might need to run `aws configure` or set AWS_PROFILE.\n"
            )

        self.push_screen(
            ErrorScreen(
                title="Access forbidden",
                message=message,
            )
        )


def main() -> Any | None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "uri",
        nargs="?",
        help="uri to browse: gs://<bucket>/... or s3://<bucket>/...",
    )

    args = parser.parse_args()

    # Determine initial URI and Storage
    if args.uri:
        scheme, uri = parse_uri(args.uri)
    else:
        # Ask user for preference
        if not HAS_GCS and not HAS_S3:
             print("No storage backends installed. Please install burf[gcs] or burf[s3].")
             return None
        
        selection_app = StorageSelectionApp()
        scheme_str = selection_app.run()
        if scheme_str is None:
            return None
        scheme = StorageScheme(scheme_str)
        uri = CloudPath(scheme, "", [])
    
    try:
        storage = StorageFactory.create_storage(scheme)
    except (ImportError, ValueError) as e:
        print(f"Error: {e}")
        sys.exit(1)

    app = BurfApp(
        uri=uri,
        storage=storage,
    )

    return app.run()


if __name__ == "__main__":
    main()
