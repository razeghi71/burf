from typing import List, Optional

from google.api_core.exceptions import NotFound
from google.auth.credentials import Credentials
from google.cloud.storage import Client  # type: ignore

from burf.storage.ds import CloudPath
from burf.storage.storage import Storage


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

    def list_buckets(self) -> List[CloudPath]:
        buckets = self.client.list_buckets()
        return [CloudPath(self.scheme, bucket.name, []) for bucket in buckets]

    def list_prefix(self, uri: CloudPath) -> List[CloudPath]:
        blobs = self.client.bucket(uri.bucket_name).list_blobs(
            delimiter="/", prefix=uri.full_prefix
        )

        blob_list = [blob for blob in list(blobs) if blob.name != uri.full_prefix]

        return sorted(
            [
                CloudPath.from_full_prefix(
                    scheme=self.scheme,
                    bucket_name=uri.bucket_name,
                    full_prefix=subdir,
                )
                for subdir in blobs.prefixes
            ]
            + [
                CloudPath.from_full_prefix(
                    scheme=self.scheme,
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

    def list_all_blobs(self, uri: CloudPath) -> List[CloudPath]:
        blobs = self.client.bucket(uri.bucket_name).list_blobs(prefix=uri.full_prefix)
        return [
            CloudPath.from_full_prefix(
                scheme=self.scheme,
                bucket_name=blob.bucket.name,
                full_prefix=blob.name,
                is_blob=True,
                size=blob.size,
                updated_at=blob.updated,
            )
            for blob in blobs
        ]

    def download_to_filename(self, uri: CloudPath, dest: str) -> None:
        blob = self.client.bucket(uri.bucket_name).blob(uri.full_prefix)

        if blob.exists():
            blob.download_to_filename(dest)

    def delete_blob(self, uri: CloudPath) -> None:
        if not uri.bucket_name or not uri.is_blob:
            raise ValueError("delete_blob expects a blob URI with a bucket name")

        blob = self.client.bucket(uri.bucket_name).blob(uri.full_prefix)
        try:
            blob.delete()
        except NotFound:
            # Best-effort: object may have been removed already.
            return
