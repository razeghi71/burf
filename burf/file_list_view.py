from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from google.api_core.exceptions import BadRequest, Forbidden
from google.auth.exceptions import RefreshError
from textual.binding import Binding
from textual.color import Color
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Label, ListItem, ListView

from burf.storage.ds import BucketWithPrefix
from burf.storage.storage import Storage
from burf.util import RecentDict, human_readable_bytes


@dataclass(frozen=True)
class _ListingCacheEntry:
    elems: List[BucketWithPrefix]
    fetched_at: datetime


class FileListView(ListView):
    class AccessForbidden(Message, bubble=True):
        path: str
        file_list_view: FileListView

        def __init__(self, file_list_view: FileListView, path: str) -> None:
            super().__init__()
            self.file_list_view = file_list_view
            self.path = path

        @property
        def control(self) -> FileListView:
            return self.file_list_view

    class InvalidProject(Message, bubble=True):
        project: str
        file_list_view: FileListView

        def __init__(self, file_list_view: FileListView, project: str) -> None:
            super().__init__()
            self.file_list_view = file_list_view
            self.project = project

        @property
        def control(self) -> FileListView:
            return self.file_list_view

    BINDINGS = [
        Binding("enter", "select_cursor", "Select"),
        Binding("backspace", "back", "Parent"),
        Binding("/", "search", "search"),
    ]

    showing_elems: reactive[List[BucketWithPrefix]] = reactive([])
    position_cache: RecentDict[BucketWithPrefix, int] = RecentDict(10)

    def __init__(
        self,
        storage: Storage,
        uri: BucketWithPrefix = BucketWithPrefix("", []),
        *children: ListItem,
        initial_index: int | None = 0,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(
            *children,
            initial_index=initial_index,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )

        self._storage = storage
        self._uri = uri
        self._listing_cache: RecentDict[BucketWithPrefix, _ListingCacheEntry] = RecentDict(
            25
        )
        self._refresh_token = 0
        self._in_flight_refreshes: set[BucketWithPrefix] = set()
        self.refresh_contents()

    @property
    def storage(self) -> Storage:
        return self._storage

    @property
    def uri(self) -> BucketWithPrefix:
        return self._uri

    @uri.setter
    def uri(self, new_uri: BucketWithPrefix) -> None:
        self.position_cache[self.uri] = self.index or 0
        self._uri = new_uri

    def watch_showing_elems(
        self, _: List[BucketWithPrefix], new_showing_elems: List[BucketWithPrefix]
    ) -> None:
        self.clear()
        self.index = 0

        base_prefix = self.uri.full_prefix if self.uri.bucket_name != "" else ""

        for showing_elem in new_showing_elems:
            row = []
            if showing_elem.is_bucket:
                display_name = showing_elem.bucket_name
                pretty_name = Label(f"📦 {display_name}")
            elif not showing_elem.is_blob:
                display_name = showing_elem.full_prefix
                if base_prefix and display_name.startswith(base_prefix):
                    display_name = display_name[len(base_prefix) :]
                pretty_name = Label(f"📂 {display_name}")
            else:
                display_name = showing_elem.full_prefix
                if base_prefix and display_name.startswith(base_prefix):
                    display_name = display_name[len(base_prefix) :]
                pretty_name = Label(f"📒 {display_name}")

            row.append(pretty_name)
            if showing_elem.is_blob:
                pretty_name.styles.width = "65%"
                bg_color = self.background_colors[0]

                if showing_elem.updated_at is not None:
                    time_label = Label(
                        showing_elem.updated_at.strftime("%Y-%m-%d %H:%M:%S.%f")
                    )
                else:
                    time_label = Label("")
                time_label.styles.width = "25%"
                time_label.styles.background = Color.lighten(bg_color, 0.2)

                if showing_elem.size is not None:
                    size_label = Label(human_readable_bytes(showing_elem.size))
                else:
                    size_label = Label("")
                size_label.styles.width = "10%"
                size_label.styles.background = Color.lighten(bg_color, 0.1)

                row.append(time_label)
                row.append(size_label)

            self.append(
                ListItem(
                    Horizontal(
                        *row,
                    ),
                    name=showing_elem.bucket_name
                    if showing_elem.is_bucket
                    else showing_elem.full_prefix,
                )
            )

        if self.uri in self.position_cache:
            self.index = self.position_cache[self.uri]

    def action_back(self) -> None:
        self.uri = self.uri.parent()
        self.refresh_contents()

    def on_list_view_selected(self, selected: ListView.Selected) -> None:
        selected_name = selected.item.name or ""
        if not selected_name:
            return

        if self.uri.bucket_name != "" and selected_name[-1] != "/":
            return
        elif self.uri.bucket_name == "":
            self.uri = BucketWithPrefix(selected_name, [])
        else:
            self.uri = BucketWithPrefix.from_full_prefix(
                self.uri.bucket_name, selected_name
            )

        self.refresh_contents()

    @staticmethod
    def _listing_signature(elems: List[BucketWithPrefix]) -> tuple[tuple[str, bool, int | None, str | None], ...]:
        """Signature that includes metadata so refresh detects updates.

        We include size and updated_at since `BucketWithPrefix.__eq__` intentionally
        ignores them.
        """
        sig: list[tuple[str, bool, int | None, str | None]] = []
        for e in elems:
            updated = e.updated_at
            updated_s = (
                updated.astimezone(timezone.utc).isoformat()
                if updated is not None
                else None
            )
            sig.append((e.full_path, e.is_blob, e.size, updated_s))
        return tuple(sig)

    def _start_background_refresh(self, uri_snapshot: BucketWithPrefix, path: str, token: int) -> None:
        # Avoid piling up refresh threads for the same URI.
        if uri_snapshot in self._in_flight_refreshes:
            return
        self._in_flight_refreshes.add(uri_snapshot)

        def _worker() -> None:
            try:
                if not uri_snapshot.bucket_name:
                    refreshed = self.storage.list_buckets()
                else:
                    refreshed = self.storage.list_prefix(uri=uri_snapshot)

                refreshed_sig = self._listing_signature(refreshed)

                def _apply() -> None:
                    try:
                        # Drop results if the user navigated elsewhere since we started.
                        if token != self._refresh_token or self.uri != uri_snapshot:
                            return

                        cached = self._listing_cache.get(uri_snapshot)
                        cached_sig = (
                            self._listing_signature(cached.elems) if cached is not None else None
                        )

                        if cached_sig != refreshed_sig:
                            self._listing_cache[uri_snapshot] = _ListingCacheEntry(
                                elems=refreshed,
                                fetched_at=datetime.now(timezone.utc),
                            )
                            self.showing_elems = refreshed

                        self.app.title = path
                    finally:
                        self._in_flight_refreshes.discard(uri_snapshot)

                self.app.call_from_thread(_apply)

            except Forbidden:
                self.app.call_from_thread(
                    self.app.post_message, self.AccessForbidden(self, path)
                )
                self._in_flight_refreshes.discard(uri_snapshot)
            except RefreshError:
                self.app.call_from_thread(
                    self.app.post_message, self.AccessForbidden(self, path)
                )
                self._in_flight_refreshes.discard(uri_snapshot)
            except BadRequest as e:
                errors = getattr(e, "errors", None) or []
                for error in errors:
                    message = ""
                    if isinstance(error, dict):
                        message = str(error.get("message", ""))
                    if "Invalid project" in message:
                        self.app.call_from_thread(
                            self.app.post_message,
                            self.InvalidProject(self, self.storage.get_project()),
                        )
                        break
                self._in_flight_refreshes.discard(uri_snapshot)
            except Exception:
                # Best effort: keep cached contents on unexpected background errors.
                self._in_flight_refreshes.discard(uri_snapshot)

        threading.Thread(target=_worker, daemon=True).start()

    def refresh_contents(self) -> bool:
        # Increment token so any prior background refresh won't clobber this view.
        self._refresh_token += 1
        token = self._refresh_token

        uri_snapshot = self.uri

        if not uri_snapshot.bucket_name:
            path = f"list of buckets in project: ({self.storage.get_project()})"
        else:
            path = "gs://" + str(uri_snapshot)

        cached = self._listing_cache.get(uri_snapshot)
        if cached is not None:
            # Render instantly from cache, then refresh in the background.
            self.showing_elems = cached.elems
            self.app.title = path
            self._start_background_refresh(uri_snapshot=uri_snapshot, path=path, token=token)
            return True

        try:
            if not uri_snapshot.bucket_name:
                self.showing_elems = self.storage.list_buckets()
            else:
                self.showing_elems = self.storage.list_prefix(uri=uri_snapshot)
            self._listing_cache[uri_snapshot] = _ListingCacheEntry(
                elems=self.showing_elems,
                fetched_at=datetime.now(timezone.utc),
            )
            self.app.title = path
            return True
        except Forbidden:
            self.app.post_message(self.AccessForbidden(self, path))
        except RefreshError:
            self.app.post_message(self.AccessForbidden(self, path))
        except BadRequest as e:
            errors = getattr(e, "errors", None) or []
            for error in errors:
                message = ""
                if isinstance(error, dict):
                    message = str(error.get("message", ""))
                if "Invalid project" in message:
                    self.app.post_message(
                        self.InvalidProject(self, self.storage.get_project())
                    )
                    break
        self.showing_elems = []
        self.app.title = path
        return False

    def clear_cache(self) -> None:
        """Clear cached listings (e.g. after changing auth/project)."""
        self._listing_cache.clear()
        self._in_flight_refreshes.clear()
        # Bump token so any in-flight refresh won't apply.
        self._refresh_token += 1

    def action_search(self) -> None:
        self.app.query_one("#search_box").focus()

    def search_and_highlight(self, value: str) -> None:
        index = self.index or 0
        items_after_selected = list(self.children[index + 1 :])
        items_til_selected = list(self.children[: index + 1])

        for i, child in enumerate(items_after_selected + items_til_selected):
            if child.name and value in child.name:
                self.index = (i + index + 1) % len(self.children)
                return

    def get_current_uri(self) -> BucketWithPrefix:
        return self.uri

    def get_selected_uri(self) -> Optional[BucketWithPrefix]:
        index = self.index
        if index is None:
            return None
        if index < 0 or index >= len(self.showing_elems):
            return None
        return self.showing_elems[index]
