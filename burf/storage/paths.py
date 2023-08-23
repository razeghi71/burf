from datetime import datetime


class Dir:
    def __init__(self, name: str):
        self.name = name

    __match_args__ = ("name",)


class Blob:
    def __init__(self, name: str, size: int, time_created: datetime):
        self.name = name
        self.size = size
        self.time_created = time_created

    __match_args__ = ("name", "size", "time_created")
