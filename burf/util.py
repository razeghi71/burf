import math
import re
from burf.storage import BucketWithPrefix
from collections import OrderedDict


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

    return BucketWithPrefix(bucket, prefix)


class RecentDict(OrderedDict):
    def __init__(self, max_elements, *args, **kwargs):
        self.max_elements = max_elements
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        if len(self) >= self.max_elements:
            self.popitem(last=False)
        super().__setitem__(key, value)
