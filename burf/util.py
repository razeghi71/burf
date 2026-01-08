import math
import re
from collections import OrderedDict
from typing import Any, Generic, TypeVar

from burf.storage.ds import BucketWithPrefix


def human_readable_bytes(size_in_bytes: int) -> str:
    if size_in_bytes == 0:
        return "0B"

    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    idx = int(math.floor(math.log(size_in_bytes, 1024)))
    power = math.pow(1024, idx)
    size = round(size_in_bytes / power, 2)

    return f"{size} {size_name[idx]}"


def get_gcs_bucket_and_prefix(gcs_uri: str) -> BucketWithPrefix:
    match = re.match(r"(gs://)?(?P<bucket>[^/]+)/*(?P<prefix>.*)", gcs_uri)
    if match:
        bucket = match.group("bucket")
        prefix = match.group("prefix")
    else:
        bucket = gcs_uri
        prefix = ""

    return BucketWithPrefix.from_full_prefix(bucket, prefix)


K = TypeVar("K")
V = TypeVar("V")


class RecentDict(OrderedDict[K, V], Generic[K, V]):
    def __init__(self, max_elements: int, *args: Any, **kwargs: Any) -> None:
        self.max_elements = max_elements
        super().__init__(*args, **kwargs)

    def __setitem__(self, key: K, value: V) -> None:
        if key not in self and len(self) >= self.max_elements:
            self.popitem(last=False)
        super().__setitem__(key, value)
