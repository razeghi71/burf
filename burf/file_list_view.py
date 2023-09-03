from __future__ import annotations

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

        for showing_elem in new_showing_elems:
            row = []
            if showing_elem.is_bucket:
                pretty_name = Label(f"📦 {showing_elem.bucket_name}")
            elif not showing_elem.is_blob:
                pretty_name = Label(f"📂 {showing_elem.full_prefix}")
            else:
                pretty_name = Label(f"📒 {showing_elem.full_prefix}")

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

        if self.uri.bucket_name != "" and selected_name[-1] != "/":
            return
        elif self.uri.bucket_name == "":
            self.uri = BucketWithPrefix(selected_name, [])
        else:
            self.uri = BucketWithPrefix(self.uri.bucket_name, selected_name)

        self.refresh_contents()

    def refresh_contents(self) -> bool:
        try:
            if not self.uri.bucket_name:
                path = f"list of buckets in project: ({self.storage.get_project()})"
                self.showing_elems = self.storage.list_buckets()
            else:
                path = "gs://" + str(self.uri)
                self.showing_elems = self.storage.list_prefix(uri=self.uri)
            self.app.title = path
            return True
        except Forbidden:
            self.app.post_message(self.AccessForbidden(self, path))
        except RefreshError:
            self.app.post_message(self.AccessForbidden(self, path))
        except BadRequest as e:
            for error in e.errors:
                if "Invalid project" in error["message"]:
                    self.app.post_message(
                        self.InvalidProject(self, self.storage.get_project())
                    )
                    break
        self.showing_elems = []
        self.app.title = path
        return False

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
        if self.highlighted_child is None:
            return None
        if self.highlighted_child.name is None:
            return None
        if self.uri.bucket_name is None:
            return BucketWithPrefix(self.highlighted_child.name, None)
        else:
            return BucketWithPrefix(
                self.uri.bucket_name,
                self.highlighted_child.name,
            )
