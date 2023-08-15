from textual.widgets import Input
from textual.binding import Binding


class SearchBox(Input):
    BINDINGS = [
        Binding("escape", "cancel_search", "cancel search"),
    ]

    def action_cancel_search(self):
        self.value = ""
        self.app.query_one("#file_list").focus()
