from os.path import expanduser
from typing import Generator

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, Label

from burf.storage.ds import BucketWithPrefix
from burf.storage.storage import Storage


class Downloader:
    def __init__(self, uri: BucketWithPrefix, storage: Storage) -> None:
        self._uri = uri
        self._storage = storage

    def number_of_buckets(self):
        pass

    def download(self) -> Generator[str]:
        pass


class DownloaderScreen(Screen[None]):
    def __init__(
        self,
        download_uri: str,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)
        self._downloader = Downloader(download_uri)

    def compose(self) -> ComposeResult:
        yield Header(f"Downloading {self.download_uri}")
        yield Label(f"Downloading {self.download_uri} to {expanduser('.')}")
        yield Footer()
