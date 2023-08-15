from textual.widgets import (
    RadioButton,
    RadioSet,
    Button,
    DirectoryTree,
    Header,
    Footer,
    Label,
)
from textual.containers import Horizontal, Center
from textual.screen import Screen
from textual.app import ComposeResult
from burf.credentials_provider import CredentialsProvider
from os.path import expanduser

from google.oauth2 import service_account

from typing import Optional


class CredentialsSelector(Screen[Optional[service_account.Credentials]]):
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

    radio_set: RadioSet

    def __init__(
        self,
        credential_provider: CredentialsProvider,
        error: Optional[str] = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)
        self.credential_provider = credential_provider
        self.error = error

        self.initialize_radio_buttons()

    def initialize_radio_buttons(self) -> None:
        service_accounts = self.credential_provider.get_current_service_accounts()
        account_emails = []
        radio_buttons = []

        for account in service_accounts:
            account_emails.append(account.service_account_email)
            radio_buttons.append(
                RadioButton(
                    account.service_account_email,
                    name=account,
                )
            )

        self.radio_set = RadioSet(*radio_buttons)

    def compose(self) -> ComposeResult:
        yield Header()
        if self.error is not None:
            with Center():
                yield Label(
                    str(self.error) + ". Please select a compatible service account:",
                    id="error",
                )
        with Center():
            yield self.radio_set

        with Center():
            with Horizontal(id="buttons"):
                yield Button("Ok", name="ok")
                yield Button("Add New", name="new")
                yield Button("Close", name="close")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.name == "ok":
            pressed = self.radio_set.pressed_button
            # this is a hack using element.name but name should be str, so find another way
            if pressed:
                self.dismiss(pressed.name)
        elif event.button.name == "close":
            self.dismiss(None)
        elif event.button.name == "new":
            self.app.push_screen(AddCredential(), self.add_service_account)

    def action_close_screen(self) -> None:
        self.dismiss(None)

    def add_service_account(self, service_account_file: Optional[str]) -> None:
        if service_account_file is not None:
            self.credential_provider.add_service_account(service_account_file)
            account = self.credential_provider.to_credential(service_account_file)
            self.radio_set.mount(
                RadioButton(account.service_account_email, name=account, value=True)
            )


class AddCredential(Screen[Optional[str]]):
    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)

    BINDINGS = [
        ("escape", "close_screen", "close"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield DirectoryTree(expanduser("~"), id="directory")
        yield Footer()

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        self.dismiss(str(event.path))

    def action_close_screen(self) -> None:
        self.dismiss(None)
