from enum import Enum


class StorageScheme(str, Enum):
    GCS = "gs"
    S3 = "s3"
