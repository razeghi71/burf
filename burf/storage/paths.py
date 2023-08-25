from abc import ABC, abstractmethod

from datetime import datetime


class Path(ABC):
    @abstractmethod
    def uri(self) -> str:
        pass


class Bucket(Path):
    def __init__(self, bucket: str) -> None:
        self.bucket = bucket

    def uri(self) -> str:
        return self.bucket

    __match_args__ = "bucket"


class Prefix(Path):
    def __init__(self, name: str, bucket: str) -> None:
        self.name = name
        self.bucket = bucket

    def uri(self) -> str:
        return self.bucket + "/" + self.name

    __match_args__ = ("name", "bucket")


class Blob(Path):
    def __init__(self, name: str, bucket: str, size: int, time_updated: datetime):
        self.name = name
        self.bucket = bucket
        self.size = size
        self.time_updated = time_updated

    def uri(self) -> str:
        return self.bucket + "/" + self.name

    __match_args__ = ("name", "bucket", "size", "time_updated")
