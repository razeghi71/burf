from __future__ import annotations

from typing import List

from google.api_core.exceptions import BadRequest, Forbidden
from google.auth.exceptions import RefreshError
from textual.binding import Binding
from textual.color import Color
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Label, ListItem, ListView

from burf.storage.ds import BucketWithPrefix
from burf.storage.paths import Blob, Dir
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

    showing_elems: reactive[List[Dir | Blob]] = reactive([])
    position_cache: RecentDict[BucketWithPrefix, int] = RecentDict(10)

    def __init__(
        self,
        storage: Storage,
        uri: BucketWithPrefix = BucketWithPrefix("", ""),
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
        self, _: List[Dir | Blob], new_showing_elems: List[Dir | Blob]
    ) -> None:
        self.clear()
        self.index = 0

        for showing_elem in new_showing_elems:
            row = []
            match showing_elem:
                case Dir(name):
                    pretty_name = Label(f"📂 {name}")
                    pretty_name.styles.width = "65%"
                    row.append(pretty_name)
                case Blob(name, size, time_created):
                    pretty_name = Label(f"📒 {name}")
                    pretty_name.styles.width = "65%"

                    bg_color = self.background_colors[0]

                    time_label = Label(time_created.strftime("%Y-%m-%d %H:%M:%S.%f"))
                    time_label.styles.width = "25%"
                    time_label.styles.background = Color.lighten(bg_color, 0.2)

                    size_label = Label(human_readable_bytes(size))
                    size_label.styles.width = "10%"
                    size_label.styles.background = Color.lighten(bg_color, 0.1)

                    row.append(pretty_name)
                    row.append(time_label)
                    row.append(size_label)

            self.append(
                ListItem(
                    Horizontal(
                        *row,
                    ),
                    name=showing_elem.name,
                )
            )

        if self.uri in self.position_cache:
            self.index = self.position_cache[self.uri]

    def action_back(self) -> None:
        self.uri = self.uri.parent()
        self.refresh_contents()

    def on_list_view_selected(self, selected: ListView.Selected) -> None:
        selected_name = selected.item.name or ""
        if selected_name == "":
            return
        if self.uri.bucket_name != "" and selected_name[-1] != "/":
            return
        elif self.uri.bucket_name == "":
            self.uri = BucketWithPrefix(selected_name, self.uri.prefix)
        else:
            self.uri = BucketWithPrefix(self.uri.bucket_name, selected_name)

        self.refresh_contents()

    def refresh_contents(self) -> bool:
        try:
            if not self.uri.bucket_name:
                path = f"list of buckets in project: ({self.storage.get_project()})"
                new_showing_elem: List[Dir | Blob] = []
                new_showing_elem.extend(self.storage.list_buckets())
                self.showing_elems = new_showing_elem
            else:
                path = "gs://" + str(self.uri)
                self.showing_elems = self.storage.list_prefix(
                    bucket_name=self.uri.bucket_name, prefix=self.uri.prefix
                )
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
