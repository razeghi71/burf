from abc import ABC, abstractmethod
from google.cloud import storage


class Path(ABC):
    def __init__(self, name) -> None:
        self.name = name


class Dir(Path):
    pass


class Blob(Path):
    pass


class Storage(ABC):
    @abstractmethod
    def list_buckets(self) -> Path:
        pass

    @abstractmethod
    def list_prefix(self, bucket_name: str, prefix: str) -> Path:
        pass


class GCS(Storage):
    def __init__(self, credentials=None) -> None:
        self.client = storage.Client(credentials=credentials)

    def set_credentials(self, credentials):
        self.client = storage.Client(credentials=credentials)

    def list_buckets(self):
        buckets = self.client.list_buckets()
        return [Dir(bucket.name) for bucket in buckets]

    def list_prefix(self, bucket_name: str, prefix: str):
        blobs = self.client.bucket(bucket_name).list_blobs(delimiter="/", prefix=prefix)
        blob_list = list(blobs)

        result = [Dir(subdir) for subdir in blobs.prefixes] + [
            Blob(blob.name) for blob in blob_list
        ]

        sorted_result = sorted(result, key=lambda x: x.name)

        return sorted_result
