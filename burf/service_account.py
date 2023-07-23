from textual.widgets import RadioButton, RadioSet, Button
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.app import ComposeResult


class ServiceAccountSelectScreen(Screen):
    CSS = """
        Screen {
            align: center middle;
        }
        Vectical {
            width: 80%;
            height: 80%;
        }
    """
    BINDINGS = [("escape", "app.pop_screen", "Pop screen")]

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)

    def compose(self) -> ComposeResult:
        service_accounts = ["111111", "222222"]
        active_account = "111111"
        with Vertical():
            with RadioSet(id="service_accounts"):
                for account in service_accounts:
                    yield RadioButton(
                        account, name=account, value=(account == active_account)
                    )
            with Horizontal():
                yield Button("Ok", name="ok")
                yield Button("Close", name="close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.name == "ok":
            for element in self.query_one("#service_accounts").children:
                if element.value == True:
                    self.dismiss(element.value)
        elif event.button.name == "close":
            self.dismiss("")
