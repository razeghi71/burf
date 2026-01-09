from typing import List, Optional

import boto3
from botocore.exceptions import ClientError

from burf.storage.ds import BucketWithPrefix
from burf.storage.storage import Storage


class S3(Storage):
    def __init__(self, profile: Optional[str] = None):
        self.profile = profile
        self.session = boto3.Session(profile_name=profile)
        self.client = self.session.client("s3")

    @property
    def scheme(self) -> str:
        return "s3"

    def get_project(self) -> str:
        if self.profile:
            return self.profile
        return "default"

    def list_buckets(self) -> List[BucketWithPrefix]:
        try:
            response = self.client.list_buckets()
            return [
                BucketWithPrefix(bucket["Name"], [])
                for bucket in response.get("Buckets", [])
            ]
        except ClientError:
            # Handle error appropriately, maybe re-raise or return empty list
            return []

    def list_prefix(self, uri: BucketWithPrefix) -> List[BucketWithPrefix]:
        # S3 expects prefix to end with / if we want to list contents of a directory
        prefix = uri.full_prefix
        
        try:
            paginator = self.client.get_paginator("list_objects_v2")
            page_iterator = paginator.paginate(
                Bucket=uri.bucket_name,
                Prefix=prefix,
                Delimiter="/",
            )

            prefixes = []
            blobs = []

            for page in page_iterator:
                # CommonPrefixes represent subdirectories
                for p in page.get("CommonPrefixes", []):
                    # p['Prefix'] is the full path including current prefix
                    # We want just the subdirectory name relative to current prefix
                    # But BucketWithPrefix.from_full_prefix handles the parsing
                    prefixes.append(p["Prefix"])

                # Contents represent files
                for obj in page.get("Contents", []):
                    # Skip if it is the current directory itself (sometimes S3 returns it)
                    if obj["Key"] == prefix:
                        continue
                        
                    blobs.append(
                        BucketWithPrefix.from_full_prefix(
                            bucket_name=uri.bucket_name,
                            full_prefix=obj["Key"],
                            is_blob=True,
                            size=obj["Size"],
                            updated_at=obj["LastModified"],
                        )
                    )

            # Convert prefixes to BucketWithPrefix
            # We need to extract the subdirectory name. 
            # BucketWithPrefix.from_full_prefix handles 'a/b/c/' correctly.
            dir_list = [
                BucketWithPrefix.from_full_prefix(
                    bucket_name=uri.bucket_name,
                    full_prefix=p,
                )
                for p in prefixes
            ]

            return sorted(dir_list + blobs, key=lambda x: x.full_prefix)

        except ClientError:
             # Handle access denied or other errors
            return []

    def list_all_blobs(self, uri: BucketWithPrefix) -> List[BucketWithPrefix]:
        try:
            paginator = self.client.get_paginator("list_objects_v2")
            page_iterator = paginator.paginate(
                Bucket=uri.bucket_name,
                Prefix=uri.full_prefix
            )

            blobs = []
            for page in page_iterator:
                for obj in page.get("Contents", []):
                     blobs.append(
                        BucketWithPrefix.from_full_prefix(
                            bucket_name=uri.bucket_name,
                            full_prefix=obj["Key"],
                            is_blob=True,
                            size=obj["Size"],
                            updated_at=obj["LastModified"],
                        )
                    )
            return blobs
        except ClientError:
            return []

    def download_to_filename(self, uri: BucketWithPrefix, dest: str) -> None:
        try:
            self.client.download_file(uri.bucket_name, uri.full_prefix, dest)
        except ClientError:
            pass

    def delete_blob(self, uri: BucketWithPrefix) -> None:
        if not uri.bucket_name or not uri.is_blob:
            raise ValueError("delete_blob expects a blob URI with a bucket name")

        try:
            self.client.delete_object(Bucket=uri.bucket_name, Key=uri.full_prefix)
        except ClientError:
            pass
