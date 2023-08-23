from __future__ import annotations


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
