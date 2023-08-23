from textual.binding import Binding
from textual.widgets import Input


class SearchBox(Input):
    BINDINGS = [
        Binding("escape", "cancel_search", "cancel search"),
    ]

    def action_cancel_search(self) -> None:
        self.value = ""
        self.app.query_one("#file_list").focus()
