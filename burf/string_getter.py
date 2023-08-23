from typing import Optional

from textual.app import ComposeResult
from textual.containers import Center, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label


class StringGetter(Screen[Optional[str]]):
    BINDINGS = [
        ("escape", "close_screen", "close"),
    ]

    CSS = """
        #service_accounts {
            width: auto;
        }
        #buttons{
            padding-top: 1;
            width: auto;
        }
        #error {
            padding-top: 1;
            padding-bottom: 1;
            color: red;
            text-style: bold;
        }
    """

    input: Input
    place_holder: str

    def __init__(
        self,
        place_holder: str,
        error: Optional[str] = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)
        self.place_holder = place_holder
        self.error = error

    def compose(self) -> ComposeResult:
        self.input = Input(placeholder=self.place_holder)

        yield Header()

        if self.error is not None:
            with Center():
                yield Label(str(self.error), id="error")

        with Center():
            yield self.input

        with Center():
            with Horizontal(id="buttons"):
                yield Button("Ok", name="ok")
                yield Button("Close", name="close")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.name == "ok":
            self.dismiss(self.input.value)
        elif event.button.name == "close":
            self.dismiss(None)

    def action_close_screen(self) -> None:
        self.dismiss(None)
