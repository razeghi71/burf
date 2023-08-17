import math
import re


def human_readable_bytes(size_in_bytes: int) -> str:
    if size_in_bytes == 0:
        return "0B"

    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    idx = int(math.floor(math.log(size_in_bytes, 1024)))
    power = math.pow(1024, idx)
    size = round(size_in_bytes / power, 2)

    return f"{size} {size_name[idx]}"


def get_gcs_bucket_and_subdir(gcs_uri: str) -> tuple[str, str]:
    match = re.match(r"(gs://)?(?P<bucket>[^/]+)/*(?P<subdir>.*)", gcs_uri)
    if match:
        bucket = match.group("bucket")
        subdir = match.group("subdir")
    else:
        bucket = gcs_uri
        subdir = ""

    return bucket, subdir
