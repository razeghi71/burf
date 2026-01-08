from abc import ABC, abstractmethod
import threading
from typing import List, Optional

from google.auth.credentials import Credentials
from google.cloud.storage import Client  # type: ignore

from burf.storage.ds import BucketWithPrefix


class ListingCancelledError(Exception):
    """Raised when a listing operation is cancelled cooperatively."""


class Storage(ABC):
    @abstractmethod
    def list_buckets(
        self, cancel_event: threading.Event | None = None
    ) -> List[BucketWithPrefix]:
        pass

    @abstractmethod
    def list_prefix(
        self, uri: BucketWithPrefix, cancel_event: threading.Event | None = None
    ) -> List[BucketWithPrefix]:
        pass

    @abstractmethod
    def list_all_blobs(
        self, uri: BucketWithPrefix, cancel_event: threading.Event | None = None
    ) -> List[BucketWithPrefix]:
        pass

    @abstractmethod
    def get_project(self) -> str:
        pass

    @abstractmethod
    def download_to_filename(self, uri: BucketWithPrefix, dest: str) -> None:
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

    def list_buckets(
        self, cancel_event: threading.Event | None = None
    ) -> List[BucketWithPrefix]:
        buckets = self.client.list_buckets()
        out: list[BucketWithPrefix] = []
        for bucket in buckets:
            if cancel_event is not None and cancel_event.is_set():
                raise ListingCancelledError()
            out.append(BucketWithPrefix(bucket.name, []))
        return out

    def list_prefix(
        self, uri: BucketWithPrefix, cancel_event: threading.Event | None = None
    ) -> List[BucketWithPrefix]:
        if cancel_event is not None and cancel_event.is_set():
            raise ListingCancelledError()

        blobs = self.client.bucket(uri.bucket_name).list_blobs(
            delimiter="/", prefix=uri.full_prefix
        )

        blob_list = []
        for blob in blobs:
            if cancel_event is not None and cancel_event.is_set():
                raise ListingCancelledError()
            if blob.name != uri.full_prefix:
                blob_list.append(blob)

        return sorted(
            [
                BucketWithPrefix.from_full_prefix(
                    bucket_name=uri.bucket_name,
                    full_prefix=subdir,
                )
                for subdir in blobs.prefixes
            ]
            + [
                BucketWithPrefix.from_full_prefix(
                    bucket_name=blob.bucket.name,
                    full_prefix=blob.name,
                    is_blob=True,
                    size=blob.size,
                    updated_at=blob.updated,
                )
                for blob in blob_list
            ],
            key=lambda x: x.full_prefix,
        )

    def list_all_blobs(
        self, uri: BucketWithPrefix, cancel_event: threading.Event | None = None
    ) -> List[BucketWithPrefix]:
        if cancel_event is not None and cancel_event.is_set():
            raise ListingCancelledError()
        blobs = self.client.bucket(uri.bucket_name).list_blobs(prefix=uri.full_prefix)
        out: list[BucketWithPrefix] = []
        for blob in blobs:
            if cancel_event is not None and cancel_event.is_set():
                raise ListingCancelledError()
            out.append(
                BucketWithPrefix.from_full_prefix(
                    bucket_name=blob.bucket.name,
                    full_prefix=blob.name,
                    is_blob=True,
                    size=blob.size,
                    updated_at=blob.updated,
                )
            )
        return out

    def download_to_filename(self, uri: BucketWithPrefix, dest: str) -> None:
        blob = self.client.bucket(uri.bucket_name).blob(uri.full_prefix)

        if blob.exists():
            blob.download_to_filename(dest)
