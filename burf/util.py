import math


def human_readable_bytes(size_in_bytes: int) -> str:
    if size_in_bytes == 0:
        return "0B"

    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    idx = int(math.floor(math.log(size_in_bytes, 1024)))
    power = math.pow(1024, idx)
    size = round(size_in_bytes / power, 2)

    return f"{size} {size_name[idx]}"
