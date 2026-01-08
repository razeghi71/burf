from __future__ import annotations

from typing import List, Optional

from google.api_core.exceptions import BadRequest, Forbidden
from google.auth.exceptions import RefreshError
from textual.binding import Binding
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Label, ListItem, ListView

from burf.storage.ds import BucketWithPrefix
from burf.storage.storage import Storage
from burf.listing_service import ListingService
from burf.util import RecentDict, human_readable_bytes


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
        self._listing_service = ListingService(storage)
        self._uri = uri
        self._refresh_token = 0

    def on_mount(self) -> None:
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

                if showing_elem.updated_at is not None:
                    time_label = Label(
                        showing_elem.updated_at.strftime("%Y-%m-%d %H:%M:%S.%f")
                    )
                else:
                    time_label = Label("")
                time_label.styles.width = "25%"

                if showing_elem.size is not None:
                    size_label = Label(human_readable_bytes(showing_elem.size))
                else:
                    size_label = Label("")
                size_label.styles.width = "10%"

                row.append(time_label)
                row.append(size_label)

            # In Textual 7, container widgets may default to stretching, which can
            # make each ListItem fill the available height. Set explicit row/item
            # heights so each entry remains a single terminal line.
            row_container = Horizontal(*row)
            row_container.styles.height = 1
            row_container.styles.min_height = 1
            row_container.styles.max_height = 1
            for cell in row:
                cell.styles.height = 1

            item = ListItem(
                row_container,
                name=showing_elem.bucket_name
                if showing_elem.is_bucket
                else showing_elem.full_prefix,
            )
            item.styles.height = 1
            item.styles.min_height = 1
            item.styles.max_height = 1
            self.append(item)

        # Set selection after appending items (Textual 7 may ignore index changes
        # while the list is empty).
        if len(self.children) == 0:
            self.index = None
            return

        if self.uri in self.position_cache:
            cached_index = self.position_cache[self.uri]
            self.index = max(0, min(cached_index, len(self.children) - 1))
        else:
            self.index = 0

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

    def _apply_refreshed_listing(
        self,
        *,
        uri_snapshot: BucketWithPrefix,
        token: int,
        elems: List[BucketWithPrefix],
        path: str,
    ) -> None:
        if token != self._refresh_token or self.uri != uri_snapshot:
            return
        self.showing_elems = elems
        self.app.title = path
        self.app.set_loading(False)

    def _handle_background_error(
        self, *, uri_snapshot: BucketWithPrefix, token: int, exc: BaseException, path: str
    ) -> None:
        if token != self._refresh_token or self.uri != uri_snapshot:
            return
        self.app.set_loading(False)
        if isinstance(exc, Forbidden) or isinstance(exc, RefreshError):
            self.app.post_message(self.AccessForbidden(self, path))
            return
        if isinstance(exc, BadRequest):
            errors = getattr(exc, "errors", None) or []
            for error in errors:
                message = ""
                if isinstance(error, dict):
                    message = str(error.get("message", ""))
                if "Invalid project" in message:
                    self.app.post_message(self.InvalidProject(self, self.storage.get_project()))
                    return
        # For other background errors, keep existing contents (best-effort).

    def refresh_contents(self) -> bool:
        self._refresh_token += 1
        token = self._refresh_token

        uri_snapshot = self.uri

        if not uri_snapshot.bucket_name:
            path = f"list of buckets in project: ({self.storage.get_project()})"
        else:
            path = "gs://" + str(uri_snapshot)

        cached = self._listing_service.get_cached(uri_snapshot)
        if cached is not None:
            self.showing_elems = cached
            self.app.title = path
            self.app.set_loading(False)
            self._listing_service.refresh_async(
                uri_snapshot,
                on_success=lambda elems: self.app.call_from_thread(
                    self._apply_refreshed_listing,
                    uri_snapshot=uri_snapshot,
                    token=token,
                    elems=elems,
                    path=path,
                ),
                on_error=lambda exc: self.app.call_from_thread(
                    self._handle_background_error,
                    uri_snapshot=uri_snapshot,
                    token=token,
                    exc=exc,
                    path=path,
                ),
            )
            return True

        self.showing_elems = []
        self.app.title = path
        self.app.set_loading(True)

        self._listing_service.refresh_async(
            uri_snapshot,
            on_success=lambda elems: self.app.call_from_thread(
                self._apply_refreshed_listing,
                uri_snapshot=uri_snapshot,
                token=token,
                elems=elems,
                path=path,
            ),
            on_error=lambda exc: self.app.call_from_thread(
                self._handle_background_error,
                uri_snapshot=uri_snapshot,
                token=token,
                exc=exc,
                path=path,
            ),
        )
        return True

    def clear_cache(self) -> None:
        self._listing_service.clear()
        self._refresh_token += 1
        self.app.set_loading(False)

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
