from __future__ import annotations

from datetime import datetime
from typing import Optional, Sequence


class CloudPath:
    def __init__(
        self,
        scheme: str,
        bucket_name: str,
        prefixes: Sequence[str],
        is_blob: bool = False,
        size: Optional[int] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.scheme = scheme
        self.bucket_name = bucket_name
        self.is_blob = is_blob
        self.size = size
        self.updated_at = updated_at
        if isinstance(prefixes, str):
            raise TypeError(
                "CloudPath(prefixes=...) must be a sequence of path parts, not a string"
            )
        # Copy into a list so we have a stable internal representation.
        self.prefixes = list(prefixes)

    @staticmethod
    def full_prefix_to_list(full_prefix: str) -> list[str]:
        return list(filter(lambda x: x.strip() != "", full_prefix.split("/")))

    @classmethod
    def from_full_prefix(
        cls,
        scheme: str,
        bucket_name: str,
        full_prefix: str,
        *,
        is_blob: bool = False,
        size: Optional[int] = None,
        updated_at: Optional[datetime] = None,
    ) -> CloudPath:
        """Create from a single string prefix like 'a/b/c/' or 'a/b.txt'."""
        return cls(
            scheme=scheme,
            bucket_name=bucket_name,
            prefixes=cls.full_prefix_to_list(full_prefix),
            is_blob=is_blob,
            size=size,
            updated_at=updated_at,
        )

    @property
    def full_prefix(self) -> str:
        joined = "/".join(self.prefixes)
        if joined == "":
            return ""
        if not self.is_blob:
            return joined + "/"
        return joined

    @property
    def full_path(self) -> str:
        return self.bucket_name + "/" + self.full_prefix

    @property
    def is_bucket(self) -> bool:
        return len(self.prefixes) == 0

    def parent(self) -> CloudPath:
        if self.bucket_name == "":
            return self
        if len(self.prefixes) == 0:
            return CloudPath(self.scheme, "", [])
        else:
            return CloudPath(self.scheme, self.bucket_name, self.prefixes[:-1])

    def get_last_part_of_address(self) -> str:
        if self.is_bucket:
            return self.bucket_name
        return self.prefixes[-1]

    def __str__(self) -> str:
        if not self.bucket_name:
            return f"list of buckets ({self.scheme})"
        return f"{self.scheme}://{self.full_path}"

    def __hash__(self) -> int:
        return hash((self.scheme, self.full_path))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CloudPath):
            return False
        return (
            self.scheme == other.scheme
            and self.full_path == other.full_path
            and self.is_blob == other.is_blob
        )
