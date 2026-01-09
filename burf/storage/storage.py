from abc import ABC, abstractmethod
from typing import List, Optional

from google.api_core.exceptions import NotFound
from google.auth.credentials import Credentials
from google.cloud.storage import Client  # type: ignore

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

    @property
    def scheme(self) -> str:
        return "gs"

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

    def list_buckets(self) -> List[BucketWithPrefix]:
        buckets = self.client.list_buckets()
        return [BucketWithPrefix(bucket.name, []) for bucket in buckets]

    def list_prefix(self, uri: BucketWithPrefix) -> List[BucketWithPrefix]:
        blobs = self.client.bucket(uri.bucket_name).list_blobs(
            delimiter="/", prefix=uri.full_prefix
        )

        blob_list = [blob for blob in list(blobs) if blob.name != uri.full_prefix]

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

    def list_all_blobs(self, uri: BucketWithPrefix) -> List[BucketWithPrefix]:
        blobs = self.client.bucket(uri.bucket_name).list_blobs(prefix=uri.full_prefix)
        return [
            BucketWithPrefix.from_full_prefix(
                bucket_name=blob.bucket.name,
                full_prefix=blob.name,
                is_blob=True,
                size=blob.size,
                updated_at=blob.updated,
            )
            for blob in blobs
        ]

    def download_to_filename(self, uri: BucketWithPrefix, dest: str) -> None:
        blob = self.client.bucket(uri.bucket_name).blob(uri.full_prefix)

        if blob.exists():
            blob.download_to_filename(dest)

    def delete_blob(self, uri: BucketWithPrefix) -> None:
        if not uri.bucket_name or not uri.is_blob:
            raise ValueError("delete_blob expects a blob URI with a bucket name")

        blob = self.client.bucket(uri.bucket_name).blob(uri.full_prefix)
        try:
            blob.delete()
        except NotFound:
            # Best-effort: object may have been removed already.
            return
