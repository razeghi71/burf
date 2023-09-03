import os
import threading
from enum import Enum
from typing import Iterator, Callable, Any

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
        call_before_each_object: Callable[[BucketWithPrefix], Any],
        call_after_each_object: Callable[[BucketWithPrefix], Any],
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

    def number_of_blobs(self) -> int:
        return len(self._storage.list_all_blobs(self.uri))

    def download(self):
        blobs = self._storage.list_all_blobs(self.uri)
        for blob in blobs:
            if not self.stopped:
                destination_path = os.path.join(
                    self.destination, blob.get_last_part_of_address()
                )
                os.makedirs(os.path.dirname(destination_path), exist_ok=True)
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

    def start_download(self) -> None:
        self._downloader.download()

        self.state = State.FINISHED
        self.label.update("Download Finished")

    def before_download(self, uri: BucketWithPrefix, destination: str) -> None:
        self.label.update(f"Downloading {uri} -> {destination}")

    def after_download(self, uri: BucketWithPrefix, destination: str) -> None:
        self.progress.advance(1)
        self.label.update(f"Downloaded {uri} -> {destination}")

    def compose(self) -> ComposeResult:
        self.label = Label("Starting Download", id="download-info")
        self.progress = ProgressBar(total=self._downloader.number_of_blobs())

        yield Header()

        with Container(id="question"):
            with Center():
                self.question_label = Label(
                    f"Proceed Downloading {self._downloader.uri} => {self._downloader.destination}"
                )
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
                threading.Thread(target=self.start_download).start()
            else:
                self.dismiss()
        elif self.state == State.STARTED:
            if event.button.id == "yes":
                self._downloader.stopped = True
                self.dismiss()
            else:
                self.query_one("#question").styles.display = "none"
                self.query_one("#downloader").styles.display = "block"
