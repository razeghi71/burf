import os
import threading
from typing import Iterator

from textual import events
from textual.app import ComposeResult
from textual.containers import Center, Middle
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, ProgressBar

from burf.storage.ds import BucketWithPrefix
from burf.storage.paths import Blob
from burf.storage.storage import Storage


class Downloader:
    def __init__(self, uri: BucketWithPrefix, storage: Storage) -> None:
        self._uri = uri
        self._storage = storage

    def number_of_blobs(self) -> int:
        return len(
            self._storage.list_all_blobs(self._uri.bucket_name, self._uri.prefix)
        )

    def download(self, destination_folder: str) -> Iterator[Blob]:
        for blob in self._storage.list_all_blobs(
            self._uri.bucket_name, self._uri.prefix
        ):
            destination_path = os.path.join(
                destination_folder, blob.name[len(self._uri.prefix) :]
            )
            # TODO: uncomment this and also put everything in the original bucket name
            # os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            self._storage.download_to_filename(blob, destination_path)
            yield blob


class DownloaderScreen(Screen[None]):
    BINDINGS = [
        ("ctrl+d", "app.pop_screen", "cancel"),
        ("escape", "app.pop_screen", "close"),
    ]

    CSS = """
        Label {
            margin-bottom: 1;
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

    def update_progress(self) -> None:
        for blob in self._downloader.download(os.path.expanduser(".")):
            self.progress.advance(1)
            self.label.update(f"Downloaded {blob.name}")
        self.label.update("Download Finished")

    def _on_mount(self, event: events.Mount) -> None:
        super()._on_mount(event)
        threading.Thread(target=self.update_progress).start()

    def compose(self) -> ComposeResult:
        self.label = Label("Starting Download")
        self.progress = ProgressBar(total=self._downloader.number_of_blobs())
        yield Header()

        with Middle():
            with Center():
                yield self.label
            with Center():
                yield self.progress
        yield Footer()
