import os
import threading
from enum import Enum
from typing import Iterator

from textual.app import ComposeResult
from textual.containers import Center, Container, Horizontal, Middle
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ProgressBar

from burf.storage.ds import BucketWithPrefix
from burf.storage.paths import Blob
from burf.storage.storage import Storage


class Downloader:
    def __init__(self, uri: BucketWithPrefix, storage: Storage) -> None:
        self._uri = uri
        self._storage = storage
        self._stopped = False

    @property
    def uri(self) -> BucketWithPrefix:
        return self._uri

    @property
    def stopped(self):
        return self._stopped

    @stopped.setter
    def stopped(self, new):
        self._stopped = new

    def number_of_blobs(self) -> int:
        return len(
            self._storage.list_all_blobs(self._uri.bucket_name, self._uri.prefix)
        )

    def download(self, destination_folder: str) -> Iterator[Blob]:
        blobs = self._storage.list_all_blobs(self._uri.bucket_name, self._uri.prefix)
        for blob in blobs:
            if not self.stopped:
                destination_path = os.path.join(
                    destination_folder, blob.name[len(self._uri.prefix) :]
                )
                # TODO: uncomment this and also put everything in the original bucket name
                # os.makedirs(os.path.dirname(destination_path), exist_ok=True)
                self._storage.download_to_filename(blob, destination_path)
                yield blob
            else:
                break


class State(Enum):
    STOPPED = 0
    STARTED = 1


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
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)
        self._downloader = Downloader(download_uri, storage)
        self.state = State.STOPPED

    def start_download(self) -> None:
        for blob in self._downloader.download("."):
            self.progress.advance(1)
            self.label.update(f"Downloaded {blob.name}")
        self.label.update("Download Finished")

    def compose(self) -> ComposeResult:
        self.label = Label("Starting Download", id="download-info")
        self.progress = ProgressBar(total=self._downloader.number_of_blobs())
        download_to = os.getcwd()

        yield Header()

        with Container(id="question"):
            with Center():
                self.question_label = Label(
                    f"Proceed Downloading {self._downloader.uri} => {download_to}"
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

    def action_close(self):
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
