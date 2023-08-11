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


class CredentialsSelector(Screen):
    BINDINGS = [
        ("ctrl+s", "app.pop_screen", "cancel"),
        ("escape", "close_screen", "close"),
    ]

    CSS = """
        #service_accounts {
            width: auto;
        }
        #hor{
            padding-top: 1;
            width: auto;
        }
    """

    def __init__(
        self,
        credential_provider: CredentialsProvider,
        error=None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)
        self.credential_provider = credential_provider
        self.error = error

    def compose(self) -> ComposeResult:
        service_accounts = self.credential_provider.get_current_service_accounts()
        account_emails = []
        yield Header()
        if self.error is not None:
            yield Label(str(self.error), id="error")
        with Center():
            with RadioSet(id="service_accounts"):
                for account in service_accounts:
                    account_emails.append(account.service_account_email)
                    yield RadioButton(
                        account.service_account_email,
                        name=account,
                    )

        with Center():
            with Horizontal(id="hor"):
                yield Button("Add New", name="new")
                yield Button("Ok", name="ok")
                yield Button("Close", name="close")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.name == "ok":
            for element in self.query_one("#service_accounts").children:
                if element.value == True:
                    self.dismiss(
                        element.name
                    )  # this is a hack using element.name but name should be str, so find another way
        elif event.button.name == "close":
            self.dismiss(None)
        elif event.button.name == "new":
            self.app.push_screen(AddCredential(), self.add_service_account)

    def action_close_screen(self):
        self.dismiss(None)

    def add_service_account(self, service_account_file):
        if service_account_file is not None:
            self.credential_provider.add_service_account(service_account_file)
            self.refresh()


class AddCredential(Screen):
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

    def on_directory_tree_file_selected(self, event):
        self.dismiss(event.path)

    def action_close_screen(self):
        self.dismiss(None)
