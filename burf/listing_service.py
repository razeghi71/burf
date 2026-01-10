from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

from burf.storage.ds import CloudPath
from burf.storage.storage import Storage
from burf.util import RecentDict


Listing = list[CloudPath]
OnSuccess = Callable[[Listing], None]
OnError = Callable[[BaseException], None]


def _listing_signature(elems: Listing) -> tuple[tuple[str, bool, int | None, str | None], ...]:
    """Build a signature that detects listing changes.

    `CloudPath.__eq__` intentionally ignores metadata like size/updated_at.
    For refresh-diffing we include that metadata so UI updates when it changes.
    """
    sig: list[tuple[str, bool, int | None, str | None]] = []
    for e in elems:
        updated = e.updated_at
        updated_s = (
            updated.astimezone(timezone.utc).isoformat() if updated is not None else None
        )
        sig.append((e.full_path, e.is_blob, e.size, updated_s))
    return tuple(sig)


@dataclass(frozen=True)
class ListingCacheEntry:
    elems: Listing
    signature: tuple[tuple[str, bool, int | None, str | None], ...]
    fetched_at: datetime


class ListingService:
    def __init__(self, storage: Storage, *, cache_size: int = 25) -> None:
        self._storage = storage
        self._cache: RecentDict[CloudPath, ListingCacheEntry] = RecentDict(cache_size)
        self._lock = threading.Lock()
        self._generation: dict[CloudPath, int] = {}

    def clear(self) -> None:
        self._cache.clear()
        with self._lock:
            self._generation.clear()

    def get_cached(self, uri: CloudPath) -> Optional[Listing]:
        # We must acquire lock here?
        # RecentDict is generally not thread safe for read/write mix, but here we just read.
        # But if _worker is writing to it...
        # RecentDict inherits from OrderedDict.
        with self._lock:
            entry = self._cache.get(uri)
        return entry.elems if entry is not None else None

    def _fetch(self, uri: CloudPath) -> Listing:
        if not uri.bucket_name:
            return self._storage.list_buckets()
        else:
            return self._storage.list_prefix(uri=uri)

    def refresh_async(
        self,
        uri: CloudPath,
        *,
        on_success: OnSuccess,
        on_error: Optional[OnError] = None,
    ) -> None:
        """Refresh a listing in the background.

        - `on_success` is only called if the new listing differs from the cached one.
        - Callbacks are invoked on the worker thread.
        """
        with self._lock:
            gen = self._generation.get(uri, 0) + 1
            self._generation[uri] = gen
            entry = self._cache.get(uri)
            cached_sig = entry.signature if entry is not None else None

        def _worker() -> None:
            try:
                refreshed = self._fetch(uri)
                refreshed_sig = _listing_signature(refreshed)

                with self._lock:
                    if self._generation.get(uri, 0) != gen:
                        return
                    self._cache[uri] = ListingCacheEntry(
                        elems=refreshed,
                        signature=refreshed_sig,
                        fetched_at=datetime.now(timezone.utc),
                    )
                    should_notify = cached_sig != refreshed_sig

                if should_notify:
                    on_success(refreshed)
            except BaseException as e:
                if on_error is not None:
                    on_error(e)

        threading.Thread(target=_worker, daemon=True).start()
