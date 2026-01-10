import argparse
import sys
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
from burf.storage import GCS, HAS_GCS, HAS_S3, S3
from burf.storage.ds import CloudPath
from burf.storage.storage import Storage
from burf.storage_selection_app import StorageSelectionApp
from burf.string_getter import StringGetter
from burf.util import parse_uri


class BurfApp(App[Any]):
    BINDINGS = [
        Binding("ctrl+p", "project_select", "select gcp project/aws profile"),
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
    def current_scheme(self) -> str:
        # Determine scheme based on instance type
        if HAS_GCS and isinstance(self.storage, GCS):
            return "gs"
        if HAS_S3 and isinstance(self.storage, S3):
            return "s3"
        return "unknown"

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
    def change_project(self, project: Optional[str]) -> None:
        if project is not None:
            if self.current_scheme == "gs":
                # We can safely assume it is GCS because of current_scheme impl
                # Type checker might need ignore or cast, but runtime is safe.
                self.storage.set_project(project) # type: ignore
            elif self.current_scheme == "s3":
                # For S3, we treat 'project' as profile
                self.storage = S3(profile=project)
                self.file_list_view.storage = self.storage
            
            self.file_list_view.clear_cache()
            self.file_list_view.refresh_contents()

    def change_addr(self, new_addr: Optional[str]) -> None:
        if new_addr is not None:
            scheme, uri = parse_uri(new_addr)
            
            # Check if we need to switch storage backend
            if scheme == "s3":
                if not HAS_S3:
                    self.push_screen(
                        ErrorScreen(
                            title="S3 Not Installed",
                            message="S3 support is not installed.\n\nPlease install it with:\n  pip install burf[s3]"
                        )
                    )
                    return
                if self.current_scheme != "s3":
                    self.storage = S3()
                    self.file_list_view.storage = self.storage

            elif scheme == "gs":
                if not HAS_GCS:
                    self.push_screen(
                        ErrorScreen(
                            title="GCS Not Installed",
                            message="GCS support is not installed.\n\nPlease install it with:\n  pip install burf[gcs]"
                        )
                    )
                    return
                if self.current_scheme != "gs":
                    self.storage = GCS()
                    self.file_list_view.storage = self.storage
            
            self.file_list_view.uri = uri
            self.file_list_view.refresh_contents()

    # actions
    def action_project_select(self, error: Optional[str] = None) -> None:
        self.push_screen(
            StringGetter(place_holder="gcp project name / aws profile", error=error),
            self.change_project,
        )

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
        
        if self.current_scheme == "gs":
            message += (
                "This app relies on Application Default Credentials (ADC).\n"
                "Authenticate and/or switch identity outside the app (e.g. with gcloud),\n"
                "then re-run burf.\n\n"
                "Common fix:\n"
                "  gcloud auth application-default login\n"
            )
        elif self.current_scheme == "s3":
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

    def on_file_list_view_invalid_project(
        self, ip: FileListView.InvalidProject
    ) -> None:
        self.action_project_select(
            f"Invalid Project/Profile Name: {ip.project}, please enter a valid name:"
        )


def main() -> Any | None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "uri",
        nargs="?",
        help="uri to browse: gs://<bucket>/... or s3://<bucket>/...",
    )
    parser.add_argument("-p", "--project", help="gcp project or aws profile to use")

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
        scheme = selection_app.run()
        if scheme is None:
            return None
        uri = CloudPath(scheme, "", [])

    project_or_profile = args.project
    storage: Optional[Storage] = None

    if scheme == "s3":
        if not HAS_S3:
            print("Error: S3 dependencies not found.")
            print("Please install them with: pip install burf[s3]")
            sys.exit(1)
        storage = S3(profile=project_or_profile)
    else:
        # Default to gs
        if not HAS_GCS:
            print("Error: GCS dependencies not found.")
            print("Please install them with: pip install burf[gcs]")
            sys.exit(1)
        storage = GCS(project=project_or_profile)

    app = BurfApp(
        uri=uri,
        storage=storage,
    )

    return app.run()


if __name__ == "__main__":
    main()
