from textual.widgets import RadioButton, RadioSet, Button, DirectoryTree
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.app import ComposeResult
from burf.credentials_provider import CredentialsProvider


class CredentialsSelector(Screen):
    BINDINGS = [("ctrl+s", "app.pop_screen", "cancel")]

    def __init__(
        self,
        credential_provider: CredentialsProvider,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)
        self.credential_provider = credential_provider

    def compose(self) -> ComposeResult:
        service_accounts = self.credential_provider.get_current_service_accounts()
        account_emails = []

        with RadioSet(id="service_accounts"):
            for account in service_accounts:
                account_emails.append(account.service_account_email)
                yield RadioButton(
                    account.service_account_email,
                    name=account,
                )

        with Horizontal():
            yield Button("Add New", name="new")
            yield Button("Ok", name="ok")
            yield Button("Close", name="close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.name == "ok":
            for element in self.query_one("#service_accounts").children:
                if element.value == True:
                    self.dismiss(
                        element.name
                    )  # this is a hack using element.name but name should be str, so find another way
        elif event.button.name == "close":
            self.dismiss(None)
        # elif event.button.name == "new":
        #     self.push_screen(AddCredential())


# class AddCredential(Screen):
#     def compose(self) -> ComposeResult:
#         yield DirectoryTree("./", id="directory")

#     def on_directory_tree_file_selected(self, event):
#         print(event)
#         return
