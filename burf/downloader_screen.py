import os
import threading
from enum import Enum
from typing import Any, Callable, Optional

from textual.app import ComposeResult
from textual.containers import Center, Container, Horizontal, Middle
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ProgressBar

from burf.storage.ds import BucketWithPrefix
from burf.storage.storage import Storage


class Downloader:
    def __init__(
        self,
        uri: BucketWithPrefix,
        storage: Storage,
        destination: str,
        call_before_each_object: Callable[[BucketWithPrefix, str], Any],
        call_after_each_object: Callable[[BucketWithPrefix, str], Any],
    ) -> None:
        self.uri = uri
        self.stopped = False
        self.destination = destination
        self._call_before = call_before_each_object
        self._call_after = call_after_each_object
        if not uri.is_blob:
            self.destination = os.path.join(
                self.destination, uri.get_last_part_of_address()
            )
        self._storage = storage
        self._blobs: Optional[list[BucketWithPrefix]] = None

    def list_blobs(self) -> list[BucketWithPrefix]:
        if self._blobs is None:
            self._blobs = self._storage.list_all_blobs(self.uri)
        return self._blobs

    def number_of_blobs(self) -> int:
        return len(self.list_blobs())

    def download(self) -> None:
        blobs = self.list_blobs()
        base_prefix = self.uri.full_prefix if not self.uri.is_blob else ""
        for blob in blobs:
            if not self.stopped:
                if base_prefix and blob.full_prefix.startswith(base_prefix):
                    rel_path = blob.full_prefix[len(base_prefix) :]
                else:
                    rel_path = blob.get_last_part_of_address()

                destination_path = os.path.join(self.destination, rel_path)
                destination_dir = os.path.dirname(destination_path)
                if destination_dir:
                    os.makedirs(destination_dir, exist_ok=True)
                self._call_before(blob, destination_path)
                self._storage.download_to_filename(blob, destination_path)
                self._call_after(blob, destination_path)
            else:
                break


class State(Enum):
    STOPPED = 0
    STARTED = 1
    FINISHED = 2


class DownloaderScreen(Screen[None]):
    BINDINGS = [
        ("escape", "close", "close"),
        ("ctrl+d", "close", "close"),
    ]

    CSS = """
        #download-info {
            margin-bottom: 1;
        }
        #downloader {
            display: none;
            padding-top: 2; 
        }
        #question {
            padding-top: 2;
        }
        #horizontal {
            padding-top: 1;
        }
    """

    def __init__(
        self,
        download_uri: BucketWithPrefix,
        storage: Storage,
        download_to: str = os.getcwd(),
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)
        self._download_to = download_to
        self._downloader = Downloader(
            download_uri,
            storage,
            self._download_to,
            self.before_download,
            self.after_download,
        )
        self.state = State.STOPPED
        self._download_thread: Optional[threading.Thread] = None

    def start_download(self) -> None:
        total = self._downloader.number_of_blobs()

        def _set_total() -> None:
            self.progress.total = total

        self.app.call_from_thread(_set_total)

        self._downloader.download()

        def _finish() -> None:
            if self._downloader.stopped:
                self.label.update("Download stopped")
                self.state = State.STOPPED
            else:
                self.label.update("Download finished")
                self.state = State.FINISHED

        self.app.call_from_thread(_finish)

    def before_download(self, uri: BucketWithPrefix, destination: str) -> None:
        self.app.call_from_thread(
            self.label.update, f"Downloading {uri} -> {destination}"
        )

    def after_download(self, uri: BucketWithPrefix, destination: str) -> None:
        def _update() -> None:
            self.progress.advance(1)
            self.label.update(f"Downloaded {uri} -> {destination}")

        self.app.call_from_thread(_update)

    def compose(self) -> ComposeResult:
        self.label = Label("Ready to download", id="download-info")
        # Avoid blocking UI by listing objects in compose; total is set in the worker thread.
        self.progress = ProgressBar(total=0)

        yield Header()

        with Container(id="question"):
            with Center():
                q = (
                    "Proceed downloading "
                    f"{self._downloader.uri} "
                    "=> "
                    f" {self._downloader.destination}"
                )
                self.question_label = Label(q)
                yield self.question_label

            with Horizontal(id="horizontal"):
                with Center():
                    yield Button("Yes", id="yes")
                    yield Button("No", id="no")

        with Middle(id="downloader"):
            with Center():
                yield self.label
            with Center():
                yield self.progress
        yield Footer()

    def action_close(self) -> None:
        if self.state == State.STARTED:
            self.query_one("#question").styles.display = "block"
            self.question_label.update("Do you want to stop the download?")
        else:
            self.dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if self.state == State.STOPPED:
            if event.button.id == "yes":
                self.query_one("#question").styles.display = "none"
                self.query_one("#downloader").styles.display = "block"
                self.state = State.STARTED
                self._downloader.stopped = False
                self._download_thread = threading.Thread(
                    target=self.start_download, daemon=True
                )
                self._download_thread.start()
            else:
                self.dismiss()
        elif self.state == State.STARTED:
            if event.button.id == "yes":
                self._downloader.stopped = True
                self.dismiss()
            else:
                self.query_one("#question").styles.display = "none"
                self.query_one("#downloader").styles.display = "block"

    def on_unmount(self) -> None:
        # If the screen is removed while downloading, request a cooperative stop.
        self._downloader.stopped = True
