from abc import ABC, abstractmethod
from google.cloud import storage  # type: ignore
from typing import List


class Dir:
    def __init__(self, name):
        self.name = name

    __match_args__ = ("name",)


class Blob:
    def __init__(self, name, size):
        self.name = name
        self.size = size

    __match_args__ = ("name", "size")


class Storage(ABC):
    @abstractmethod
    def list_buckets(self) -> List[Dir]:
        pass

    @abstractmethod
    def list_prefix(self, bucket_name: str, prefix: str) -> List[Dir | Blob]:
        pass


class GCS(Storage):
    def __init__(self, credentials=None):
        self.client = storage.Client(credentials=credentials)

    def set_credentials(self, credentials) -> None:
        self.client = storage.Client(credentials=credentials)

    def list_buckets(self) -> List[Dir]:
        buckets = self.client.list_buckets()
        return [Dir(bucket.name) for bucket in buckets]

    def list_prefix(self, bucket_name: str, prefix: str) -> List[Dir | Blob]:
        blobs = self.client.bucket(bucket_name).list_blobs(delimiter="/", prefix=prefix)
        blob_list = list(blobs)

        result = [Dir(subdir) for subdir in blobs.prefixes] + [
            Blob(blob.name, blob.size) for blob in blob_list
        ]

        sorted_result = sorted(result, key=lambda x: x.name)

        return sorted_result
