from abc import ABC, abstractmethod
from google.cloud.storage import Client  # type: ignore
from google.auth.credentials import Credentials
from typing import List, Optional

from burf.storage.paths import Dir, Blob


class Storage(ABC):
    @abstractmethod
    def list_buckets(self) -> List[Dir]:
        pass

    @abstractmethod
    def list_prefix(self, bucket_name: str, prefix: str) -> List[Dir | Blob]:
        pass

    @abstractmethod
    def get_project(self) -> str:
        pass


class GCS(Storage):
    credentials: Optional[Credentials]
    project: Optional[str]
    client: Client

    def __init__(
        self, credentials: Optional[Credentials] = None, project: Optional[str] = None
    ):
        self.credentials = credentials
        self.project = project
        self.build_client()

    def set_credentials(self, credentials: Credentials) -> None:
        self.credentials = credentials
        self.build_client()

    def set_project(self, project: str) -> None:
        self.project = project
        self.build_client()

    def get_project(self) -> str:
        if self.project is not None:
            return self.project
        else:
            return str(self.client.project)

    def build_client(self) -> None:
        if self.project is not None:
            self.client = Client(credentials=self.credentials, project=self.project)
        else:
            self.client = Client(credentials=self.credentials)

    def list_buckets(self) -> List[Dir]:
        buckets = self.client.list_buckets()
        return [Dir(bucket.name) for bucket in buckets]

    def list_prefix(self, bucket_name: str, prefix: str) -> List[Dir | Blob]:
        blobs = self.client.bucket(bucket_name).list_blobs(delimiter="/", prefix=prefix)
        blob_list = list(blobs)

        result = [Dir(subdir) for subdir in blobs.prefixes] + [
            Blob(blob.name, blob.size, blob.updated) for blob in blob_list
        ]

        sorted_result = sorted(result, key=lambda x: x.name)

        return sorted_result
