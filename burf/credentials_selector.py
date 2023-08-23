from os.path import expanduser
from typing import Optional

from google.oauth2 import service_account
from textual.app import ComposeResult
from textual.containers import Center, Horizontal
from textual.screen import Screen
from textual.widgets import (
    Button,
    DirectoryTree,
    Footer,
    Header,
    Label,
    RadioButton,
    RadioSet,
)

from burf.credentials_provider import CredentialsProvider


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
        self.service_accounts = list(
            self.credential_provider.get_current_service_accounts()
        )

    def compose(self) -> ComposeResult:
        account_emails = []
        radio_buttons = []

        for account in self.service_accounts:
            account_emails.append(account.service_account_email)
            radio_buttons.append(
                RadioButton(
                    account.service_account_email,
                    name=account.service_account_email,
                )
            )

        self.radio_set = RadioSet(*radio_buttons)

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
            if pressed:
                for service_account in self.service_accounts:
                    if service_account.service_account_email == pressed.name:
                        self.dismiss(service_account)
                        return
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
            self.service_accounts.append(account)
            self.radio_set.mount(
                RadioButton(
                    account.service_account_email,
                    name=account.service_account_email,
                    value=False,
                )
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
