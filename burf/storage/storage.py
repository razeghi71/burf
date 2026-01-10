from abc import ABC, abstractmethod
from typing import List

from burf.storage.ds import CloudPath


class Storage(ABC):
    @property
    @abstractmethod
    def scheme(self) -> str:
        pass

    @abstractmethod
    def list_buckets(self) -> List[CloudPath]:
        pass

    @abstractmethod
    def list_prefix(self, uri: CloudPath) -> List[CloudPath]:
        pass

    @abstractmethod
    def list_all_blobs(self, uri: CloudPath) -> List[CloudPath]:
        pass

    @abstractmethod
    def download_to_filename(self, uri: CloudPath, dest: str) -> None:
        pass

    @abstractmethod
    def delete_blob(self, uri: CloudPath) -> None:
        """Delete a single blob object."""
        pass
