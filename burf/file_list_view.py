from __future__ import annotations

from textual.events import Mount
from textual.widgets import ListView, ListItem, Label
from textual.reactive import reactive
from textual.widgets._list_item import ListItem
from textual.binding import Binding
from burf.storage import Storage, Dir, Blob
from google.api_core.exceptions import Forbidden
from google.auth.exceptions import RefreshError
from burf.util import human_readable_bytes
from typing import List
from textual.message import Message


class FileListView(ListView):
    BINDINGS = [
        Binding("enter", "select_cursor", "Select"),
        Binding("backspace", "back", "Parent"),
        Binding("/", "search", "search"),
    ]
    showing_elems: reactive[List[Dir | Blob]] = reactive([])
    current_subdir = ""
    current_bucket = ""

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

    def __init__(
        self,
        storage: Storage,
        start_bucket: str = "",
        start_subdir: str = "",
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

        self.storage = storage
        self.current_bucket = start_bucket
        self.current_subdir = start_subdir

    def _on_mount(self, _: Mount) -> None:
        self.refresh_contents()

    def watch_showing_elems(
        self, _: List[Dir | Blob], new_showing_elems: List[Dir | Blob]
    ) -> None:
        self.clear()
        self.index = 0
        for showing_elem in new_showing_elems:
            match showing_elem:
                case Dir(name):
                    pretty_name = f"📂 {name}"
                case Blob(name, size):
                    pretty_name = f"📒 {name} ({human_readable_bytes(size)})"

            self.append(ListItem(Label(pretty_name), name=showing_elem.name))

    def action_back(self) -> None:
        if self.current_bucket == "":
            return
        if self.current_subdir == "":
            self.current_bucket = ""
        else:
            self.current_subdir = (
                ""
                if self.current_subdir.count("/") == 1
                else "/".join(self.current_subdir.split("/")[:-2]) + "/"
            )

        self.refresh_contents()

    def on_list_view_selected(self, child_element: ListView.Selected) -> None:
        child_name = child_element.item.name or ""
        if child_name == "":
            return
        if self.current_bucket != "" and child_name[-1] != "/":
            return
        elif self.current_bucket == "":
            self.current_bucket = child_name
        else:
            self.current_subdir = child_name

        self.refresh_contents()

    def refresh_contents(self) -> None:
        try:
            if not self.current_bucket:
                path = f"list of buckets in project: {self.storage.get_project()}"
                new_showing_elem: List[Dir | Blob] = []
                new_showing_elem.extend(self.storage.list_buckets())
                self.showing_elems = new_showing_elem
            else:
                path = "gs://" + self.current_path()
                self.showing_elems = self.storage.list_prefix(
                    bucket_name=self.current_bucket, prefix=self.current_subdir
                )
        except Forbidden:
            self.app.post_message(self.AccessForbidden(self, path))
        except RefreshError:
            self.app.post_message(self.AccessForbidden(self, path))
        self.app.title = path

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

    def current_path(self) -> str:
        return self.current_bucket + "/" + self.current_subdir
