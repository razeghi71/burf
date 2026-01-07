from textual.app import ComposeResult
from textual.containers import Center, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label


class ErrorScreen(Screen[None]):
    BINDINGS = [
        ("escape", "close_screen", "close"),
    ]

    CSS = """
        #message {
            padding-top: 1;
            padding-bottom: 1;
        }
        #buttons {
            padding-top: 1;
            width: auto;
        }
    """

    def __init__(
        self,
        title: str,
        message: str,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)
        self._title = title
        self._message = message

    def compose(self) -> ComposeResult:
        yield Header()
        with Center():
            yield Label(self._title)
        with Center():
            yield Label(self._message, id="message")
        with Center():
            with Horizontal(id="buttons"):
                yield Button("Close", name="close")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.name == "close":
            self.dismiss()

    def action_close_screen(self) -> None:
        self.dismiss()

