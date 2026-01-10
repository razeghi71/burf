import math
import re
from collections import OrderedDict
from typing import Any, Generic, TypeVar, Tuple

from burf.scheme import StorageScheme
from burf.storage.ds import CloudPath


def human_readable_bytes(size_in_bytes: int) -> str:
    if size_in_bytes == 0:
        return "0B"

    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    idx = int(math.floor(math.log(size_in_bytes, 1024)))
    power = math.pow(1024, idx)
    size = round(size_in_bytes / power, 2)

    return f"{size} {size_name[idx]}"


def parse_uri(uri: str) -> Tuple[StorageScheme, CloudPath]:
    """
    Parses a URI and returns the StorageScheme and the CloudPath object.
    Defaults to gs if no scheme is provided or if scheme is not s3.
    """
    scheme_enum = StorageScheme.GCS  # Default
    uri_path = uri

    if uri.startswith("s3://"):
        scheme_enum = StorageScheme.S3
        uri_path = uri[5:]
    elif uri.startswith("gs://"):
        scheme_enum = StorageScheme.GCS
        uri_path = uri[5:]
    # If no scheme provided, we stick to default (gs) for backward compatibility,
    # but we can check if StorageScheme(uri) might work if we supported bare schemes?
    # No, keep logic simple.

    # Regex to capture bucket and prefix
    match = re.match(r"^(?P<bucket>[^/]+)/*(?P<prefix>.*)", uri_path)
    
    if match:
        bucket = match.group("bucket")
        prefix = match.group("prefix")
    else:
        # If it doesn't match the pattern (e.g. empty string or just slash), handle gracefully
        # If uri_path is empty, it means we are at the root (listing buckets)
        if not uri_path:
             return scheme_enum, CloudPath(scheme_enum, "", [])
        bucket = uri_path
        prefix = ""

    return scheme_enum, CloudPath.from_full_prefix(scheme_enum, bucket, prefix)


K = TypeVar("K")
V = TypeVar("V")


class RecentDict(OrderedDict[K, V], Generic[K, V]):
    def __init__(self, max_elements: int, *args: Any, **kwargs: Any) -> None:
        self.max_elements = max_elements
        super().__init__(*args, **kwargs)

    def __setitem__(self, key: K, value: V) -> None:
        if len(self) >= self.max_elements:
            self.popitem(last=False)
        super().__setitem__(key, value)
