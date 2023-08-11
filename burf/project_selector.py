from textual.widgets import RadioButton, RadioSet, Button, Header, Footer
from textual.containers import Horizontal, Center
from textual.screen import Screen
from textual.app import ComposeResult
from google.cloud import resourcemanager_v3


class CloudProjectSelector(Screen):
    BINDINGS = [
        ("ctrl+s", "app.pop_screen", "cancel"),
        ("escape", "close_screen", "close"),
    ]

    CSS = """
        #cloud_projects {
            width: auto;
        }
        #hor{
            padding-top: 1;
            width: auto;
        }
    """

    def __init__(
        self,
        credentials,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)
        self.credentials = credentials
        self.project_client = self.get_project_client()

    def compose(self) -> ComposeResult:
        projects = self.project_client.list()
        project_ids = []
        yield Header()
        with Center():
            with RadioSet(id="cloud_projects"):
                for project in projects:
                    project_ids.append(project.project_id)
                    yield RadioButton(
                        project.project_id,
                        name=project,
                    )
            with Horizontal(id="hor"):
                yield Button("Ok", name="ok")
                yield Button("Cancel", name="cancel")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.name == "ok":
            for element in self.query_one("#cloud_projects").children:
                if element.value == True:
                    self.dismiss(
                        element.name
                    )  # this is a hack using element.name but name should be str, so find another way
        elif event.button.name == "cancel":
            self.dismiss(None)

    def action_close_screen(self):
        self.dismiss(None)


def get_project_client():
    client = resourcemanager_v3.ProjectsClient()
    request = resourcemanager_v3.ListProjectsRequest()
    return client.list_projects(request=request)
