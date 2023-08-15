from textual.events import Mount
from textual.widgets import ListView, ListItem, Label
from textual.reactive import reactive
from textual.widgets._list_item import ListItem
from textual.binding import Binding
from burf.storage import Storage, Dir, Blob
from google.api_core.exceptions import Forbidden
from burf.util import human_readable_bytes


class FileListView(ListView):
    BINDINGS = [
        Binding("enter", "select_cursor", "Select", show=True),
        Binding("backspace", "back", "Parent", show=True),
        Binding("/", "search", "search"),
    ]
    showing_elems = reactive([])
    current_subdir = ""
    current_bucket = ""

    def __init__(
        self,
        storage: Storage,
        start_bucket="",
        start_subdir="",
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

    def watch_showing_elems(self, _, new_showing_elems):
        self.clear()
        self.index = 0
        for showing_elem in new_showing_elems:
            pretty_name = ""
            if isinstance(showing_elem, Dir):
                pretty_name = f"📂 {showing_elem.name}"
            else:
                pretty_name = (
                    f"📒 {showing_elem.name} ({human_readable_bytes(showing_elem.size)})"
                )

            self.append(ListItem(Label(pretty_name), name=showing_elem.name))

    def action_back(self):
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

    def on_list_view_selected(self, child_element):
        child_name = child_element.item.name
        if self.current_bucket != "" and child_name[-1] != "/":
            return
        elif self.current_bucket == "":
            self.current_bucket = child_name
        else:
            self.current_subdir = child_name

        self.refresh_contents()

    def refresh_contents(self):
        path = "all buckets in project"
        try:
            if not self.current_bucket:
                self.showing_elems = self.storage.list_buckets()
                self.app.title = path
                return
            self.showing_elems = self.storage.list_prefix(
                bucket_name=self.current_bucket, prefix=self.current_subdir
            )
            path = self.current_path()
            self.app.title = path
        except Forbidden as f:
            self.showing_elems = []
            self.app.title = path
            self.app.action_service_account_select(f"Forbidden to get {path}")

    def action_search(self):
        self.app.query_one("#search_box").focus()

    def search_and_highlight(self, value):
        for i, child in enumerate(
            self.children[self.index + 1 :] + self.children[: self.index + 1]
        ):
            if value in child.name:
                self.index = (i + self.index + 1) % len(self.children)
                return

    def current_path(self):
        return self.current_bucket + "/" + self.current_subdir
