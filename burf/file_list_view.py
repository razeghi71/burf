from __future__ import annotations

from typing import List, Optional

try:
    from botocore.exceptions import ClientError
except ImportError:
    class ClientError(Exception):
        pass

try:
    from google.api_core.exceptions import BadRequest, Forbidden
    from google.auth.exceptions import RefreshError
except ImportError:
    class BadRequest(Exception):
        pass
    class Forbidden(Exception):
        pass
    class RefreshError(Exception):
        pass

from textual.binding import Binding
from textual.color import Color
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Label, ListItem, ListView

from burf.scheme import StorageScheme
from burf.storage.ds import CloudPath
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

    BINDINGS = [
        Binding("enter", "select_cursor", "Select"),
        Binding("backspace", "back", "Parent"),
        Binding("/", "search", "search"),
    ]

    showing_elems: reactive[List[CloudPath]] = reactive([])
    position_cache: RecentDict[CloudPath, int] = RecentDict(10)

    def __init__(
        self,
        storage: Storage,
        uri: CloudPath = CloudPath(StorageScheme.GCS, "", []), # Default to gs scheme for empty
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

    @storage.setter
    def storage(self, new_storage: Storage) -> None:
        self._storage = new_storage
        self._listing_service = ListingService(new_storage)
        self.clear_cache()

    @property
    def uri(self) -> CloudPath:
        return self._uri

    @uri.setter
    def uri(self, new_uri: CloudPath) -> None:
        self.position_cache[self.uri] = self.index or 0
        self._uri = new_uri

    def watch_showing_elems(
        self, _: List[CloudPath], new_showing_elems: List[CloudPath]
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
            self.uri = CloudPath(self.storage.scheme, selected_name, [])
        else:
            self.uri = CloudPath.from_full_prefix(
                self.storage.scheme,
                self.uri.bucket_name,
                selected_name
            )

        self.refresh_contents()

    def _apply_refreshed_listing(
        self,
        *,
        uri_snapshot: CloudPath,
        token: int,
        elems: List[CloudPath],
        path: str,
    ) -> None:
        if token != self._refresh_token or self.uri != uri_snapshot:
            return
        self.showing_elems = elems
        self.app.title = path
        self.app.set_loading(False)

    def _handle_background_error(
        self, *, uri_snapshot: CloudPath, token: int, exc: BaseException, path: str
    ) -> None:
        if token != self._refresh_token or self.uri != uri_snapshot:
            return
        self.app.set_loading(False)
        if isinstance(exc, (Forbidden, RefreshError)):
            self.app.post_message(self.AccessForbidden(self, path))
            return
        if hasattr(exc, "response") and isinstance(exc.response, dict):
            # Check for botocore ClientError structure roughly
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code in ("AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch"):
                self.app.post_message(self.AccessForbidden(self, path))
                return
        # For other background errors, keep existing contents (best-effort).

    def refresh_contents(self) -> bool:
        self._refresh_token += 1
        token = self._refresh_token

        uri_snapshot = self.uri

        if not uri_snapshot.bucket_name:
            # We don't display project/profile name anymore since switching is removed
            path = f"list of buckets ({self.storage.scheme.value})"
        else:
            # We can use CloudPath's __str__ which includes scheme now
            path = str(uri_snapshot)

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

    def get_current_uri(self) -> CloudPath:
        return self.uri

    def get_selected_uri(self) -> Optional[CloudPath]:
        index = self.index
        if index is None:
            return None
        if index < 0 or index >= len(self.showing_elems):
            return None
        return self.showing_elems[index]
