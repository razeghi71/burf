import math
import re
from collections import OrderedDict
from typing import Any, Generic, TypeVar, Tuple

from burf.storage.ds import CloudPath


def human_readable_bytes(size_in_bytes: int) -> str:
    if size_in_bytes == 0:
        return "0B"

    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    idx = int(math.floor(math.log(size_in_bytes, 1024)))
    power = math.pow(1024, idx)
    size = round(size_in_bytes / power, 2)

    return f"{size} {size_name[idx]}"


def parse_uri(uri: str) -> Tuple[str, CloudPath]:
    """
    Parses a URI and returns the scheme (gs or s3) and the CloudPath object.
    Defaults to gs if no scheme is provided or if scheme is not s3.
    """
    if uri.startswith("s3://"):
        scheme = "s3"
        # Remove s3://
        uri_path = uri[5:]
    elif uri.startswith("gs://"):
        scheme = "gs"
        # Remove gs://
        uri_path = uri[5:]
    else:
        # Default to gs if no scheme provided, for backward compatibility
        scheme = "gs"
        uri_path = uri

    # Regex to capture bucket and prefix
    # Pattern: ^(?P<bucket>[^/]+)/*(?P<prefix>.*)
    # This assumes uri_path does not start with scheme
    match = re.match(r"^(?P<bucket>[^/]+)/*(?P<prefix>.*)", uri_path)
    
    if match:
        bucket = match.group("bucket")
        prefix = match.group("prefix")
    else:
        # If it doesn't match the pattern (e.g. empty string or just slash), handle gracefully
        # If uri_path is empty, it means we are at the root (listing buckets)
        if not uri_path:
             return scheme, CloudPath(scheme, "", [])
        bucket = uri_path
        prefix = ""

    return scheme, CloudPath.from_full_prefix(scheme, bucket, prefix)


def get_gcs_bucket_and_prefix(gcs_uri: str) -> CloudPath:
    """Deprecated: Use parse_uri instead."""
    _, cloud_path = parse_uri(gcs_uri)
    return cloud_path


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
