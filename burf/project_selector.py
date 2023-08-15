from textual.widgets import (
    Button,
    Header,
    Footer,
    Input,
)
from textual.containers import Horizontal, Center
from textual.screen import Screen
from textual.app import ComposeResult

from typing import Optional


class ProjectSelector(Screen[Optional[str]]):
    BINDINGS = [
        ("ctrl+s", "app.pop_screen", "cancel"),
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

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)

    def compose(self) -> ComposeResult:
        self.input = Input(placeholder="project name")

        yield Header()

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
