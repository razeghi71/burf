from textual.app import App, ComposeResult
from textual.widgets import ListView, ListItem, Label
from textual.containers import Horizontal

class TestApp(App):
    CSS = """
    ListView {
        height: 1fr;
    }
    ListItem {
        border: solid red;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Header")
        yield ListView(
            ListItem(Horizontal(Label("Item 1"), Label("Details 1"))),
            ListItem(Horizontal(Label("Item 2"), Label("Details 2"))),
            ListItem(Label("Item 3")),
            id="list"
        )

if __name__ == "__main__":
    app = TestApp()
    app.run()
