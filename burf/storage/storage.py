from abc import ABC, abstractmethod
from typing import List

from burf.storage.ds import BucketWithPrefix


class Storage(ABC):
    @property
    @abstractmethod
    def scheme(self) -> str:
        pass

    @abstractmethod
    def list_buckets(self) -> List[BucketWithPrefix]:
        pass

    @abstractmethod
    def list_prefix(self, uri: BucketWithPrefix) -> List[BucketWithPrefix]:
        pass

    @abstractmethod
    def list_all_blobs(self, uri: BucketWithPrefix) -> List[BucketWithPrefix]:
        pass

    @abstractmethod
    def get_project(self) -> str:
        pass

    @abstractmethod
    def download_to_filename(self, uri: BucketWithPrefix, dest: str) -> None:
        pass

    @abstractmethod
    def delete_blob(self, uri: BucketWithPrefix) -> None:
        """Delete a single blob object."""
        pass
