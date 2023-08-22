from __future__ import annotations

from abc import ABC, abstractmethod
from google.cloud.storage import Client  # type: ignore
from google.auth.credentials import Credentials
from typing import List, Optional

from datetime import datetime


class Dir:
    def __init__(self, name: str):
        self.name = name

    __match_args__ = ("name",)


class Blob:
    def __init__(self, name: str, size: int, time_created: datetime):
        self.name = name
        self.size = size
        self.time_created = time_created

    __match_args__ = ("name", "size", "time_created")


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


class BucketWithPrefix:
    def __init__(self, bucket_name: str, prefix: str) -> None:
        self._bucket_name = bucket_name
        self._prefix = prefix

    @property
    def bucket_name(self) -> str:
        return self._bucket_name

    @bucket_name.setter
    def bucket_name(self, bucket_name: str) -> None:
        self._bucket_name = bucket_name

    @property
    def prefix(self) -> str:
        return self._prefix

    @prefix.setter
    def prefix(self, prefix: str) -> None:
        self._prefix = prefix

    def __str__(self) -> str:
        return self.bucket_name + "/" + self.prefix

    def parent(self) -> BucketWithPrefix:
        if self.bucket_name == "":
            return self
        if self.prefix == "":
            return BucketWithPrefix("", "")
        else:
            if self.prefix.count("/") == 1:
                new_prefix = ""
            else:
                new_prefix = "/".join(self.prefix.split("/")[:-2]) + "/"
            return BucketWithPrefix(self.bucket_name, new_prefix)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, BucketWithPrefix):
            return other.bucket_name == self.bucket_name and other.prefix == self.prefix
        return False

    def __hash__(self) -> int:
        return hash((self.bucket_name, self.prefix))


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
