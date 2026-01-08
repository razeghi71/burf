from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

from burf.storage.ds import BucketWithPrefix
from burf.storage.storage import ListingCancelledError, Storage
from burf.util import RecentDict


Listing = list[BucketWithPrefix]
OnSuccess = Callable[[Listing], None]
OnError = Callable[[BaseException], None]


def _listing_signature(elems: Listing) -> tuple[tuple[str, bool, int | None, str | None], ...]:
    """Build a signature that detects listing changes.

    `BucketWithPrefix.__eq__` intentionally ignores metadata like size/updated_at.
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
    """Cache + refresh bucket/prefix listings for a Storage.

    This service is intentionally UI-agnostic:
    - it never touches Textual
    - it never assumes a main thread
    - it reports async results via callbacks
    """

    def __init__(self, storage: Storage, *, cache_size: int = 25) -> None:
        self._storage = storage
        self._cache: RecentDict[BucketWithPrefix, ListingCacheEntry] = RecentDict(cache_size)
        self._in_flight: set[BucketWithPrefix] = set()
        self._cancel_events: dict[BucketWithPrefix, threading.Event] = {}

    def clear(self) -> None:
        self._cache.clear()
        self.cancel_all()
        self._in_flight.clear()

    def get_cached(self, uri: BucketWithPrefix) -> Optional[Listing]:
        entry = self._cache.get(uri)
        return entry.elems if entry is not None else None

    def fetch_and_cache(
        self, uri: BucketWithPrefix, *, cancel_event: threading.Event | None = None
    ) -> Listing:
        if cancel_event is not None and cancel_event.is_set():
            raise ListingCancelledError()
        if not uri.bucket_name:
            elems = self._storage.list_buckets(cancel_event=cancel_event)
        else:
            elems = self._storage.list_prefix(uri=uri, cancel_event=cancel_event)
        self._cache[uri] = ListingCacheEntry(
            elems=elems,
            signature=_listing_signature(elems),
            fetched_at=datetime.now(timezone.utc),
        )
        return elems

    def cancel(self, uri: BucketWithPrefix) -> None:
        """Request cooperative cancellation of any in-flight work for a uri."""
        ev = self._cancel_events.pop(uri, None)
        if ev is not None:
            ev.set()
        # Allow a new refresh to start even if the old worker hasn't exited yet.
        self._in_flight.discard(uri)

    def cancel_all(self) -> None:
        """Request cooperative cancellation of all in-flight listing work."""
        for uri, ev in list(self._cancel_events.items()):
            ev.set()
            self._cancel_events.pop(uri, None)
            self._in_flight.discard(uri)

    def refresh_async(
        self,
        uri: BucketWithPrefix,
        *,
        on_success: OnSuccess,
        on_error: Optional[OnError] = None,
    ) -> None:
        """Refresh a listing in the background.

        - If another refresh for the same uri is in-flight, this is a no-op.
        - `on_success` is only called if the new listing differs from the cached one.
        - Callbacks are invoked on the worker thread.
        """
        if uri in self._in_flight:
            return
        self._in_flight.add(uri)
        cancel_event = threading.Event()
        self._cancel_events[uri] = cancel_event

        def _worker() -> None:
            try:
                cached = self._cache.get(uri)
                cached_sig = cached.signature if cached is not None else None

                refreshed = self.fetch_and_cache(uri, cancel_event=cancel_event)
                refreshed_sig = _listing_signature(refreshed)

                # Only notify if something actually changed.
                if cached_sig != refreshed_sig:
                    on_success(refreshed)
            except ListingCancelledError:
                # Cancellation is a normal control flow signal; don't treat as an error.
                return
            except BaseException as e:
                if on_error is not None:
                    on_error(e)
            finally:
                self._in_flight.discard(uri)
                # Only remove if this worker "owns" the current cancel event.
                if self._cancel_events.get(uri) is cancel_event:
                    self._cancel_events.pop(uri, None)

        threading.Thread(target=_worker, daemon=True).start()

